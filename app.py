
import io
import time
import requests
import streamlit as st

from datetime import datetime
from google import genai
from ddgs import DDGS
from docx import Document


# ============================================================
# 1. CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Writer Studio",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_VERSION = "2.0.0"

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
GEMINI_MODEL = st.secrets.get(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)

OPENROUTER_API_KEY = st.secrets.get(
    "OPENROUTER_API_KEY",
    ""
)

APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

OPENROUTER_MODEL = "openrouter/free"

# Gemini client
gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


# ============================================================
# 2. SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "authenticated": False,
    "article": "",
    "analysis": "",
    "sources": [],
    "call_log": [],
    "last_topic": "",
    "research_history": [],
    "current_provider": None
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 3. AUTHENTICATION
# ============================================================

def authentication():

    if not APP_PASSWORD:
        return True

    if st.session_state.authenticated:
        return True

    st.title("🔐 AI Writer Studio")

    password = st.text_input(
        "Пароль доступа",
        type="password"
    )

    if st.button("Войти", type="primary"):

        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()

        else:
            st.error("Неверный пароль")

    return False


if not authentication():
    st.stop()


# ============================================================
# 4. PROVIDER STATUS
# ============================================================

def get_provider_status():

    return {
        "Gemini": bool(GEMINI_API_KEY),
        "OpenRouter": bool(OPENROUTER_API_KEY)
    }


# ============================================================
# 5. GEMINI PROVIDER
# ============================================================

def ask_gemini(prompt):

    if not gemini_client:
        raise RuntimeError(
            "Gemini API key не настроен"
        )

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    if not response.text:
        raise RuntimeError(
            "Gemini вернул пустой ответ"
        )

    return response.text.strip()


# ============================================================
# 6. OPENROUTER PROVIDER
# ============================================================

def ask_openrouter(prompt):

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OpenRouter API key не настроен"
        )

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",

        headers={
            "Authorization": (
                f"Bearer {OPENROUTER_API_KEY}"
            ),
            "Content-Type": "application/json",
            "X-Title": "AI Writer Studio"
        },

        json={
            "model": OPENROUTER_MODEL,

            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional "
                        "research and editorial assistant. "
                        "Follow instructions carefully."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            "temperature": 0.5
        },

        timeout=(15, 120)
    )

    response.raise_for_status()

    data = response.json()

    result = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    # Some providers may return content as an array.
    if isinstance(result, list):
        result = "\n".join(
            item.get("text", "")
            for item in result
            if isinstance(item, dict)
        )

    if not isinstance(result, str) or not result.strip():
        raise RuntimeError(
            "OpenRouter вернул пустой ответ"
        )

    return result.strip()


# ============================================================
# 7. UNIVERSAL AI ENGINE WITH FALLBACK
# ============================================================

def ask_ai(prompt, agent_name="AI Agent"):

    providers = []

    if GEMINI_API_KEY:
        providers.append(("Gemini", ask_gemini))

    if OPENROUTER_API_KEY:
        providers.append(("OpenRouter", ask_openrouter))

    if not providers:
        raise RuntimeError(
            "Не настроен ни один API. "
            "Добавь Gemini или OpenRouter key в Secrets."
        )

    errors = []

    for provider_name, provider_function in providers:

        # Two attempts for temporary provider failures.
        for attempt in range(2):

            try:

                result = provider_function(prompt)

                st.session_state.call_log.append({
                    "agent": agent_name,
                    "provider": provider_name,
                    "status": "success",
                    "time": datetime.now().strftime(
                        "%H:%M:%S"
                    )
                })

                st.session_state.current_provider = (
                    provider_name
                )

                return result

            except Exception as error:

                error_message = str(error)

                errors.append(
                    f"{provider_name}: {error_message}"
                )

                st.session_state.call_log.append({
                    "agent": agent_name,
                    "provider": provider_name,
                    "status": "failed",
                    "error": error_message[:250],
                    "time": datetime.now().strftime(
                        "%H:%M:%S"
                    )
                })

                if attempt == 0:
                    time.sleep(2)

                else:
                    st.warning(
                        f"{provider_name} недоступен. "
                        "Пробуем следующий провайдер."
                    )

    raise RuntimeError(
        "Все доступные провайдеры завершились ошибкой:\n"
        + "\n".join(errors)
    )


# ============================================================
# 8. RESEARCH AGENT
# ============================================================

def research(topic, max_results=5):

    queries = [
        topic,
        f"{topic} latest news statistics",
        f"{topic} research official sources"
    ]

    results = []
    seen_urls = set()
    search_errors = []

    progress = st.progress(0)

    for index, query in enumerate(queries):

        try:

            with DDGS() as search:

                found = search.text(
                    query,
                    max_results=max_results
                )

            for item in found or []:

                url = item.get("href", "").strip()

                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                results.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "body": item.get("body", ""),
                    "query": query
                })

        except Exception as error:

            message = str(error)

            if "no results found" not in message.lower():
                search_errors.append(message)

        progress.progress(
            (index + 1) / len(queries)
        )

    progress.empty()

    if search_errors:
        st.warning(
            f"Некоторые поисковые запросы завершились "
            f"ошибкой ({len(search_errors)})."
        )

    return results


# ============================================================
# 9. ANALYST AGENT
# ============================================================

def analyze(topic, sources):

    material = "\n\n".join(
        (
            f"SOURCE [{i + 1}]\n"
            f"TITLE: {source['title']}\n"
            f"URL: {source['url']}\n"
            f"DESCRIPTION: {source['body']}"
        )
        for i, source in enumerate(sources)
    )

    prompt = f"""
You are a senior research analyst.

RESEARCH TOPIC:
{topic}

AVAILABLE SEARCH RESULTS:
{material}

YOUR TASK:

1. Identify the most important facts.
2. Find relevant statistics and trends.
3. Identify major companies, projects and organizations.
4. Separate verified information from assumptions.
5. Identify contradictions between sources.
6. Highlight missing information.
7. Create a logical structure for the article.
8. Reference source numbers whenever possible.

IMPORTANT:

- Do not invent statistics.
- Do not invent quotes.
- Do not present assumptions as facts.
- If information is missing, explicitly say so.
- Search snippets are not equivalent to verified full articles.

OUTPUT:

A detailed research report with headings and source references.
"""

    return ask_ai(
        prompt,
        agent_name="Analyst"
    )


# ============================================================
# 10. WRITER AGENT
# ============================================================

def write_article(
    topic,
    analysis,
    sources,
    language,
    style,
    length
):

    source_list = "\n".join(
        f"[{i + 1}] {source['title']} | {source['url']}"
        for i, source in enumerate(sources)
    )

    prompt = f"""
You are an experienced professional journalist
and long-form article writer.

YOUR TASK:
Write a complete, high-quality article.

TOPIC:
{topic}

LANGUAGE:
{language}

WRITING STYLE:
{style}

TARGET LENGTH:
Approximately {length} words.

RESEARCH REPORT:
{analysis}

AVAILABLE SOURCES:
{source_list}

EDITORIAL REQUIREMENTS:

1. Create a compelling headline.
2. Write a meaningful introduction.
3. Organize the article with logical headings.
4. Explain complex topics clearly.
5. Use facts and examples from the research.
6. Include source references like [1], [2].
7. Avoid unnecessary repetition.
8. Avoid generic AI-style introductions.
9. Maintain a natural human writing style.
10. Do not invent facts, statistics or quotations.
11. Clearly distinguish predictions from confirmed facts.
12. Do not claim to have read full sources when only snippets
    are available.

ARTICLE STRUCTURE:

- Headline
- Introduction
- Main sections
- Analysis
- Risks and limitations
- Conclusion
- Sources

Return the complete article in Markdown.
"""

    return ask_ai(
        prompt,
        agent_name="Writer"
    )


# ============================================================
# 11. EDITOR AGENT
# ============================================================

def edit_article(article, analysis):

    prompt = f"""
You are the chief editor of a professional publication.

YOUR TASK:
Edit and improve the following article.

ARTICLE:
{article}

RESEARCH REPORT:
{analysis}

CHECK:

1. Logical consistency.
2. Clarity and readability.
3. Repetitions and unnecessary paragraphs.
4. Weak arguments.
5. Unsupported factual claims.
6. Headline quality.
7. Natural language.
8. Section structure.
9. Source references.
10. Contradictions with the research report.

IMPORTANT:

- Do not add invented information.
- Do not invent citations.
- Preserve important facts.
- Preserve the original meaning.
- Do not remove source references without reason.
- Mark uncertain claims as uncertain.
- Do not shorten the article unnecessarily.

Return the complete edited article in Markdown.
"""

    return ask_ai(
        prompt,
        agent_name="Editor"
    )


# ============================================================
# 12. WORD EXPORT
# ============================================================

def create_docx(markdown):

    doc = Document()

    for line in markdown.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("# "):

            doc.add_heading(
                line[2:],
                level=1
            )

        elif line.startswith("## "):

            doc.add_heading(
                line[3:],
                level=2
            )

        elif line.startswith("### "):

            doc.add_heading(
                line[4:],
                level=3
            )

        elif line.startswith("- "):

            doc.add_paragraph(
                line[2:],
                style="List Bullet"
            )

        elif line.startswith("1. "):

            doc.add_paragraph(
                line[3:],
                style="List Number"
            )

        else:

            text = line.replace("**", "").replace("*", "")

            doc.add_paragraph(text)

    buffer = io.BytesIO()

    doc.save(buffer)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# 13. MARKDOWN EXPORT
# ============================================================

def create_markdown(article, sources):

    source_section = "\n\n## Источники\n\n"

    for index, source in enumerate(sources):

        source_section += (
            f"{index + 1}. "
            f"[{source['title']}]({source['url']})\n"
        )

    return article + source_section


# ============================================================
# 14. ARTICLE GENERATION PIPELINE
# ============================================================

def run_editorial(
    topic,
    language,
    style,
    length
):

    st.session_state.article = ""
    st.session_state.analysis = ""
    st.session_state.sources = []
    st.session_state.call_log = []

    st.session_state.last_topic = topic

    # -------------------------
    # AGENT 1: RESEARCH
    # -------------------------

    with st.status(
        "🔎 Агент 1: исследование",
        expanded=True
    ) as status:

        st.write(
            "Поиск информации по нескольким запросам..."
        )

        sources = research(topic)

        if not sources:

            raise RuntimeError(
                "Не удалось найти источники. "
                "Попробуй изменить формулировку темы."
            )

        st.write(
            f"Найдено уникальных источников: {len(sources)}"
        )

        st.session_state.sources = sources

        status.update(
            label="Исследование завершено",
            state="complete"
        )

    # -------------------------
    # AGENT 2: ANALYSIS
    # -------------------------

    with st.status(
        "🧠 Агент 2: аналитика",
        expanded=True
    ) as status:

        st.write(
            "Анализ фактов, тенденций и противоречий..."
        )

        analysis = analyze(
            topic,
            sources
        )

        st.session_state.analysis = analysis

        status.update(
            label="Анализ завершён",
            state="complete"
        )

    # -------------------------
    # AGENT 3: WRITER
    # -------------------------

    with st.status(
        "✍️ Агент 3: написание",
        expanded=True
    ) as status:

        st.write(
            "Подготовка полноценной статьи..."
        )

        article = write_article(
            topic,
            analysis,
            sources,
            language,
            style,
            length
        )

        status.update(
            label="Черновик статьи готов",
            state="complete"
        )

    # -------------------------
    # AGENT 4: EDITOR
    # -------------------------

    with st.status(
        "📝 Агент 4: редактура",
        expanded=True
    ) as status:

        st.write(
            "Проверка структуры, логики и качества текста..."
        )

        final_article = edit_article(
            article,
            analysis
        )

        st.session_state.article = final_article

        status.update(
            label="Редактура завершена",
            state="complete"
        )

    # -------------------------
    # SAVE SESSION HISTORY
    # -------------------------

    st.session_state.research_history.append({
        "topic": topic,
        "article": final_article,
        "analysis": analysis,
        "sources": sources,
        "date": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    })


# ============================================================
# 15. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("⚙️ Настройки")

    st.caption(
        f"AI Writer Studio v{APP_VERSION}"
    )

    st.divider()

    language = st.selectbox(
        "Язык статьи",
        [
            "Русский",
            "English"
        ]
    )

    style = st.selectbox(
        "Стиль",

        [
            "Аналитический",
            "Экспертный",
            "Журналистский",
            "Научно-популярный",
            "Технический",
            "SEO"
        ]
    )

    length = st.select_slider(
        "Объём статьи",

        options=[
            500,
            1000,
            1500,
            2000,
            3000,
            5000
        ],

        value=2000
    )

    st.divider()

    st.subheader("ИИ-провайдеры")

    providers = get_provider_status()

    for name, available in providers.items():

        if available:
            st.success(f"{name}: подключён")

        else:
            st.error(f"{name}: не настроен")

    st.caption(
        f"Gemini: {GEMINI_MODEL}"
    )

    st.caption(
        f"Fallback: {OPENROUTER_MODEL}"
    )

    st.divider()

    st.subheader("История")

    st.metric(
        "Создано статей",
        len(st.session_state.research_history)
    )

    if st.button(
        "Очистить историю сессии",
        use_container_width=True
    ):

        st.session_state.research_history = []
        st.rerun()


# ============================================================
# 16. MAIN INTERFACE
# ============================================================

st.title("✍️ AI Writer Studio")

st.caption(
    "Автономная редакция на базе нескольких ИИ-агентов"
)

st.markdown(
    """
    Исследуй темы, анализируй источники,
    создавай статьи и редактируй их с помощью ИИ.
    """
)

st.divider()


# ============================================================
# 17. TOPIC INPUT
# ============================================================

topic = st.text_area(
    "О чём будем писать?",

    placeholder=(
        "Например: Будущее токенизации "
        "реальных активов на Solana..."
    ),

    height=140
)


# ============================================================
# 18. GENERATE BUTTON
# ============================================================

if st.button(
    "🚀 Запустить редакцию",
    type="primary",
    use_container_width=False
):

    if not topic.strip():

        st.error(
            "Сначала введи тему статьи."
        )

    elif not GEMINI_API_KEY and not OPENROUTER_API_KEY:

        st.error(
            "Не подключён ни один ИИ-провайдер."
        )

    else:

        try:

            run_editorial(
                topic=topic.strip(),
                language=language,
                style=style,
                length=length
            )

            st.success(
                "🎉 Статья успешно создана!"
            )

        except Exception as error:

            st.error(
                f"Ошибка редакции: {error}"
            )


# ============================================================
# 19. RESULTS
# ============================================================

if st.session_state.article:

    st.divider()

    st.title("📄 Результат")

    tab_article, tab_analysis, tab_sources, tab_logs = (
        st.tabs([
            "Статья",
            "Аналитика",
            "Источники",
            "Логи агентов"
        ])
    )

    # -------------------------
    # ARTICLE TAB
    # -------------------------

    with tab_article:

        st.markdown(
            st.session_state.article
        )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:

            st.download_button(
                "📥 Скачать Markdown",

                data=create_markdown(
                    st.session_state.article,
                    st.session_state.sources
                ),

                file_name="article.md",

                mime="text/markdown",

                use_container_width=True
            )

        with col2:

            st.download_button(
                "📥 Скачать Word",

                data=create_docx(
                    st.session_state.article
                ),

                file_name="article.docx",

                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),

                use_container_width=True
            )

    # -------------------------
    # ANALYSIS TAB
    # -------------------------

    with tab_analysis:

        st.subheader(
            "Отчёт аналитика"
        )

        st.markdown(
            st.session_state.analysis
        )

    # -------------------------
    # SOURCES TAB
    # -------------------------

    with tab_sources:

        st.subheader(
            "Найденные источники"
        )

        for index, source in enumerate(
            st.session_state.sources,
            start=1
        ):

            with st.expander(
                f"{index}. {source['title']}"
            ):

                st.write(
                    source["body"]
                )

                st.link_button(
                    "Открыть источник",
                    source["url"]
                )

    # -------------------------
    # LOGS TAB
    # -------------------------

    with tab_logs:

        st.subheader(
            "История выполнения агентов"
        )

        if st.session_state.call_log:

            st.dataframe(
                st.session_state.call_log,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Нет записей."
            )


# ============================================================
# 20. RESEARCH HISTORY
# ============================================================

if st.session_state.research_history:

    st.divider()

    st.subheader(
        "📚 Последние проекты"
    )

    for index, project in enumerate(
        reversed(st.session_state.research_history[-10:])
    ):

        with st.expander(
            project["topic"]
        ):

            st.caption(
                project["date"]
            )

            st.markdown(
                project["article"][:1500] + "..."
            )

            st.download_button(
                "Скачать статью",

                data=project["article"],

                file_name=f"article_{index + 1}.md",

                mime="text/markdown",

                key=f"history_download_{index}"
            )


# ============================================================
# 21. FOOTER
# ============================================================

st.divider()

st.caption(
    "AI Writer Studio | "
    "Powered by Gemini & OpenRouter | "
    f"Version {APP_VERSION}"
)
