# TripPlanner AI

A multi-agent trip planner built with **LangGraph**, **Groq (Llama)**, **Aviationstack**, **Tavily** and **Flask**.
Enter your route, dates, budget and interests, and four AI agents run in sequence to produce a complete travel plan.

## How it works

```
START → flight_agent → hotel_agent → itinerary_agent → final_agent → END
```

| Agent | Tools | Job |
|-------|-------|-----|
| Flight agent | `search_flights` (Aviationstack), `web_search` (Tavily) | Finds flight options for the route |
| Hotel agent | `web_search` | Finds budget, mid-range and premium stays |
| Itinerary agent | `web_search` | Builds a day-by-day plan around flights and hotels |
| Final response agent | none | Merges everything into one Markdown plan |

Each agent's output is stored in shared graph state and passed to the next one. The Flask backend streams progress to the browser as each agent finishes, so the status board updates live.

## Project structure

```
trip_planner/
├── app.py              # Flask server and streaming /api/plan endpoint
├── backend.py          # LangGraph state, agents, nodes and graph
├── requirements.txt
├── .env                # API keys (never commit this)
├── README.md
├── static/
│   ├── styles.css
│   └── script.js       # Form handling, streaming reader, Markdown rendering
├── template/
│   └── index.html
└── tools/
    ├── __init__.py
    ├── flight.py       # Aviationstack flight lookup tool
    └── search.py       # Tavily web search tool
```

## Prerequisites

- Python 3.10+
- Free API keys:
  - **Groq**: https://console.groq.com/keys
  - **Aviationstack**: https://aviationstack.com
  - **Tavily**: https://tavily.com

## Setup

```bash
cd trip_planner
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Edit `.env` and add your keys:

```env
GROQ_API_KEY=your-groq-api-key
MODEL_NAME=llama-3.3-70b-versatile
AVIATIONSTACK_API_KEY=your-aviationstack-key
AVIATIONSTACK_BASE_URL=http://api.aviationstack.com/v1
TAVILY_API_KEY=your-tavily-key
```

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000, fill in the form and click **Plan my trip**. A full plan takes roughly 30 to 90 seconds because each agent makes several tool calls.

## Configuration

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Groq API key for the LLM |
| `MODEL_NAME` | Groq model. `llama-3.3-70b-versatile` (best quality) or `llama-3.1-8b-instant` (higher limits, weaker tool use) |
| `AVIATIONSTACK_API_KEY` | Flight data |
| `AVIATIONSTACK_BASE_URL` | Use `https://...` only on a paid Aviationstack plan |
| `TAVILY_API_KEY` | Web search |

## Known limitations and troubleshooting

- **Aviationstack free plan** only supports `http` and returns real-time and recent flights, not future schedules. Treat flight times as indicative and verify before booking. The agent falls back to Tavily for typical airlines and fares.
- **Groq 429 / rate-limit errors**: the free tier has tight tokens-per-minute limits. The client retries automatically; if it still fails, wait a minute and try again, or switch to `llama-3.1-8b-instant`.
- **Agent skips tools or sends bad arguments**: smaller Llama models are less reliable at tool calling. Use the 70B model.
- **`Error: ... API_KEY is not set`**: check `.env` is in the project root and you started the app from that folder.
- **`create_react_agent` deprecation warning** on newer LangGraph: harmless. You can migrate to `langchain.agents.create_agent` later.
- Prices and availability come from web search and can be out of date or wrong. Always verify before booking.

## Customizing

- **Swap the LLM**: edit `_llm()` in `backend.py` and the provider package in `requirements.txt`.
- **Add an agent**: write a node function, call `g.add_node(...)` and `g.add_edge(...)` in `build_graph()`, then add a row to the status board in `template/index.html` and the `ORDER` list in `static/script.js`.
- **Add a tool**: create it in `tools/` with the `@tool` decorator, export it in `tools/__init__.py`, and pass it to the relevant agent in `backend.py`.

## Security

Keep `.env` out of version control (add it to `.gitignore`) and never expose your keys in the frontend. `app.run(debug=True)` is for development only; use a production server such as gunicorn when deploying.
