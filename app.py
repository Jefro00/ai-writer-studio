
import io
import streamlit as st
from google import genai
from ddgs import DDGS
from docx import Document

st.set_page_config(
    page_title="AI Writer Studio",
    page_icon="✍️",
    layout="wide"
)

# ---------- CONFIG ----------

def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


API_KEY = get_secret("GEMINI_API_KEY")
MODEL = get_secret("GEMINI_MODEL", "gemini-3.8-flash")
APP_PASSWORD = get_secret("APP_PASSWORD", "")

# ---------- ACCESS ----------

if APP_PASSWORD:
    if not st.session_state.get("authenticated"):
        st.title("🔐 AI Writer Studio")
        password = st.text_input("Пароль доступа", type="password")

        if st.button("Войти"):
            if password == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Неверный пароль")

        st.stop()

if not API_KEY:
    st.error("Не настроен GEMINI_API_KEY в Secrets")
    st.stop()

client = genai.Client(api_key=API_KEY)

# ---------- AI ----------

def ask_ai(prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )

    if not response.text:
        raise RuntimeError("Модель вернула пустой ответ")

    return response.text.strip()


# ---------- RESEARCH AGENT ----------

def research(topic):

    queries = [
        topic,
        topic + " latest news statistics",
        topic + " research analysis official sources"
    ]

    results = []
    seen = set()

    for query in queries:
        try:
            with DDGS() as search:
                found = search.text(
                    query,
                    max_results=5
                )

            for item in found:
                url = item.get("href", "")

                if url and url not in seen:
                    seen.add(url)

                    results.append({
                        "title": item.get("title", ""),
                        "url": url,
                        "body": item.get("body", "")
                    })

        except Exception as error:
            st.warning(f"Ошибка поиска: {error}")

    return results


# ---------- ANALYST AGENT ----------

def analyze(topic, sources):

    material = "\n\n".join(
        f"[{i+1}] {s['title']}\n"
        f"URL: {s['url']}\n"
        f"{s['body']}"
        for i, s in enumerate(sources)
    )

    prompt = f"""
Ты аналитик исследовательской редакции.

ТЕМА:
{topic}

НАЙДЕННЫЕ ИСТОЧНИКИ:
{material}

ЗАДАЧИ:
1. Выдели главные факты.
2. Найди интересные закономерности.
3. Раздели подтверждённые сведения и гипотезы.
4. Укажи противоречия между источниками.
5. Определи, чего не хватает для полноценной статьи.

Не придумывай статистику.
Используй номера источников.
"""

    return ask_ai(prompt)


# ---------- WRITER AGENT ----------

def write_article(topic, analysis, sources, language, style, length):

    source_list = "\n".join(
        f"[{i+1}] {s['title']} - {s['url']}"
        for i, s in enumerate(sources)
    )

    prompt = f"""
Ты профессиональный автор аналитического издания.

Напиши полноценную статью.

ТЕМА: {topic}
ЯЗЫК: {language}
СТИЛЬ: {style}
ОБЪЁМ: {length} слов

АНАЛИТИЧЕСКИЙ ОТЧЁТ:
{analysis}

ИСТОЧНИКИ:
{source_list}

ТРЕБОВАНИЯ:
- Сильный и содержательный заголовок.
- Внятное введение.
- Логичная структура с подзаголовками.
- Аргументированное изложение.
- Конкретные факты и примеры.
- Никаких выдуманных цитат и цифр.
- Не выдавай предположения за факты.
- Добавляй ссылки на источники в формате [1], [2].
- Избегай повторов и искусственных вступлений.
- Не пиши о том, что ты искусственный интеллект.

Верни только готовую статью в Markdown.
"""

    return ask_ai(prompt)


# ---------- EDITOR AGENT ----------

def edit_article(article, analysis):

    prompt = f"""
Ты главный редактор аналитического издания.

ОТРЕДАКТИРУЙ СТАТЬЮ:

{article}

АНАЛИТИЧЕСКИЕ МАТЕРИАЛЫ:
{analysis}

ПРОВЕРЬ:
1. Логическую последовательность.
2. Фактическую аккуратность.
3. Повторы.
4. Слабые аргументы.
5. Качество заголовков.
6. Естественность языка.
7. Соответствие ссылок исходным материалам.

Не добавляй неподтверждённые факты.
Не удаляй ссылки на источники без причины.
Сохрани смысл и структуру.

Верни финальную статью в Markdown.
"""

    return ask_ai(prompt)


# ---------- EXPORT ----------

def create_docx(markdown):

    doc = Document()

    for line in markdown.splitlines():

        line = line.strip()

        if not line:
            continue

        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)

        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)

        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)

        elif line.startswith("- "):
            doc.add_paragraph(
                line[2:],
                style="List Bullet"
            )

        else:
            doc.add_paragraph(
                line.replace("**", "").replace("*", "")
            )

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()


# ---------- INTERFACE ----------

st.title("✍️ AI Writer Studio")

st.caption(
    "Автономная редакция на базе нескольких ИИ-агентов"
)

with st.sidebar:

    st.subheader("Настройки")

    language = st.selectbox(
        "Язык статьи",
        ["Русский", "English"]
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
        options=[500, 1000, 1500, 2000, 3000, 5000],
        value=2000
    )

    st.caption(f"Модель: {MODEL}")

topic = st.text_area(
    "О чём будем писать?",
    placeholder="Например: Будущее токенизации реальных активов на Solana...",
    height=120
)

if st.button("🚀 Запустить редакцию", type="primary"):

    if not topic.strip():
        st.error("Укажи тему статьи")
        st.stop()

    try:

        with st.status(
            "Редакция приступила к работе...",
            expanded=True
        ) as status:

            st.write("🔎 Агент 1: исследование источников")

            sources = research(topic)

            if not sources:
                raise RuntimeError(
                    "Не удалось найти источники. "
                    "Попробуй позже или измени тему."
                )

            st.write(
                f"Найдено источников: {len(sources)}"
            )

            st.write("🧠 Агент 2: аналитика")

            analysis = analyze(topic, sources)

            st.write("✍️ Агент 3: написание статьи")

            article = write_article(
                topic,
                analysis,
                sources,
                language,
                style,
                length
            )

            st.write("📝 Агент 4: редактура")

            final_article = edit_article(
                article,
                analysis
            )

            status.update(
                label="Статья готова!",
                state="complete"
            )

        st.session_state.article = final_article
        st.session_state.sources = sources
        st.session_state.analysis = analysis

    except Exception as error:
        st.error(f"Ошибка: {error}")

# ---------- RESULTS ----------

if st.session_state.get("article"):

    st.divider()

    st.subheader("📄 Готовая статья")

    st.markdown(st.session_state.article)

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            "Скачать Markdown",
            data=st.session_state.article,
            file_name="article.md",
            mime="text/markdown"
        )

    with col2:
        st.download_button(
            "Скачать Word",
            data=create_docx(
                st.session_state.article
            ),
            file_name="article.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    with st.expander("Исследование и источники"):

        st.markdown(st.session_state.analysis)

        for i, source in enumerate(
            st.session_state.sources,
            start=1
        ):
            st.markdown(
                f"{i}. [{source['title']}]({source['url']})"
            )
