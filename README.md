# AI Writer Studio

**AI-powered research and writing platform for Crypto, Web3, DeFi, RWA and X (Twitter) content.**

AI Writer Studio is a Streamlit-based application designed to research topics, analyze collected information, generate long-form articles and prepare content for publication on X.

The project is focused on creating research-driven content rather than generic AI-generated articles.

---

## Project status

| Component | Status |
|---|---|
| Streamlit web interface | Implemented |
| Gemini API integration | Implemented |
| OpenRouter fallback | Implemented |
| DuckDuckGo search | Implemented |
| AI research pipeline | Implemented |
| Article generation | Implemented |
| AI editing | Implemented |
| Session history | Implemented |
| Markdown export | Implemented |
| DOCX export | Implemented |
| Streamlit Cloud deployment | Implemented |
| Modular architecture 3.0 | Planned |
| Full webpage content extraction | Planned |
| Advanced source verification | Planned |
| X Articles API integration | Planned |
| Automatic publishing to X | Planned |
| Publication scheduler | Planned |
| Persistent database | Planned |

**Current version: 2.0**

Version 2.0 is deployed on Streamlit Community Cloud. The next development stage is the transition to a modular architecture (3.0).

---

# 1. Currently implemented

## 1.1. Web interface

The application uses Streamlit as its frontend.

Current interface includes:

- Password-protected access.
- Article generation interface.
- Research and analysis tabs.
- Source information tab.
- Execution logs.
- Generated content history within the current session.

## 1.2. AI providers

Two AI providers are integrated:

**Primary provider:**
- Google Gemini API.

**Fallback provider:**
- OpenRouter Free.

Implemented functionality:

- Automatic fallback when the primary provider fails.
- Retry handling.
- Basic request logging.
- Error handling.

The application is designed to work within free API limits, although provider availability and usage quotas may change.

## 1.3. Web research

DuckDuckGo search integration is implemented.

Current functionality:

- Search for information related to the requested topic.
- Collect search result snippets.
- Remove duplicate results.
- Pass collected information to the AI research pipeline.

**Current limitation:** the application primarily works with search snippets rather than extracting and analyzing the complete content of source webpages.

## 1.4. AI writing pipeline

The current generation process consists of four sequential stages:

1. **Research**: collects relevant information about the selected topic.
2. **Analysis**: processes the collected information and identifies important points.
3. **Writer**: generates the article based on the research results.
4. **Editor**: reviews and improves the generated text.

The pipeline has already been tested on a real topic:

`Solana RWA: what is actually happening in 2026?`

The application successfully generated an English-language article.

## 1.5. Export

Generated content can currently be exported in:

- Markdown (`.md`)
- Microsoft Word (`.docx`)

## 1.6. Deployment

The application is deployed using Streamlit Community Cloud.

Current deployment setup:

- GitHub repository integration.
- Automatic application deployment.
- Dependencies managed through `requirements.txt`.
- API credentials configured through Streamlit secrets.

---

# 2. Current limitations

The current implementation is functional, but it is still an early version.

The following limitations need to be addressed:

- Research relies heavily on search snippets.
- Full webpage extraction and content parsing are not implemented.
- Source URLs are not consistently included in generated articles.
- Independent fact-checking is not yet implemented.
- Important numerical claims may be generated without sufficient verification.
- Source reliability and publication dates are not systematically evaluated.
- No persistent database is available.
- Generated history is stored in Streamlit session state and is not guaranteed to survive a new session.
- There is no direct integration with X publishing functionality.

The current application should therefore be treated as a content generation tool, not yet as a fully automated research and publishing platform.

---

# 3. Planned development: AI Writer Studio 3.0

The next major version will introduce a modular architecture, specialized AI agents and a more reliable research workflow.

## 3.1. Modular architecture

Move away from the current monolithic application structure.

Proposed architecture:

```text
ai-writer-studio/
│
├── app.py
├── requirements.txt
├── .gitignore
│
├── core/
│   ├── ai_engine.py
│   ├── orchestrator.py
│   └── state.py
│
├── agents/
│   ├── research_manager.py
│   ├── market_researcher.py
│   ├── project_researcher.py
│   ├── institutional_researcher.py
│   ├── source_analyst.py
│   ├── fact_checker.py
│   ├── x_strategist.py
│   ├── writer.py
│   └── editor.py
│
├── services/
│   ├── search.py
│   ├── web_reader.py
│   └── exporter.py
│
└── prompts/
    ├── research.md
    ├── fact_check.md
    ├── x_article.md
    └── editor.md
```

Each module will have a clearly defined responsibility.

## 3.2. Specialized AI agents

The new pipeline will use dedicated agents instead of relying on a single general-purpose generation sequence.

| Agent | Responsibility |
|---|---|
| Research Manager | Coordinates the research process |
| Market Researcher | Analyzes market data and trends |
| Project Researcher | Investigates protocols, products and ecosystems |
| Institutional Researcher | Studies institutional adoption and partnerships |
| Source Analyst | Evaluates source quality and relevance |
| Fact Checker | Checks factual claims and numerical data |
| X Strategist | Defines the article structure and editorial angle |
| Writer | Produces the final article |
| Editor | Reviews language, structure and consistency |

The orchestration layer will manage the order of execution and preserve intermediate results.

## 3.3. Advanced research engine

Planned improvements:

- Full webpage extraction.
- HTML parsing and content cleaning.
- Publication date detection.
- Direct source URL collection.
- Duplicate source detection.
- Source credibility assessment.
- Primary and secondary source classification.
- Research notes and evidence storage.
- Better handling of conflicting information.

The research engine should prioritize official documentation, project announcements, institutional publications, blockchain analytics and independent research.

## 3.4. Fact-checking system

A dedicated fact-checking stage will be introduced.

Each important claim should include:

- Original statement.
- Source URL.
- Source publication date.
- Date of the underlying data.
- Source type.
- Verification status.
- Notes and limitations.

Proposed verification labels:

- `VERIFIED`
- `PARTIALLY VERIFIED`
- `UNVERIFIED`

The system should distinguish between confirmed facts, estimates, forecasts, announcements and speculative statements.

The goal is to reduce fabricated statistics, unsupported conclusions and misleading claims.

## 3.5. X content generation

The application will be optimized specifically for X rather than traditional SEO writing.

Supported content formats:

- X Articles.
- Twitter Threads.
- Single Posts.
- Research Posts.
- Market Commentary.

Planned writing styles:

- Researcher.
- Analyst.
- Technical.
- Educational.
- Casual / Community.

Primary content categories:

- Crypto.
- Web3.
- Solana.
- DeFi.
- RWA.
- Blockchain infrastructure.
- Tokenization.
- Institutional adoption.

The writing engine should produce natural, readable content without generic AI phrasing, unnecessary hype or promotional language.

---

# 4. X (Twitter) publishing integration

One of the planned major features is direct publishing to X.

The application should eventually be able to publish generated articles through the official X API.

## Planned functionality

- Connect an X account using OAuth.
- Store authentication credentials securely.
- Prepare content for publishing.
- Create X Article drafts where supported by the API.
- Publish supported content formats.
- Receive the publication result.
- Save the published article URL.
- Maintain publication history.
- Prevent accidental duplicate publications.

## Publishing modes

**Manual approval**

The AI generates and checks the article. The user reviews it and manually confirms publication.

**Automatic publishing**

The system completes research, fact-checking, writing and editing, then publishes according to configured rules.

**Scheduled publishing**

The user selects a publication date and time. The application queues the content and publishes it according to the schedule.

### Important API consideration

X API access, supported endpoints and pricing must be checked before implementation.

Full X Articles publishing should only be considered implemented after the required API access and publishing workflow have been successfully tested.

---

# 5. Persistent storage

The current session-based history will eventually be replaced with persistent storage.

Planned capabilities:

- Save research sessions.
- Store generated articles.
- Store source references.
- Save fact-checking results.
- Maintain editing history.
- Track publication statuses.
- Retrieve previously generated content.

A database solution will be selected during the implementation stage.

---

# 6. Export and content management

Planned improvements:

- Better Markdown formatting.
- Improved DOCX export.
- Save drafts.
- Edit generated articles before publication.
- Compare article versions.
- Export research notes and source lists.
- Store final published versions.

---

# 7. Development roadmap

The proposed implementation order:

| Stage | Work | Priority |
|---|---|---|
| 1 | Modularize the existing application | High |
| 2 | Implement centralized AI engine | High |
| 3 | Implement research orchestration | High |
| 4 | Build full webpage extraction | High |
| 5 | Introduce specialized research agents | High |
| 6 | Implement source analysis | High |
| 7 | Implement fact-checking | High |
| 8 | Improve X Article generation | High |
| 9 | Add persistent storage | Medium |
| 10 | Implement X API authorization | Medium |
| 11 | Implement X publishing | Medium |
| 12 | Add scheduled publishing | Medium |
| 13 | Improve analytics and content management | Low |

---

# 8. Technology stack

| Technology | Purpose |
|---|---|
| Python | Backend |
| Streamlit | Web interface |
| Google Gemini API | Primary AI provider |
| OpenRouter | Alternative AI provider |
| DuckDuckGo Search | Web search |
| Requests | HTTP requests |
| BeautifulSoup | HTML parsing |
| Trafilatura | Webpage content extraction |
| Pydantic | Data validation |
| python-docx | DOCX export |
| GitHub | Source code management |
| Streamlit Community Cloud | Application hosting |
| X API | Planned publishing integration |

The project aims to remain within a $0 operating budget wherever possible, using free API tiers and free hosting options. Paid API features will be treated as optional dependencies rather than assumed requirements.

---

# 9. Project objective

The long-term goal is to build an AI-powered editorial platform that can independently:

1. Receive a topic or research question.
2. Search for relevant information.
3. Analyze projects, markets and institutions.
4. Collect and evaluate sources.
5. Verify important facts and figures.
6. Develop an editorial angle.
7. Generate a high-quality X Article.
8. Review and edit the final content.
9. Prepare the article for publication.
10. Publish it to X after approval or according to a configured schedule.

**The main principle: research first, verify second, write third, publish last.**

AI Writer Studio should become a research-driven content production system, not just another AI text generator.

---

*This README describes the current implementation status and the proposed development roadmap. Planned features are not considered implemented until they are integrated and tested.*
