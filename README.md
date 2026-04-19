# Restaurant AI Partner

> A natural language AI operations partner for small independent restaurants — built as a portfolio project.

---

## What This Is

Restaurant owners spend significant time on manual inventory tracking, recipe management, and sales analysis. Existing tools like MarketMan or WISK require tedious manual counting and offer no conversational interface. This app bridges that gap.

**Core concept:** Take a photo of your delivery invoice or closing receipt → AI parses it automatically → inventory and sales data update in real time. Then ask anything in plain language.

**Target user:** Small independent restaurant owners in Canada (under 50 staff), including immigrant-run restaurants where language flexibility matters.

---

## Features

### Implemented (MVP)

| Feature | Description |
|---------|-------------|
| **Natural Language Chat** | Ask about sales, stock levels, and ordering in plain English or Korean. Claude answers using live restaurant data injected into context. |
| **Recipe Registration** | Describe a recipe in natural language ("1 tbsp garlic, 200g chicken breast..."). Claude estimates quantities from vague units (a handful, a drizzle of, etc.) and shows a confirmation table before saving. Also works through the Chat interface. |
| **Invoice Vision Parsing** | Upload a delivery invoice photo → Claude Vision extracts line items → fuzzy-matched against existing inventory → review & confirm flow updates stock automatically. |
| **Receipt Vision Parsing** | Upload a closing sales receipt → Claude Vision extracts menu items sold → fuzzy-matched against recipes → confirm to record sales and deduct ingredient stock. |
| **Inventory Depletion Forecast** | Linear projection of days remaining per ingredient based on sales history. Dashboard shows ingredients that need reorder. |

### Architecture Highlights

- **Two-step confirm flow** for both invoice and receipt: Claude parses first, user reviews and edits, then DB write happens. No accidental data corruption.
- **Fuzzy ingredient matching** (SequenceMatcher, threshold 0.7) links scanned items to existing inventory without exact name matches.
- **Vague unit conversion**: Claude converts "a handful", "a pinch of", "half a block of tofu" into gram/ml values with reasoning shown to the user.
- **Multi-turn chat context**: Conversation history injected per session. Live inventory and sales data injected into system prompt based on keyword detection.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS (PWA) |
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL |
| AI | Claude Sonnet 4.6 (chat + recipe parsing) + Claude Vision (invoice/receipt) |
| Testing | pytest + SQLite in-memory with SAVEPOINT isolation |

---

## Project Structure

```
Restaurant-AI/
├── frontend/
│   └── src/
│       ├── api/          # fetch wrappers (chat, recipe, vision)
│       ├── components/   # ChatBubble, Navbar
│       └── pages/        # Chat, Dashboard, Recipe, Invoice, Receipt, Settings
├── backend/
│   ├── main.py           # FastAPI entry point + router registration
│   ├── routers/          # chat, recipe, invoice, receipt, vision, inventory
│   ├── services/         # claude, ingredient, recipe_svc, invoice, receipt, prediction
│   ├── models/           # SQLAlchemy ORM models
│   └── tests/            # 72 tests, all passing
└── docker-compose.yml
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL (or use Docker)
- Anthropic API key

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

uvicorn main:app --reload
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:5173
```

### Docker (PostgreSQL only)

```bash
docker-compose up -d
```

### Run Tests

```bash
cd backend
pytest tests/ -q
# Expected: 72 passed
```

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/message` | Send a chat message, get Claude's reply |
| GET | `/api/chat/history/{session_id}` | Retrieve conversation history |
| POST | `/api/recipe/preview` | Parse NL ingredient text, get fuzzy-matched preview |
| POST | `/api/recipe/confirm` | Save recipe + ingredient links to DB |
| GET | `/api/recipe/` | List all recipes |
| POST | `/api/vision/invoice/preview` | Parse invoice image, return items with match suggestions |
| POST | `/api/vision/invoice/confirm` | Persist reviewed invoice items, update stock |
| POST | `/api/vision/receipt/preview` | Parse receipt image, return items with recipe matches |
| POST | `/api/vision/receipt/confirm` | Persist sales, deduct ingredient stock |
| GET | `/api/inventory/` | List ingredients with forecast data |

---

## Roadmap

### Next Up
- [ ] Dashboard prediction cards — "Chicken breast runs out tomorrow evening" style depletion alerts surfaced in UI
- [ ] Reorder suggestions — auto-generate order list based on forecast + historical purchase quantities

### Planned
- [ ] Settings page — configure reorder thresholds, restaurant name/timezone
- [ ] Auth — single-user login (JWT) to protect data
- [ ] Push notifications — PWA push when ingredient hits reorder threshold
- [ ] Weekly summary — Claude-generated report sent by email or in-app
- [ ] Deployment — Vercel (frontend) + Railway (backend + PostgreSQL)

### Stretch Goals
- [ ] Multi-language support (English / Korean / Simplified Chinese) for the UI
- [ ] Weekday seasonality model for more accurate depletion forecasts
- [ ] Receipt scanning from POS export files (CSV) in addition to images

---

## Development Notes

- AI calls use `claude-sonnet-4-6` for all tasks (chat, recipe parsing, vision extraction)
- The Claude client is a module-level singleton — one connection per process
- All DB writes go through a confirm step; preview endpoints never write
- Tests use SQLite with SAVEPOINT isolation — each test rolls back automatically
- Vague unit conversion reference (~30 Korean + English expressions) is embedded in the recipe parsing prompt

---

## Competitive Context

| Tool | Gap |
|------|-----|
| MarketMan / WISK | Requires manual stock counts; no natural language interface |
| Restoke | Has vision parsing but no conversational AI; not targeting small operators |
| Square AI | Sales Q&A only; no inventory or ordering integration |

This project combines vision parsing + NL chat + inventory forecasting in a single lightweight PWA aimed specifically at small, often immigrant-run restaurants.

---

## Built With

- [Claude API](https://www.anthropic.com/) — Anthropic
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/) + [Vite](https://vitejs.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
