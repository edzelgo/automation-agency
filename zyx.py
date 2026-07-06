#!/usr/bin/env python3
"""
Zyx — Autonomous Executive Assistant for EmpowerAutomate

Usage:
  python3 zyx.py                        Morning briefing (default)
  python3 zyx.py chat                   Talk to Zyx
  python3 zyx.py think                  Zyx generates ideas autonomously
  python3 zyx.py launch                 View all launches
  python3 zyx.py launch new             Plan a new launch
  python3 zyx.py launch complete NAME   Mark a launch complete
  python3 zyx.py ideas                  View saved idea bank
  python3 zyx.py goals                  View weekly goals
  python3 zyx.py goals set GOAL         Add a weekly goal
  python3 zyx.py goals done             Mark a goal complete
  python3 zyx.py email                  Send morning briefing by email only
  python3 zyx.py help                   Show this help

Email setup (Gmail):
  export ZYX_EMAIL_FROM="you@gmail.com"
  export ZYX_EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
  export ZYX_EMAIL_TO="you@gmail.com"   # optional, defaults to FROM

  Get an App Password at: myaccount.google.com → Security → App passwords
  When set, morning briefings are emailed automatically in addition to
  printing to the terminal. Use 'python3 zyx.py email' with cron to
  have Zyx email you every morning without opening a terminal.
"""

import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from anthropic import Anthropic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DATA_FILE = os.path.join(BASE_DIR, "agent_data.json")
ZYX_MEMORY_FILE = os.path.join(BASE_DIR, "zyx_memory.json")

MODEL = "claude-sonnet-4-6"

PHASES = [
    {"name": "Phase 1: Foundation",              "revenue_target": 4500,  "client_target": 3,  "months": "1-2"},
    {"name": "Phase 2: Validate & Systematize",  "revenue_target": 10000, "client_target": 6,  "months": "3-4"},
    {"name": "Phase 3: Scale with Systems",       "revenue_target": 30000, "client_target": 15, "months": "5-8"},
    {"name": "Phase 4: Build the Machine",        "revenue_target": 60000, "client_target": 23, "months": "9-14"},
    {"name": "Phase 5: Million-Dollar Run",       "revenue_target": 83333, "client_target": 25, "months": "15-20"},
]

ZYX_SYSTEM = """You are Zyx — the autonomous executive assistant for EmpowerAutomate, an AI automation agency run by a solo founder building from $1,700 to $1,000,000.

YOUR ROLE:
You are not a chatbot. You are the founder's business partner, strategist, and operations lead. You own the roadmap, push the launches, generate the ideas, and keep the founder focused on the highest-leverage work.

YOUR PERSONALITY:
- Sharp and direct — you cut to what matters, no fluff
- Entrepreneurial — you think in clients, revenue, and momentum
- Proactive — you flag problems and opportunities before the founder sees them
- Opinionated — you have a point of view and you defend it
- Honest — you say what's true, not what's comfortable

YOUR COMMUNICATION STYLE:
- Lead with the most important thing
- Use specific numbers, names, and dates — never vague language
- End every response with one clear next action
- Occasionally call the founder "boss" but don't overdo it
- No bullet-point soup — write like an intelligent human, not a report generator
- When you have an idea, say it directly and explain why it will work

BUSINESS CONTEXT:
EmpowerAutomate sells done-for-you AI automation to law firms, contractors/HVAC, busy professionals, and content creators. Services range from $1,500–$6,000/mo retainers. The tech stack includes Make.com, n8n, Zapier, Vapi, GoHighLevel, and custom GPT chatbots. The main sales channel right now is Instagram (8K followers) and warm network outreach. The first proof of concept is Mike's law firm/medical project."""


# ─── Data helpers ────────────────────────────────────────────────────────────

def load_agent_data():
    if os.path.exists(AGENT_DATA_FILE):
        with open(AGENT_DATA_FILE) as f:
            return json.load(f)
    return {
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "current_phase": 0,
        "current_mrr": 0,
        "current_clients": 0,
        "completed_milestones": [],
        "daily_log": [],
    }


def load_zyx_memory():
    if os.path.exists(ZYX_MEMORY_FILE):
        with open(ZYX_MEMORY_FILE) as f:
            return json.load(f)
    return {
        "ideas": [],
        "launches": [],
        "weekly_goals": [],
        "flags": [],
        "last_briefing_date": None,
        "conversation_history": [],
    }


def save_zyx_memory(memory):
    with open(ZYX_MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def build_business_context(data, memory):
    phase = PHASES[data["current_phase"]]
    start = datetime.strptime(data["start_date"], "%Y-%m-%d")
    days_in = (datetime.now() - start).days
    gap = max(0, phase["revenue_target"] - data["current_mrr"])
    clients_needed = max(0, phase["client_target"] - data["current_clients"])

    active_launches = [l for l in memory["launches"] if l["status"] == "active"]
    open_goals = [g for g in memory["weekly_goals"] if not g.get("done")]
    flags = memory.get("flags", [])

    lines = [
        f"DATE: {datetime.now().strftime('%A, %B %d, %Y')}",
        f"DAY: {days_in} into the journey",
        "",
        f"PHASE: {phase['name']} (months {phase['months']})",
        f"MRR: ${data['current_mrr']:,}/mo — target ${phase['revenue_target']:,}/mo — gap ${gap:,}/mo",
        f"CLIENTS: {data['current_clients']} active — need {clients_needed} more to hit phase target",
        f"MILESTONES COMPLETED: {len(data['completed_milestones'])}",
    ]

    if active_launches:
        lines.append("")
        lines.append("ACTIVE LAUNCHES:")
        for l in active_launches:
            lines.append(f"  • {l['name']} — started {l['start_date']}, target: {l.get('target_date') or 'TBD'}")

    if open_goals:
        lines.append("")
        lines.append("OPEN WEEKLY GOALS:")
        for g in open_goals[-5:]:
            lines.append(f"  • {g['goal']}")

    if flags:
        lines.append("")
        lines.append("ACTIVE FLAGS:")
        for flag in flags[-5:]:
            lines.append(f"  ⚑ {flag['text']} (flagged {flag['date']})")

    return "\n".join(lines)


# ─── Email ───────────────────────────────────────────────────────────────────

def _briefing_to_html(text, ctx):
    """Convert plain-text briefing to a clean HTML email."""
    lines = text.split("\n")
    html_lines = []
    for line in lines:
        stripped = line.strip()
        # Section headers are lines like "SITUATION —" or "TODAY'S TOP 3 —"
        if stripped and stripped == stripped.upper() and len(stripped) > 3:
            html_lines.append(
                f'<p style="margin:24px 0 6px;font-size:11px;font-weight:700;'
                f'letter-spacing:1.5px;color:#6b7280;text-transform:uppercase;">'
                f'{stripped}</p>'
            )
        elif stripped.startswith(("1.", "2.", "3.")):
            html_lines.append(
                f'<p style="margin:6px 0 6px 16px;font-size:15px;color:#111827;">'
                f'{stripped}</p>'
            )
        elif stripped:
            html_lines.append(
                f'<p style="margin:4px 0;font-size:15px;line-height:1.6;color:#111827;">'
                f'{stripped}</p>'
            )
        else:
            html_lines.append('<div style="height:8px;"></div>')

    date_str = datetime.now().strftime("%A, %B %d, %Y")
    body = "\n".join(html_lines)

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td style="background:#0f172a;border-radius:12px 12px 0 0;padding:28px 36px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:3px;color:#94a3b8;text-transform:uppercase;margin-bottom:6px;">Your Executive Assistant</div>
          <div style="font-size:26px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">ZYX</div>
          <div style="font-size:13px;color:#64748b;margin-top:4px;">Morning Briefing &nbsp;·&nbsp; {date_str}</div>
        </td></tr>

        <!-- Body -->
        <tr><td style="background:#ffffff;padding:32px 36px;">
          {body}
        </td></tr>

        <!-- Stats bar -->
        <tr><td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 36px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="font-size:11px;color:#94a3b8;">EmpowerAutomate</td>
              <td align="right" style="font-size:11px;color:#94a3b8;">Reply to this email to talk to Zyx</td>
            </tr>
          </table>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:16px 36px;">
          <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;">
            Sent by Zyx &nbsp;·&nbsp; Your autonomous executive assistant &nbsp;·&nbsp; EmpowerAutomate
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_briefing_email(briefing_text, ctx):
    """Send the morning briefing via Gmail SMTP. Silent no-op if env vars not set."""
    email_from = os.environ.get("ZYX_EMAIL_FROM", "").strip()
    app_password = os.environ.get("ZYX_EMAIL_APP_PASSWORD", "").strip()
    email_to = os.environ.get("ZYX_EMAIL_TO", email_from).strip()

    if not email_from or not app_password:
        return  # email not configured — skip silently

    date_str = datetime.now().strftime("%A, %B %d")
    subject = f"Zyx · Morning Briefing — {date_str}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Zyx (EmpowerAutomate) <{email_from}>"
    msg["To"] = email_to

    # Plain-text fallback
    msg.attach(MIMEText(briefing_text, "plain"))
    # HTML version
    msg.attach(MIMEText(_briefing_to_html(briefing_text, ctx), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_from, app_password)
            server.sendmail(email_from, email_to, msg.as_string())
        print(f"  [Email sent to {email_to}]\n")
    except Exception as e:
        print(f"  [Email failed: {e}]\n")


# ─── Modes ───────────────────────────────────────────────────────────────────

def morning_briefing(client, data, memory, send_email=True):
    ctx = build_business_context(data, memory)

    print()
    print("═" * 62)
    print("  ZYX  ·  MORNING BRIEFING")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y')}")
    print("═" * 62)
    print()

    prompt = f"""BUSINESS STATE:
{ctx}

Give me my morning briefing. Structure it as:

SITUATION — one sharp sentence on where we actually stand right now (not a recap, a diagnosis)

TODAY'S TOP 3 — three specific actions for today. Not "do outreach" — give me exactly who to contact, what to say, or what to build.

THIS WEEK'S BIG MOVE — one high-leverage thing I should be driving toward over the next 7 days and why

WATCH OUT — one risk, gap, or blind spot I need to know about

Keep the whole thing tight. I read this in 60 seconds over coffee."""

    with client.messages.stream(
        model=MODEL,
        max_tokens=900,
        system=ZYX_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response_text = ""
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_text += text

    print("\n")

    if send_email:
        send_briefing_email(response_text, ctx)

    memory["last_briefing_date"] = datetime.now().strftime("%Y-%m-%d")
    if "briefing_log" not in memory:
        memory["briefing_log"] = []
    memory["briefing_log"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "content": response_text,
    })
    memory["briefing_log"] = memory["briefing_log"][-7:]
    save_zyx_memory(memory)


def chat_mode(client, data, memory):
    ctx = build_business_context(data, memory)

    # Restore conversation history (last 20 turns)
    history = memory.get("conversation_history", [])[-20:]

    print()
    print("═" * 62)
    print("  ZYX  ·  CHAT")
    print("  Commands: 'exit' · 'flag: TEXT' · 'idea: TEXT' · 'clear'")
    print("═" * 62)
    print()
    print("Zyx: I'm here. What do you need?\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nZyx: Got it. Go execute.\n")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye", "done"):
            print("\nZyx: Got it. Go execute.\n")
            break

        if user_input.lower() == "clear":
            history = []
            memory["conversation_history"] = []
            save_zyx_memory(memory)
            print("Zyx: Memory cleared.\n")
            continue

        if user_input.lower().startswith("flag:"):
            flag_text = user_input[5:].strip()
            if "flags" not in memory:
                memory["flags"] = []
            memory["flags"].append({"text": flag_text, "date": datetime.now().strftime("%Y-%m-%d")})
            save_zyx_memory(memory)
            print("Zyx: Flagged. I'll keep that on my radar.\n")
            continue

        if user_input.lower().startswith("idea:"):
            idea_text = user_input[5:].strip()
            memory["ideas"].append({
                "idea": idea_text,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source": "manual",
            })
            save_zyx_memory(memory)
            print("Zyx: Saved to the idea bank.\n")
            continue

        # Build messages — inject context on first message of session
        messages = history.copy()
        content = user_input
        if not history:
            content = f"[BUSINESS CONTEXT]\n{ctx}\n\n{user_input}"
        messages.append({"role": "user", "content": content})

        with client.messages.stream(
            model=MODEL,
            max_tokens=1500,
            system=ZYX_SYSTEM,
            messages=messages,
        ) as stream:
            response_text = ""
            print("\nZyx: ", end="", flush=True)
            for text in stream.text_stream:
                print(text, end="", flush=True)
                response_text += text
            print("\n")

        # Persist history (store original user input, not context-injected)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response_text})
        memory["conversation_history"] = history[-40:]
        save_zyx_memory(memory)


def think_mode(client, data, memory):
    ctx = build_business_context(data, memory)

    print()
    print("═" * 62)
    print("  ZYX  ·  AUTONOMOUS THINK SESSION")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y')}")
    print("═" * 62)
    print()

    prompt = f"""BUSINESS STATE:
{ctx}

You have free rein to think about EmpowerAutomate. No prompt from the boss — just you working on the business.

Produce:

CONTENT IDEAS (3) — specific Instagram Reel or carousel concepts. Give me the hook line, the angle, and the niche it targets.

LEAD GEN PLAY — one outreach or lead generation tactic we haven't tried yet. Be specific about who, how, and what to say.

BOTTLENECK — the single thing most likely to stall growth right now, and what to do about it.

NEW OFFER IDEA — one service, package, or upsell worth testing in the next 30 days. Include the name, price point, and who it's for.

HIGHEST LEVERAGE MOVE — your single recommendation for the next 7 days. The one thing that, if done well, compounds everything else.

Think like you own the business. Be specific enough that each item could be acted on today."""

    with client.messages.stream(
        model=MODEL,
        max_tokens=1800,
        system=ZYX_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        response_text = ""
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_text += text

    print("\n")

    memory["ideas"].append({
        "idea": f"[Think session {datetime.now().strftime('%Y-%m-%d')}]",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "think_session",
        "full": response_text,
    })
    save_zyx_memory(memory)
    print("  [Session saved to zyx_memory.json  ·  python3 zyx.py ideas to review]\n")


def launch_mode(client, data, memory, args):
    ctx = build_business_context(data, memory)
    sub = args[1] if len(args) > 1 else "status"

    if sub == "status" or sub == "list":
        launches = memory.get("launches", [])
        if not launches:
            print("\nZyx: No launches yet. Start one: python3 zyx.py launch new\n")
            return
        print()
        print("═" * 62)
        print("  ZYX  ·  LAUNCH TRACKER")
        print("═" * 62)
        for l in launches:
            icon = "🟢" if l["status"] == "active" else ("✓" if l["status"] == "complete" else "⏸")
            print(f"\n  {icon}  {l['name']}")
            print(f"     Status: {l['status']}  |  Started: {l['start_date']}  |  Target: {l.get('target_date') or 'TBD'}")
            if l.get("notes"):
                print(f"     Last note: {l['notes'][-1]['text']}")
        print()
        return

    if sub == "new":
        print()
        print("═" * 62)
        print("  ZYX  ·  NEW LAUNCH PLAN")
        print("═" * 62)
        print()
        launch_name = input("  What are we launching? ").strip()
        if not launch_name:
            return
        target_date = input("  Target date (YYYY-MM-DD or Enter to skip): ").strip() or None

        prompt = f"""BUSINESS STATE:
{ctx}

We're planning a launch: "{launch_name}"
Target date: {target_date or 'TBD'}

Build me a complete launch plan:

WHAT IT IS — one paragraph on what this launch is, who it's for, and what success looks like.

PRE-LAUNCH (list these in order with day counts, e.g. "Day 1–3: ...", "Day 4–5: ...")

LAUNCH DAY CHECKLIST — everything that needs to happen on the day itself

POST-LAUNCH (days 1–7 after launch) — follow-up actions to convert interest into revenue

SUCCESS METRIC — the single number that tells us if this worked and what it needs to be

Think like a launch manager who has done this 50 times. Be specific."""

        with client.messages.stream(
            model=MODEL,
            max_tokens=1800,
            system=ZYX_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            plan_text = ""
            print()
            print("Zyx: ", end="", flush=True)
            for text in stream.text_stream:
                print(text, end="", flush=True)
                plan_text += text
            print("\n")

        launch = {
            "name": launch_name,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "target_date": target_date,
            "status": "active",
            "plan": plan_text,
            "notes": [],
        }
        memory["launches"].append(launch)
        save_zyx_memory(memory)
        print(f"  [Launch '{launch_name}' saved  ·  python3 zyx.py launch to track]\n")
        return

    if sub == "note" and len(args) >= 3:
        # python3 zyx.py launch note "launch name" text...
        # Find by partial name match
        name_query = args[2].lower()
        note_text = " ".join(args[3:]) if len(args) > 3 else input("  Note: ").strip()
        for l in memory["launches"]:
            if name_query in l["name"].lower():
                if "notes" not in l:
                    l["notes"] = []
                l["notes"].append({"date": datetime.now().strftime("%Y-%m-%d"), "text": note_text})
                save_zyx_memory(memory)
                print(f"\nZyx: Note added to '{l['name']}'.\n")
                return
        print(f"\nZyx: No launch matching '{name_query}'.\n")
        return

    if sub == "complete" and len(args) >= 3:
        name_query = " ".join(args[2:]).lower()
        for l in memory["launches"]:
            if name_query in l["name"].lower():
                l["status"] = "complete"
                l["completed_date"] = datetime.now().strftime("%Y-%m-%d")
                save_zyx_memory(memory)
                print(f"\nZyx: '{l['name']}' marked complete. Good work.\n")
                return
        print(f"\nZyx: No launch matching '{name_query}'.\n")
        return

    print(f"\nZyx: Unknown launch command '{sub}'. Try: launch, launch new, launch complete NAME\n")


def ideas_mode(memory):
    ideas = memory.get("ideas", [])
    if not ideas:
        print("\nZyx: No ideas yet. Run 'python3 zyx.py think' to generate some.\n")
        return

    print()
    print("═" * 62)
    print(f"  ZYX  ·  IDEA BANK  ({len(ideas)} saved)")
    print("═" * 62)
    print()

    for idea in reversed(ideas):
        date = idea.get("date", "?")
        source = idea.get("source", "manual")
        if source == "think_session":
            print(f"  [{date}] THINK SESSION")
            full = idea.get("full", "")
            preview = full[:400].replace("\n", "\n  ")
            print(f"  {preview}{'...' if len(full) > 400 else ''}")
        else:
            print(f"  [{date}] {idea.get('idea', '')}")
        print()


def goals_mode(client, data, memory, args):
    sub = args[1] if len(args) > 1 else "list"

    if sub == "set":
        goal_text = " ".join(args[2:]) if len(args) > 2 else input("  Goal: ").strip()
        if not goal_text:
            return
        if "weekly_goals" not in memory:
            memory["weekly_goals"] = []
        memory["weekly_goals"].append({
            "goal": goal_text,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "done": False,
        })
        save_zyx_memory(memory)
        print(f"\nZyx: Goal locked in — '{goal_text}'\n")
        return

    if sub == "done":
        open_goals = [g for g in memory.get("weekly_goals", []) if not g.get("done")]
        if not open_goals:
            print("\nZyx: No open goals.\n")
            return
        print()
        for i, g in enumerate(open_goals, 1):
            print(f"  {i}. [{g['date']}] {g['goal']}")
        print()
        try:
            sel = int(input("  Mark done (number): ").strip()) - 1
            open_goals[sel]["done"] = True
            save_zyx_memory(memory)
            print(f"\nZyx: Done. ✓\n")
        except (ValueError, IndexError):
            print("  Invalid.\n")
        return

    # Default: list
    goals = memory.get("weekly_goals", [])
    if not goals:
        print("\nZyx: No goals set. Use: python3 zyx.py goals set YOUR GOAL\n")
        return

    print()
    print("═" * 62)
    print("  ZYX  ·  WEEKLY GOALS")
    print("═" * 62)
    print()
    for g in goals[-15:]:
        icon = "✓" if g.get("done") else "○"
        print(f"  {icon}  [{g['date']}]  {g['goal']}")
    print()


def print_help():
    print(__doc__)


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    mode = args[0] if args else "morning"

    if mode == "help":
        print_help()
        return

    if mode == "ideas":
        ideas_mode(load_zyx_memory())
        return

    if mode == "goals" and (len(args) < 2 or args[1] == "list"):
        goals_mode(None, load_agent_data(), load_zyx_memory(), args)
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n  Zyx needs your Anthropic API key to think.")
        print("  Run: export ANTHROPIC_API_KEY=your_key_here\n")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    data = load_agent_data()
    memory = load_zyx_memory()

    if mode in ("morning", "brief", "briefing"):
        morning_briefing(client, data, memory, send_email=True)
    elif mode == "email":
        # Email-only mode: generate briefing and send it, no terminal output needed for cron
        morning_briefing(client, data, memory, send_email=True)
    elif mode == "chat":
        chat_mode(client, data, memory)
    elif mode == "think":
        think_mode(client, data, memory)
    elif mode == "launch":
        launch_mode(client, data, memory, args)
    elif mode == "goals":
        goals_mode(client, data, memory, args)
    else:
        print(f"\nZyx: Unknown command '{mode}'. Run 'python3 zyx.py help' for options.\n")


if __name__ == "__main__":
    main()
