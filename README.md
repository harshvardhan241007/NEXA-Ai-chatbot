# NEXA AI Chatbot

An advanced, modular Python AI chatbot — evolved from a simple rule-based
script into an LLM-capable assistant with conversation memory, intent
detection, built-in tools, document Q&A (RAG), a SQLite database, a
FastAPI backend, and a web chat UI. CLI mode is preserved for terminal use.

Works **fully offline with zero API keys** (local fallback mode) and can be
upgraded to a real LLM by simply adding an API key to `.env`.

## Features

- **LLM integration** — OpenAI or Anthropic, chosen via `.env`, called
  through plain REST (`requests`), no vendor SDK lock-in.
- **Local fallback mode** — if no API key is set, or the API call fails
  for any reason, NEXA answers using a rule-based responder (the original
  keyword-dictionary logic is preserved) so it **never crashes and always
  replies**.
- **Conversation memory** — every message is persisted in SQLite and
  short-term history is fed back into the LLM prompt as context.
- **Intent detection** — lightweight regex/keyword classifier routes each
  message to greeting / farewell / calculator / date-time / document-Q&A /
  general conversation.
- **Tools**
  - Safe calculator — parses expressions with Python's `ast` module and a
    whitelist of operators. **No `eval()`/`exec()` anywhere in the
    project.**
  - Date/Time tool — answers "what's the date/time/day/month/year".
- **Document reading + RAG** — upload a `.txt` or `.pdf`, NEXA chunks it
  and retrieves the most relevant chunks with a from-scratch TF-IDF
  index (numpy only — no external embeddings API required), then feeds
  them to the LLM (or, in fallback mode, returns the best excerpt
  directly).
- **FastAPI backend** — `/api/chat`, `/api/upload`, `/api/history/{id}`,
  `/api/health`, serving a modern HTML/JS chat UI.
- **CLI mode** — the original terminal experience (name → time-based
  greeting → question loop → `bye` to exit), now backed by the same
  engine as the web app.
- **SQLite database** for conversations/messages.
- **Logging** to file + console with configurable level.
- **`.env`-based configuration** — no secrets hard-coded anywhere.
- **pytest test suite** — 34 tests covering the calculator (including
  rejecting `eval()`-style injection attempts), intent detection, memory,
  RAG retrieval, and full chatbot flows.
- **Dockerfile** for containerized deployment.

## Project structure

```
nexa_ai_chatbot/
├── app/
│   ├── api.py          # FastAPI app (web backend)
│   ├── cli.py           # Terminal chat mode
│   ├── chatbot.py        # Orchestrator: intent -> tool/RAG/LLM/fallback
│   ├── config.py          # .env-driven settings
│   ├── database.py         # SQLite connection + schema
│   ├── fallback.py          # Original dictionary-based local responder
│   ├── file_reader.py        # .txt / .pdf loading
│   ├── intents.py              # Rule-based intent detector
│   ├── llm.py                   # OpenAI / Anthropic REST client (fails soft)
│   ├── logger.py                 # Logging setup
│   ├── memory.py                  # Conversation memory (SQLite-backed)
│   └── tools.py                    # Safe calculator + date/time tool
├── static/index.html      # Web chat UI
├── tests/                 # pytest suite (34 tests)
├── data/                   # SQLite DB + logs (gitignored)
├── uploads/                # Uploaded documents (gitignored)
├── main.py                # Entry point: `cli` or `api` mode
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
└── README.md
```

## What was preserved from the original `nexa.py`

- Asking for the user's name.
- Time-of-day greeting logic (Morning/Afternoon/Evening/Night).
- The original keyword → canned-response dictionary (`how are you`,
  `who are you`, `motivate me`, `happy`, ...) — now used as the offline
  fallback responder in `app/fallback.py`.
- The "type BYE to exit" question loop, now in `app/cli.py`.

## Installation

```bash
git clone <your-repo-url>
cd nexa_ai_chatbot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## `.env` setup

```bash
cp .env.example .env
```

Leave `LLM_PROVIDER=none` (default) to run entirely offline with no API
key. To enable a real LLM, edit `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

or

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Never commit `.env` — it's already in `.gitignore`.

## Run

**CLI mode** (terminal chat, same feel as the original script):
```bash
python main.py cli
```

**API + Web UI**:
```bash
python main.py api
# then open http://localhost:8000
```
or directly with uvicorn:
```bash
uvicorn app.api:app --reload
```

## Testing

```bash
pytest
```

34 tests covering the calculator (including injection-style inputs being
safely rejected), intent detection, memory persistence, RAG chunking &
retrieval, and full chatbot conversations.

## Docker

```bash
docker build -t nexa-chatbot .
docker run -p 8000:8000 --env-file .env nexa-chatbot
```

## GitHub upload

```bash
git init
git add .
git commit -m "NEXA AI Chatbot v2 - modular, LLM-ready, RAG, FastAPI, tests"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Notes / honesty

- This was built and verified in a sandboxed, network-disabled
  environment. All core logic — calculator, intents, memory, RAG,
  fallback responder, PDF/TXT reading, and the full CLI — was executed
  directly and a 34-test suite was run against it (all passing). The
  FastAPI server itself could not be started in that sandbox because
  `fastapi`/`uvicorn` aren't available without internet access; the code
  follows standard, well-established FastAPI patterns, but please run
  `pytest` and `python main.py api` yourself after `pip install -r
  requirements.txt` to confirm on your machine before deploying.
- The RAG implementation is a lightweight, dependency-free TF-IDF
  retriever — good for small/medium documents and demos. For large-scale
  production RAG, swap `app/rag.py`'s index for a real vector database
  (e.g. Chroma, pgvector, Pinecone).
## Render deployment

This project includes `render.yaml` and a Dockerfile configured for a Render Web Service.

1. Push the project to GitHub/GitLab.
2. In Render, create a **New → Web Service** and connect the repository.
3. Choose **Docker** (the included `render.yaml` can also be used as a Blueprint).
4. Set `LLM_PROVIDER` to `openai` if using OpenAI and add `OPENAI_API_KEY` as a Render secret.
5. Deploy and verify `https://<your-service>.onrender.com/api/health`.

The app listens on Render's `PORT` environment variable and uses `/api/health` for health checks. Render services use an ephemeral filesystem by default, so this SQLite database and uploaded documents will not survive restarts/redeploys unless you configure persistent storage or move the data to a managed datastore.
