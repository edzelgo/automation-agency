# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

EmpowerAutomate is a two-part project:

1. **Static marketing website** (`index.html` + `styles.css` + `script.js`) — a single-page agency site with no build step, no framework, and no dependencies.
2. **`daily_agent.py`** — a Python 3 CLI tool the founder runs each morning to see their current business phase, top 3 priorities for the day, and track milestone progress.

The markdown files (`BUSINESS-PLAN.md`, `SCALING-ROADMAP.md`, `INSTAGRAM-STRATEGY.md`) are business planning documents, not code. The agent script references `SCALING-ROADMAP.md` by name in some output strings.

## Running Things

**Website**: No build step. Open `index.html` directly in a browser, or serve with any static file server:
```bash
python3 -m http.server 8080
```

**Daily agent**:
```bash
python3 daily_agent.py
```

The agent has no external dependencies — only Python stdlib (`json`, `os`, `datetime`). It persists state to `agent_data.json` in the same directory (this file is runtime state, not committed).

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

## Key Conventions

- The business has 5 phases. Phase indices (0–4) map to the `PHASES` list. When adding or reordering phases, update both the list and any hardcoded `elif data["current_phase"] == N` blocks in `get_top_3()`.
- Service pricing shown in `index.html` should stay in sync with the pricing table in `BUSINESS-PLAN.md`.
- The contact form (`#contactForm`) submits to nothing — replacing the `alert()` with a real form handler (e.g. Formspree, Netlify Forms) is an expected future task.
