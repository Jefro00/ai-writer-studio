"""Safe, bounded extraction of public web pages."""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 4
USER_AGENT = "AIWriterStudio/3.0 (+research; contact: local application)"


def _validate_public_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Разрешены только публичные HTTP(S) URL без данных авторизации")
    host = parts.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Локальные хосты не разрешены")
    try:
        addresses = [ipaddress.ip_address(host)] if _is_ip(host) else [ipaddress.ip_address(x[4][0]) for x in socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)]
    except (OSError, ValueError) as exc:
        raise ValueError("Не удалось проверить публичный адрес источника") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Источник ведёт на непубличный адрес и заблокирован")
    # Drop fragments; they are irrelevant to a request.
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _extract_date(soup) -> str | None:
    selectors = [
        ("meta", {"property": "article:published_time"}, "content"),
        ("meta", {"property": "article:modified_time"}, "content"),
        ("meta", {"name": "date"}, "content"),
        ("meta", {"name": "pubdate"}, "content"),
        ("time", {"datetime": True}, "datetime"),
    ]
    for tag, attrs, key in selectors:
        node = soup.find(tag, attrs=attrs)
        if node and node.get(key):
            raw = str(node.get(key)).strip()
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", raw)
                if match:
                    return match.group(1)
    for node in soup.find_all("script", type="application/ld+json")[:5]:
        try:
            data = json.loads(node.string or node.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            raw = item.get("datePublished") or item.get("dateCreated")
            if raw:
                try:
                    return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date().isoformat()
                except ValueError:
                    pass
    return None


def _clean_html(html: str) -> tuple[str, str, str | None]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "")
    published_at = _extract_date(soup)
    # Prefer Trafilatura when installed; BeautifulSoup remains a supported fallback.
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True, favor_recall=False)
    except ImportError:
        extracted = None
    if not extracted:
        for node in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form", "iframe"]):
            node.decompose()
        main = soup.find("article") or soup.find("main") or soup.body or soup
        extracted = main.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", extracted or "").strip()
    return title, text[:30000], published_at


def read_source(url: str, timeout: tuple[int, int] = (6, 12)) -> dict:
    """Fetch a public web page, validating every redirect and limiting bytes."""
    current = _validate_public_url(url)
    response = None
    session = requests.Session()
    try:
        for _ in range(MAX_REDIRECTS + 1):
            # Validate host again immediately before each request (including redirects).
            current = _validate_public_url(current)
            response = session.get(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}, timeout=timeout, allow_redirects=False, stream=True)
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise RuntimeError("У ответа отсутствует адрес перенаправления")
                current = urljoin(current, location)
                continue
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not any(t in content_type for t in ("text/html", "application/xhtml+xml", "text/plain")):
                return {"final_url": current, "content": "", "title": "", "published_at": None, "extraction_status": "unsupported_content_type"}
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_BYTES:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
            encoding = response.encoding or "utf-8"
            html = raw.decode(encoding, errors="replace")
            title, content, published = _clean_html(html)
            return {"final_url": current, "content": content, "title": title, "published_at": published,
                    "extraction_status": "extracted" if content else "empty"}
        raise RuntimeError("Слишком много перенаправлений")
    finally:
        if response is not None:
            response.close()
        session.close()


def enrich_source(source: dict) -> dict:
    """Enrich a search result without failing the entire research run."""
    result = dict(source)
    result.setdefault("snippet", result.get("body", ""))
    result["content"] = ""
    result["published_at"] = None
    result["extraction_status"] = "not_attempted"
    try:
        extracted = read_source(result["url"])
        result.update(extracted)
        if extracted.get("title"):
            result["title"] = extracted["title"]
    except Exception as exc:
        result["extraction_status"] = "failed"
        result["extraction_error"] = str(exc)[:240]
    return result
