# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

EmpowerAutomate is a three-part project:

1. **Static marketing website** (`index.html` + `styles.css` + `script.js`) — a single-page agency site with no build step, no framework, and no dependencies.
2. **`daily_agent.py`** — a simple Python 3 CLI (stdlib only) the founder runs each morning for phase tracking and daily priorities. No AI calls.
3. **`zyx.py`** — the autonomous executive assistant powered by the Claude API. Handles morning briefings, interactive chat, autonomous idea generation, launch planning, and goal tracking. This is the primary AI layer.

The markdown files (`BUSINESS-PLAN.md`, `SCALING-ROADMAP.md`, `INSTAGRAM-STRATEGY.md`) are business planning documents, not code. `daily_agent.py` references `SCALING-ROADMAP.md` by name in some output strings.

## Running Things

**Website**: No build step. Open `index.html` directly in a browser, or serve with any static file server:
```bash
python3 -m http.server 8080
```

**Daily agent** (no API key needed):
```bash
python3 daily_agent.py
```

**Zyx — autonomous executive assistant** (requires Anthropic API key):
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here

python3 zyx.py                        # morning briefing
python3 zyx.py chat                   # interactive conversation
python3 zyx.py think                  # autonomous idea generation
python3 zyx.py launch new             # plan a launch
python3 zyx.py launch                 # view all launches
python3 zyx.py launch complete NAME   # mark launch complete
python3 zyx.py launch note NAME TEXT  # add a note to a launch
python3 zyx.py ideas                  # view saved idea bank
python3 zyx.py goals set GOAL         # set a weekly goal
python3 zyx.py goals done             # mark a goal complete
```

`daily_agent.py` persists state to `agent_data.json`. `zyx.py` persists its own memory (ideas, launches, goals, conversation history, briefing log) to `zyx_memory.json`. Neither file is committed — both are runtime state.

## Architecture: daily_agent.py

The script is structured around a single `PHASES` list (lines 14–202) containing all five business phases hardcoded. Each phase has:
- `revenue_target`, `client_target`, `months`
- `roles` — the 2–3 hats the founder wears at that phase
- `daily_tasks` — a dict keyed by role name, each containing a list of task strings
- `milestones` — ordered list of checkpoint strings

**State** (`agent_data.json`):
```json
{
  "start_date": "YYYY-MM-DD",
  "current_phase": 0,
  "current_mrr": 0,
  "current_clients": 0,
  "completed_milestones": [],
  "daily_log": []
}
```

`completed_milestones` stores milestone strings (not indices), so milestone text must match exactly between the `PHASES` list and the saved JSON when editing.

The `interactive_menu()` function is the entry point and calls itself recursively for the menu loop (no explicit loop construct). `get_top_3()` generates priority strings based on `current_phase` and `current_clients` — this logic at lines 253–305 is where phase-specific coaching lives.

## Architecture: Website

The site is a single scrolling page with anchor-linked sections: `#services`, `#niches`, `#process`, `#pricing`, `#contact`. All styling is in `styles.css` with no CSS framework. `script.js` handles three things only: mobile nav toggle, smooth scroll for anchor links, and the contact form submission (currently just an `alert()` — no backend).

## Architecture: zyx.py

`zyx.py` uses the Anthropic Python SDK with streaming (`client.messages.stream`). All Claude calls share a single system prompt (`ZYX_SYSTEM`) that defines the Zyx persona — direct, opinionated, business-focused. Business state is pulled from `agent_data.json` and assembled into a plain-text `build_business_context()` block that gets prepended to every prompt.

**Modes and their prompting strategy:**
- `morning` — single-turn, tight format prompt (situation / top 3 / big move / watch out), max 900 tokens
- `chat` — multi-turn with persisted `conversation_history` (last 40 messages stored in `zyx_memory.json`); business context only injected on the first turn of a session
- `think` — single-turn autonomous session that generates content ideas, a lead gen play, a bottleneck diagnosis, a new offer idea, and a highest-leverage recommendation; full response saved to idea bank
- `launch new` — single-turn prompt that builds a structured launch plan (pre-launch timeline, launch day checklist, post-launch actions, success metric)

**Memory schema** (`zyx_memory.json`):
```json
{
  "ideas": [{"idea": "...", "date": "...", "source": "manual|think_session", "full": "..."}],
  "launches": [{"name": "...", "start_date": "...", "target_date": "...", "status": "active|complete", "plan": "...", "notes": []}],
  "weekly_goals": [{"goal": "...", "date": "...", "done": false}],
  "flags": [{"text": "...", "date": "..."}],
  "conversation_history": [],
  "briefing_log": [],
  "last_briefing_date": "..."
}
```

The `PHASES` list in `zyx.py` must stay in sync with the one in `daily_agent.py` — both define the same 5-phase roadmap and are read independently.

## Key Conventions

- The business has 5 phases. Phase indices (0–4) map to the `PHASES` list. When adding or reordering phases, update both the list and any hardcoded `elif data["current_phase"] == N` blocks in `get_top_3()`.
- Service pricing shown in `index.html` should stay in sync with the pricing table in `BUSINESS-PLAN.md`.
- The contact form (`#contactForm`) submits to nothing — replacing the `alert()` with a real form handler (e.g. Formspree, Netlify Forms) is an expected future task.
