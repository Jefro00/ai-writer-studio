"""AI Writer Studio 3.0 — Streamlit interface; business logic lives in modules."""
from __future__ import annotations

import copy
import os
import streamlit as st
import streamlit.components.v1 as components

from core.ai_engine import AIEngine
from core.orchestrator import run_editorial
from core.storage import Storage
from services.exporter import create_docx, create_markdown
from services.infographic import card_height, render_html, render_svg

APP_VERSION = "3.1.0"

st.set_page_config(page_title="AI Writer Studio", page_icon="✍️", layout="wide", initial_sidebar_state="expanded")


def secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except Exception:
        return os.getenv(name, default)


def initialize_state():
    defaults = {"authenticated": False, "article": "", "analysis": "", "strategy": "", "sources": [],
                "fact_checks": [], "infographics": [], "call_log": [], "last_topic": "", "history_id": None,
                "article_editor": "", "last_loaded_history": None}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


def authenticate() -> bool:
    app_password = secret("APP_PASSWORD")
    if not app_password or st.session_state.authenticated:
        return True
    st.title("🔐 AI Writer Studio")
    password = st.text_input("Пароль доступа", type="password")
    if st.button("Войти", type="primary"):
        if password == app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный пароль")
    return False


initialize_state()
if not authenticate():
    st.stop()

storage = Storage()
engine = AIEngine(
    gemini_key=secret("GEMINI_API_KEY"),
    openrouter_key=secret("OPENROUTER_API_KEY"),
    gemini_model=secret("GEMINI_MODEL", "gemini-2.5-flash"),
    openrouter_model=secret("OPENROUTER_MODEL", "openrouter/free"),
)

with st.sidebar:
    st.title("⚙️ Настройки")
    st.caption(f"AI Writer Studio v{APP_VERSION}")
    if not secret("APP_PASSWORD"):
        st.warning("APP_PASSWORD не задан: вход в приложение не защищён паролем.")
    st.divider()
    language = st.selectbox("Язык", ["Русский", "English"])
    content_format = st.selectbox("Формат для X", ["X Article", "Thread", "Single Post", "Research Post", "Market Commentary"])
    style = st.selectbox("Стиль", ["Аналитический", "Экспертный", "Журналистский", "Научно-популярный", "Технический", "Неформальный"])
    length = st.select_slider("Объём (для длинных форматов)", options=[500, 1000, 1500, 2000, 3000, 5000], value=1500)
    make_infographics = st.checkbox(
        "Автоматически создавать инфографику, если она полезна",
        value=True,
        help="Добавляет один AI-запрос. Карточки формируются только из утверждений, прошедших этап фактчекинга.",
    )
    st.divider()
    st.subheader("AI-провайдеры")
    if engine.gemini_key:
        st.success("Gemini: подключён")
    else:
        st.error("Gemini: не настроен")
    if engine.openrouter_key:
        st.success("OpenRouter: подключён")
    else:
        st.error("OpenRouter: не настроен")
    st.caption(f"Gemini: {engine.gemini_model} · резервный: {engine.openrouter_model}")
    st.divider()
    st.subheader("Сохранённые проекты")
    sessions = storage.list_sessions(50)
    st.metric("Всего черновиков", len(sessions))
    if sessions:
        labels = {f"#{x['id']} · {x['topic'][:70]} · {x['updated_at'][:10]}": x["id"] for x in sessions}
        chosen_label = st.selectbox("Открыть проект", ["— Текущий —", *labels.keys()], key="history_choice")
        if chosen_label != "— Текущий —":
            chosen_id = labels[chosen_label]
            if chosen_id != st.session_state.last_loaded_history:
                record = storage.get_session(chosen_id)
                if record:
                    for key in ("article", "analysis", "strategy", "sources", "fact_checks", "infographics", "last_topic"):
                        st.session_state[key] = record.get(key) or ("" if key in {"article", "analysis", "strategy", "last_topic"} else [])
                    st.session_state.last_topic = record["topic"]
                    st.session_state.history_id = record["id"]
                    st.session_state.article_editor = record["article"]
                    st.session_state.last_loaded_history = chosen_id
                    st.rerun()
    if st.button("Очистить выбранный черновик", disabled=not st.session_state.history_id, use_container_width=True):
        storage.delete_session(int(st.session_state.history_id))
        st.session_state.history_id = None
        st.session_state.last_loaded_history = None
        st.session_state.article = ""
        st.session_state.article_editor = ""
        st.rerun()

st.title("✍️ AI Writer Studio")
st.caption("Исследуй источники, проверяй утверждения и готовь материалы для X")
st.markdown("**Исследование → оценка источников → синтез → фактчекинг → редактура.** Публикация в X пока не включена: доступность нужных официальных API-возможностей не подтверждена.")
st.divider()

topic = st.text_area("Тема или исследовательский вопрос", value=st.session_state.last_topic,
                     placeholder="Например: Что на самом деле происходит с токенизацией RWA на Solana?", height=120)
run_clicked = st.button("🚀 Запустить редакцию", type="primary", disabled=not engine.providers)
if not engine.providers:
    st.info("Для запуска добавьте GEMINI_API_KEY или OPENROUTER_API_KEY в Streamlit Secrets.")

if run_clicked:
    if not topic.strip():
        st.error("Сначала введите тему статьи.")
    else:
        engine.logs.clear()
        progress_bar = st.progress(0)
        status_text = st.empty()
        stages = {"search": 0.05, "extract": 0.20, "analysis": 0.38, "strategy": 0.52,
                  "writing": 0.66, "fact_check": 0.78, "infographic": 0.87, "editing": 0.94, "done": 1.0}
        def report(stage, message):
            status_text.info(message)
            progress_bar.progress(stages.get(stage, 0.2))
        try:
            result = run_editorial(
                topic.strip(), language, style, length, content_format, engine,
                make_infographics=make_infographics, progress=report,
            )
            result["call_log"] = engine.logs
            st.session_state.article = result["article"]
            st.session_state.analysis = result["analysis"]
            st.session_state.strategy = result["strategy"]
            st.session_state.sources = result["sources"]
            st.session_state.fact_checks = result["fact_checks"]
            st.session_state.infographics = result.get("infographics", [])
            st.session_state.call_log = engine.logs
            st.session_state.last_topic = topic.strip()
            st.session_state.article_editor = result["article"]
            saved_id = storage.save_session(result)
            st.session_state.history_id = saved_id
            st.session_state.last_loaded_history = saved_id
            st.success(f"Черновик #{saved_id} сохранён в локальной базе данных.")
        except Exception as exc:
            st.error(f"Ошибка редакции: {exc}")
        finally:
            progress_bar.empty()
            status_text.empty()

if st.session_state.article:
    st.divider()
    st.subheader("📄 Черновик")
    tab_article, tab_analysis, tab_sources, tab_facts, tab_visuals, tab_logs = st.tabs(
        ["Материал", "Исследование", "Источники", "Фактчекинг", "Инфографика", "Логи"]
    )
    with tab_article:
        st.text_area("Редактировать перед экспортом", key="article_editor", height=520)
        if st.button("💾 Сохранить правки", type="primary"):
            st.session_state.article = st.session_state.article_editor
            if st.session_state.history_id:
                record = storage.get_session(int(st.session_state.history_id)) or {}
                record.update({"article": st.session_state.article, "topic": st.session_state.last_topic,
                               "analysis": st.session_state.analysis, "strategy": st.session_state.strategy,
                               "sources": st.session_state.sources, "fact_checks": st.session_state.fact_checks})
                storage.save_session(record, int(st.session_state.history_id))
            st.success("Правки сохранены.")
        markdown = create_markdown(st.session_state.article_editor, st.session_state.sources, st.session_state.fact_checks)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("📥 Скачать Markdown", markdown, file_name="ai-writer-draft.md", mime="text/markdown", use_container_width=True)
        with c2:
            st.download_button("📥 Скачать Word", create_docx(markdown), file_name="ai-writer-draft.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        st.info("Материал подготовлен как черновик. Подключение, планирование и публикация в X не выполняются.")
    with tab_analysis:
        st.markdown(st.session_state.analysis or "Нет отчёта.")
        if st.session_state.strategy:
            with st.expander("Редакционный план"):
                st.markdown(st.session_state.strategy)
    with tab_sources:
        st.caption("Оценка — эвристический сигнал, а не гарантия достоверности. Доступность и полнота текста зависят от сайта.")
        for idx, source in enumerate(st.session_state.sources, 1):
            title = source.get("title") or source.get("url") or f"Источник {idx}"
            with st.expander(f"{idx}. {title}"):
                st.markdown(f"**URL:** {source.get('url', '')}")
                st.write(f"Тип: {source.get('source_type', 'не определён')} · Дата: {source.get('published_at') or 'не найдена'} · Извлечение: {source.get('extraction_status', 'unknown')}")
                st.caption(source.get("credibility_notes", ""))
                st.write(source.get("content") or source.get("snippet") or "Текст недоступен.")
                if source.get("url"):
                    st.link_button("Открыть источник", source["url"])
    with tab_facts:
        st.caption("Статусы сформированы моделью по собранным материалам; они требуют человеческой проверки, особенно для значимых цифр.")
        if st.session_state.fact_checks:
            for check in st.session_state.fact_checks:
                icon = {"VERIFIED": "✅", "PARTIALLY VERIFIED": "⚠️", "UNVERIFIED": "❓"}.get(check["status"], "❓")
                with st.expander(f"{icon} {check['status']}: {check['claim']}"):
                    st.write(check.get("note", ""))
                    st.caption(f"Дата данных: {check.get('data_date', 'unknown')} · Источники: {check.get('source_ids', [])}")
        else:
            st.warning("Проверки не распознаны. Не считайте утверждения подтверждёнными автоматически.")
    with tab_visuals:
        if st.session_state.infographics:
            st.caption("Карточки собираются из дословных утверждений фактчекинга и сохраняются вместе с проектом.")
            for index, card in enumerate(st.session_state.infographics, 1):
                st.subheader(f"Карточка {index}")
                components.html(render_html(card), height=max(card_height(card), card_height(card, mobile=True)) + 8, scrolling=False)
                st.download_button(
                    "Скачать векторную карточку (SVG)",
                    data=render_svg(card),
                    file_name=f"infographic_{index}.svg",
                    mime="image/svg+xml",
                    key=f"infographic_download_{st.session_state.history_id}_{index}",
                )
                cited = card.get("source_ids", [])
                if cited:
                    st.caption("Источники карточки:")
                    for source_id in cited:
                        if 1 <= source_id <= len(st.session_state.sources):
                            source = st.session_state.sources[source_id - 1]
                            st.markdown(f"[{source_id}] {source.get('title') or source.get('url')} — {source.get('url')}")
        else:
            st.info("Карточка не создана: инфографика не добавила бы наглядности, генерация отключена или не хватило проверенных утверждений.")
    with tab_logs:
        if st.session_state.call_log:
            st.dataframe(st.session_state.call_log, use_container_width=True, hide_index=True)
        else:
            st.info("Логи AI-вызовов отсутствуют.")

st.divider()
st.caption(f"AI Writer Studio {APP_VERSION} · Локальная SQLite-база; при облачном деплое её долговечность зависит от хостинга и диска.")
