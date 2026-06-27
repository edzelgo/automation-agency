#!/usr/bin/env python3
"""
EmpowerAutomate — Instagram Outreach AI Agent

This agent manages your entire Instagram DM outreach pipeline:
- Add leads with their business info
- AI generates personalized DMs for each lead (using Claude API)
- Tracks message status, follow-ups, and responses
- Tells you exactly who to message each day
- Generates follow-up messages at the right intervals
- Tracks conversion metrics

Setup:
  1. pip install anthropic
  2. export ANTHROPIC_API_KEY="your-key-here"
  3. python3 ig_outreach_agent.py

The agent generates ready-to-send messages you copy into Instagram.
It does NOT send messages directly (that violates Instagram ToS and gets you banned).
"""

import json
import os
import sys
import textwrap
from datetime import datetime, timedelta

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_FILE = os.path.join(BASE_DIR, "ig_leads.json")
OUTREACH_LOG_FILE = os.path.join(BASE_DIR, "ig_outreach_log.json")

INDUSTRIES = {
    "contractor": {
        "label": "Contractor / HVAC",
        "pain_points": [
            "missing calls while on job sites",
            "losing leads to competitors who answer faster",
            "spending hours on estimates and follow-ups",
            "no-shows wasting half-days",
            "chasing clients for reviews",
        ],
        "results": [
            "went from missing 10+ calls/week to catching every one",
            "booked 40% more estimates with zero extra effort",
            "cut no-shows by 35% with automated reminders",
            "doubled Google reviews in 60 days",
            "saved 12 hours/week on admin and follow-ups",
        ],
        "value_per_lead": "$500–$5,000",
    },
    "lawyer": {
        "label": "Law Firm / Attorney",
        "pain_points": [
            "missing potential client calls during court or meetings",
            "intake process eating up paralegal time",
            "leads going cold because follow-up takes too long",
            "no system for qualifying cases before consultations",
            "spending hours on client status update calls",
        ],
        "results": [
            "went from missing 12+ calls/week to capturing every one",
            "automated intake saves 15 hours/week of paralegal time",
            "AI qualifies cases before they hit the attorney's calendar",
            "23 new consultations booked automatically in month one",
            "client satisfaction up — instant status updates 24/7",
        ],
        "value_per_lead": "$1,000–$10,000",
    },
    "creator": {
        "label": "Content Creator",
        "pain_points": [
            "spending 15+ hours/week on content admin",
            "can't keep up with posting on multiple platforms",
            "writing captions takes forever",
            "no time to engage with audience and grow",
            "inconsistent posting schedule hurting growth",
        ],
        "results": [
            "cut content admin from 15 hours to 2 hours/week",
            "AI writes captions in their exact brand voice",
            "auto-repurposes long-form into 5 short-form pieces",
            "consistent daily posting across 3 platforms",
            "freed up 10+ hours/week to focus on creating",
        ],
        "value_per_lead": "$200–$2,000",
    },
    "business": {
        "label": "General Small Business",
        "pain_points": [
            "drowning in admin tasks that don't make money",
            "leads falling through the cracks",
            "spending too much on staff for repetitive work",
            "can't scale without hiring more people",
            "no system for follow-ups and client communication",
        ],
        "results": [
            "automated 80% of admin tasks — like adding a $50K employee for $1,500/mo",
            "capturing every lead automatically with AI follow-up",
            "saved $4,000/mo by replacing manual processes with AI",
            "scaled from 20 to 50 clients without adding staff",
            "zero missed calls or forgotten follow-ups",
        ],
        "value_per_lead": "$500–$5,000",
    },
}

SEQUENCE_STAGES = [
    {"name": "initial", "label": "Initial DM", "wait_days": 0},
    {"name": "follow_up_1", "label": "Follow-Up #1", "wait_days": 2},
    {"name": "follow_up_2", "label": "Follow-Up #2 (Value Drop)", "wait_days": 5},
    {"name": "follow_up_3", "label": "Final Follow-Up (Breakup)", "wait_days": 10},
]

SYSTEM_PROMPT = """You are an AI outreach assistant for EmpowerAutomate, an AI automation agency.

Your job is to write Instagram DM messages that:
- Sound natural and human (not salesy or robotic)
- Are personalized to the specific lead's business
- Lead with curiosity and their pain points, not a pitch
- Are concise (under 80 words for cold DMs, under 100 for follow-ups)
- End with a question or soft CTA
- Never use emojis excessively (1-2 max)
- Never say "I'd love to" or "I was wondering if" — be direct but friendly

About EmpowerAutomate:
- We build AI automation systems for businesses (AI phone answering, automated follow-ups, content automation, chatbots)
- Our proof case: Built an AI system for a law firm that went from missing 12+ calls/week to capturing every one. AI answers calls 24/7, qualifies leads, books consultations automatically.
- Pricing: $1,500–$6,000/mo recurring
- Target: Contractors, law firms, content creators, busy professionals
- Founder's tone: Confident, casual, helpful. Talks like a smart friend, not a corporate salesperson."""


def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE, "r") as f:
            return json.load(f)
    return []


def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)


def load_log():
    if os.path.exists(OUTREACH_LOG_FILE):
        with open(OUTREACH_LOG_FILE, "r") as f:
            return json.load(f)
    return {"messages_generated": 0, "daily_stats": {}}


def save_log(log):
    with open(OUTREACH_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)


def log_activity(action):
    log = load_log()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in log["daily_stats"]:
        log["daily_stats"][today] = {"generated": 0, "leads_added": 0, "responses": 0, "booked": 0}
    if action == "generated":
        log["messages_generated"] += 1
        log["daily_stats"][today]["generated"] += 1
    elif action in log["daily_stats"][today]:
        log["daily_stats"][today][action] += 1
    save_log(log)


def generate_message_ai(lead, stage):
    if not HAS_ANTHROPIC:
        return generate_message_template(lead, stage)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return generate_message_template(lead, stage)

    client = anthropic.Anthropic(api_key=api_key)

    industry_info = INDUSTRIES.get(lead["industry"], INDUSTRIES["business"])
    history = lead.get("message_history", [])

    if stage == "initial":
        user_prompt = f"""Write an initial cold Instagram DM to this lead:

Name: {lead['name']}
Instagram: @{lead['instagram']}
Business: {lead['business_name']}
Industry: {industry_info['label']}
Location: {lead.get('location', 'Unknown')}
Notes: {lead.get('notes', 'None')}
Relationship: {lead.get('relationship', 'cold')} (cold = never interacted, warm = they follow us or engaged)

Their likely pain points: {', '.join(industry_info['pain_points'][:3])}

Rules:
- If warm: reference that they follow us or engaged with our content
- If cold: reference something specific about their business (use the notes field or their business name)
- Ask ONE question related to their biggest pain point
- Do NOT pitch in the first message
- Keep it under 80 words
- Sound like a real person texting, not a marketer"""

    elif stage == "follow_up_1":
        user_prompt = f"""Write a first follow-up Instagram DM. The initial message got no response.

Name: {lead['name']}
Business: {lead['business_name']}
Industry: {industry_info['label']}
Previous message sent: {history[-1]['content'] if history else 'Unknown'}

Rules:
- Keep it super short (under 50 words)
- Don't be pushy — just a friendly bump
- Add one small piece of value or a relevant result
- Example result you can mention: {industry_info['results'][0]}
- End with a low-pressure question"""

    elif stage == "follow_up_2":
        user_prompt = f"""Write a second follow-up Instagram DM. This is a value-drop message — give them something useful.

Name: {lead['name']}
Business: {lead['business_name']}
Industry: {industry_info['label']}
Notes: {lead.get('notes', 'None')}

Rules:
- Lead with a useful tip, stat, or insight relevant to their industry
- Subtly tie it back to what we do
- Don't reference that they haven't replied
- Keep it under 70 words
- Example results to weave in: {industry_info['results'][1]}"""

    elif stage == "follow_up_3":
        user_prompt = f"""Write a final "breakup" follow-up Instagram DM. This is the last message we'll send.

Name: {lead['name']}
Business: {lead['business_name']}
Industry: {industry_info['label']}

Rules:
- Acknowledge this is your last message
- Keep it light and friendly, not guilt-trippy
- Leave the door open for the future
- Mention one compelling result: {industry_info['results'][2]}
- Under 60 words"""

    else:
        return generate_message_template(lead, stage)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        message = response.content[0].text.strip()
        message = message.strip('"').strip("'")
        log_activity("generated")
        return message
    except Exception as e:
        print(f"\n  [AI Error: {e}]")
        print("  Falling back to template-based message.\n")
        return generate_message_template(lead, stage)


def generate_message_template(lead, stage):
    industry_info = INDUSTRIES.get(lead["industry"], INDUSTRIES["business"])
    name = lead["name"].split()[0]
    biz = lead["business_name"]
    warm = lead.get("relationship", "cold") == "warm"

    if stage == "initial":
        if warm:
            msg = (
                f"Hey {name}! Thanks for following along. "
                f"I noticed you're running {biz} — that's actually "
                f"one of the industries I build AI systems for.\n\n"
                f"Curious: what's the most repetitive, time-sucking "
                f"part of running your business right now?"
            )
        else:
            msg = (
                f"Hey {name}! Came across {biz} — "
                f"looks like you're doing solid work.\n\n"
                f"Quick question: {industry_info['pain_points'][0]}? "
                f"I built an AI system for a {industry_info['label'].lower()} that "
                f"{industry_info['results'][0]}.\n\n"
                f"Would you be open to a quick 10-min chat to see if "
                f"something like that could work for {biz}?"
            )
    elif stage == "follow_up_1":
        msg = (
            f"Hey {name}! Just bumping this in case it got buried — "
            f"I know DMs can be a jungle.\n\n"
            f"Quick win I just helped a {industry_info['label'].lower()} with: "
            f"{industry_info['results'][1]}.\n\n"
            f"Worth a chat? No pressure either way."
        )
    elif stage == "follow_up_2":
        msg = (
            f"Hey {name} — not trying to blow up your DMs, just thought "
            f"this might be useful:\n\n"
            f"Most {industry_info['label'].lower()}s I talk to don't realize "
            f"they're losing 20-30% of leads just from slow follow-up. "
            f"One of my clients {industry_info['results'][2]}.\n\n"
            f"Happy to share how if you're ever curious."
        )
    elif stage == "follow_up_3":
        msg = (
            f"Last one from me, {name} — I don't want to be that person.\n\n"
            f"If you ever want to explore AI automation for {biz}, "
            f"I'm always here. No expiration date.\n\n"
            f"Wishing you a great week!"
        )
    else:
        msg = f"Hey {name}! Just following up on our conversation about {biz}."

    log_activity("generated")
    return msg


def print_header(title):
    w = 62
    print("\n" + "=" * w)
    print(f"  {title}")
    print("=" * w)


def print_divider(title=""):
    w = 62
    if title:
        print(f"\n{'-' * w}\n  {title}\n{'-' * w}")
    else:
        print("-" * 62)


def wrap_message(msg, indent=4):
    lines = msg.split("\n")
    result = []
    for line in lines:
        if line.strip() == "":
            result.append("")
        else:
            wrapped = textwrap.fill(line, width=58, initial_indent=" " * indent, subsequent_indent=" " * indent)
            result.append(wrapped)
    return "\n".join(result)


def add_lead():
    print_divider("ADD NEW LEAD")
    name = input("  Full name: ").strip()
    if not name:
        print("  Cancelled.")
        return

    instagram = input("  Instagram handle (without @): ").strip().lstrip("@")
    business_name = input("  Business name: ").strip()

    print("\n  Industry:")
    for i, (key, val) in enumerate(INDUSTRIES.items(), 1):
        print(f"    {i}. {val['label']}")
    ind_choice = input("  Select (1-4): ").strip()
    industry_keys = list(INDUSTRIES.keys())
    try:
        industry = industry_keys[int(ind_choice) - 1]
    except (ValueError, IndexError):
        industry = "business"

    print("\n  Relationship:")
    print("    1. Cold (never interacted)")
    print("    2. Warm (they follow you or engaged with your content)")
    rel_choice = input("  Select (1-2): ").strip()
    relationship = "warm" if rel_choice == "2" else "cold"

    location = input("  Location (city/state, optional): ").strip()
    notes = input("  Notes (recent post, something specific about them): ").strip()

    lead = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + f"_{len(load_leads())}",
        "name": name,
        "instagram": instagram,
        "business_name": business_name,
        "industry": industry,
        "relationship": relationship,
        "location": location or "",
        "notes": notes or "",
        "status": "new",
        "current_stage": "initial",
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "last_contacted": None,
        "next_contact_date": datetime.now().strftime("%Y-%m-%d"),
        "message_history": [],
        "response_received": False,
        "audit_booked": False,
        "closed": False,
    }

    leads = load_leads()
    leads.append(lead)
    save_leads(leads)
    log_activity("leads_added")
    print(f"\n  Added: {name} (@{instagram}) — {INDUSTRIES[industry]['label']}")


def add_leads_bulk():
    print_divider("BULK ADD LEADS")
    print("  Enter leads in this format (one per line):")
    print("  Name | @instagram | Business Name | Industry (1-4) | cold/warm")
    print("  Industries: 1=Contractor, 2=Lawyer, 3=Creator, 4=Business")
    print("  Type 'done' when finished.\n")

    leads = load_leads()
    industry_keys = list(INDUSTRIES.keys())
    count = 0

    while True:
        line = input("  > ").strip()
        if line.lower() == "done":
            break
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            print("    Invalid format. Need at least: Name | @handle | Business")
            continue

        name = parts[0]
        instagram = parts[1].lstrip("@")
        business_name = parts[2]
        try:
            industry = industry_keys[int(parts[3]) - 1] if len(parts) > 3 else "business"
        except (ValueError, IndexError):
            industry = "business"
        relationship = parts[4] if len(parts) > 4 and parts[4] in ("cold", "warm") else "cold"

        lead = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S") + f"_{len(leads)}",
            "name": name,
            "instagram": instagram,
            "business_name": business_name,
            "industry": industry,
            "relationship": relationship,
            "location": "",
            "notes": "",
            "status": "new",
            "current_stage": "initial",
            "added_date": datetime.now().strftime("%Y-%m-%d"),
            "last_contacted": None,
            "next_contact_date": datetime.now().strftime("%Y-%m-%d"),
            "message_history": [],
            "response_received": False,
            "audit_booked": False,
            "closed": False,
        }
        leads.append(lead)
        count += 1
        log_activity("leads_added")
        print(f"    Added: {name} (@{instagram})")

    save_leads(leads)
    print(f"\n  {count} leads added.")


def get_todays_queue():
    leads = load_leads()
    today = datetime.now().strftime("%Y-%m-%d")
    queue = []
    for lead in leads:
        if lead["status"] in ("completed", "closed", "responded", "booked"):
            continue
        if lead.get("next_contact_date") and lead["next_contact_date"] <= today:
            queue.append(lead)
    queue.sort(key=lambda x: (x["current_stage"] != "initial", x["next_contact_date"]))
    return queue


def show_daily_queue():
    queue = get_todays_queue()
    print_header("TODAY'S OUTREACH QUEUE")

    if not queue:
        print("\n  No leads to contact today.")
        print("  Add new leads (option 1) or check back tomorrow.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    initial = [l for l in queue if l["current_stage"] == "initial"]
    follow_ups = [l for l in queue if l["current_stage"] != "initial"]

    print(f"\n  Date: {today}")
    print(f"  Total to contact: {len(queue)}")
    print(f"  New DMs: {len(initial)}  |  Follow-ups: {len(follow_ups)}")

    if initial:
        print_divider("NEW DMs TO SEND")
        for i, lead in enumerate(initial, 1):
            ind = INDUSTRIES.get(lead["industry"], INDUSTRIES["business"])
            rel = "WARM" if lead["relationship"] == "warm" else "COLD"
            print(f"\n  {i}. @{lead['instagram']} — {lead['name']}")
            print(f"     {lead['business_name']} | {ind['label']} | {rel}")
            if lead.get("notes"):
                print(f"     Notes: {lead['notes']}")

    if follow_ups:
        print_divider("FOLLOW-UPS DUE")
        for i, lead in enumerate(follow_ups, len(initial) + 1):
            stage_info = next((s for s in SEQUENCE_STAGES if s["name"] == lead["current_stage"]), None)
            stage_label = stage_info["label"] if stage_info else lead["current_stage"]
            print(f"\n  {i}. @{lead['instagram']} — {lead['name']}")
            print(f"     {lead['business_name']} | Stage: {stage_label}")
            if lead.get("last_contacted"):
                print(f"     Last contacted: {lead['last_contacted']}")

    print(f"\n  >> Select a lead number to generate their message (or 0 to go back)")
    choice = input("  Enter number: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(queue):
            generate_for_lead(queue[idx])
    except ValueError:
        pass


def generate_for_lead(lead):
    stage = lead["current_stage"]
    stage_info = next((s for s in SEQUENCE_STAGES if s["name"] == stage), SEQUENCE_STAGES[0])

    print_divider(f"GENERATING: {stage_info['label']}")
    print(f"  To: @{lead['instagram']} ({lead['name']})")
    print(f"  Business: {lead['business_name']}")

    if HAS_ANTHROPIC and os.environ.get("ANTHROPIC_API_KEY"):
        print("  Using AI personalization...")
    else:
        print("  Using template (set ANTHROPIC_API_KEY for AI personalization)")

    message = generate_message_ai(lead, stage)

    print(f"\n  {'.' * 58}")
    print(f"  MESSAGE TO COPY & SEND:")
    print(f"  {'.' * 58}\n")
    print(wrap_message(message))
    print(f"\n  {'.' * 58}")

    print("\n  Actions:")
    print("    1. Mark as SENT (I sent this message)")
    print("    2. Regenerate (give me a different version)")
    print("    3. Skip this lead for today")
    print("    4. Back to queue")

    action = input("\n  Choice: ").strip()

    if action == "1":
        mark_sent(lead, message)
    elif action == "2":
        generate_for_lead(lead)
    elif action == "3":
        leads = load_leads()
        for l in leads:
            if l["id"] == lead["id"]:
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                l["next_contact_date"] = tomorrow
        save_leads(leads)
        print("  Skipped — will show again tomorrow.")


def mark_sent(lead, message):
    leads = load_leads()
    today = datetime.now().strftime("%Y-%m-%d")

    for l in leads:
        if l["id"] == lead["id"]:
            l["message_history"].append({
                "stage": l["current_stage"],
                "content": message,
                "sent_date": today,
            })
            l["last_contacted"] = today
            l["status"] = "contacted"

            current_idx = next(
                (i for i, s in enumerate(SEQUENCE_STAGES) if s["name"] == l["current_stage"]),
                0
            )
            if current_idx < len(SEQUENCE_STAGES) - 1:
                next_stage = SEQUENCE_STAGES[current_idx + 1]
                l["current_stage"] = next_stage["name"]
                l["next_contact_date"] = (
                    datetime.now() + timedelta(days=next_stage["wait_days"])
                ).strftime("%Y-%m-%d")
            else:
                l["status"] = "completed"
                l["next_contact_date"] = None

            break

    save_leads(leads)
    print(f"\n  Marked as sent. Next follow-up scheduled.")


def generate_batch():
    queue = get_todays_queue()
    if not queue:
        print("\n  No leads in today's queue.")
        return

    print_header("BATCH MESSAGE GENERATION")
    print(f"\n  Generating messages for {len(queue)} leads...\n")

    results = []
    for i, lead in enumerate(queue, 1):
        stage = lead["current_stage"]
        stage_info = next((s for s in SEQUENCE_STAGES if s["name"] == stage), SEQUENCE_STAGES[0])
        print(f"  [{i}/{len(queue)}] @{lead['instagram']} — {stage_info['label']}...")

        message = generate_message_ai(lead, stage)
        results.append({"lead": lead, "message": message, "stage_label": stage_info["label"]})

    print_divider("ALL MESSAGES READY")
    for i, r in enumerate(results, 1):
        lead = r["lead"]
        print(f"\n  --- {i}. @{lead['instagram']} ({lead['name']}) — {r['stage_label']} ---\n")
        print(wrap_message(r["message"]))
        print()

    export = input("\n  Export all to a text file? (y/n): ").strip().lower()
    if export == "y":
        export_file = os.path.join(BASE_DIR, f"outreach_batch_{datetime.now().strftime('%Y%m%d')}.txt")
        with open(export_file, "w") as f:
            f.write(f"EmpowerAutomate — Outreach Batch — {datetime.now().strftime('%A, %B %d, %Y')}\n")
            f.write("=" * 60 + "\n\n")
            for i, r in enumerate(results, 1):
                lead = r["lead"]
                f.write(f"--- {i}. @{lead['instagram']} ({lead['name']}) — {r['stage_label']} ---\n\n")
                f.write(r["message"] + "\n\n\n")
        print(f"  Exported to: {export_file}")

    mark_all = input("  Mark all as sent? (y/n): ").strip().lower()
    if mark_all == "y":
        for r in results:
            mark_sent(r["lead"], r["message"])
        print(f"  All {len(results)} messages marked as sent.")


def record_response():
    leads = load_leads()
    active = [l for l in leads if l["status"] == "contacted" and not l["response_received"]]

    if not active:
        print("\n  No active leads waiting for responses.")
        return

    print_divider("RECORD A RESPONSE")
    for i, lead in enumerate(active, 1):
        print(f"  {i}. @{lead['instagram']} — {lead['name']} ({lead['business_name']})")
        print(f"     Last contacted: {lead['last_contacted']} | Stage: {lead['current_stage']}")

    choice = input("\n  Select lead number: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(active):
            lead = active[idx]
            print(f"\n  What did @{lead['instagram']} say?")
            print("    1. Interested — wants to chat")
            print("    2. Asked a question")
            print("    3. Said 'not now' / 'maybe later'")
            print("    4. Not interested / negative")
            print("    5. Booked an audit call!")

            resp = input("  Choice: ").strip()

            for l in leads:
                if l["id"] == lead["id"]:
                    l["response_received"] = True
                    log_activity("responses")

                    if resp == "1":
                        l["status"] = "responded"
                        l["next_contact_date"] = datetime.now().strftime("%Y-%m-%d")
                        print("\n  Send them your Calendly link to book a Free Automation Audit!")
                    elif resp == "2":
                        l["status"] = "responded"
                        l["next_contact_date"] = datetime.now().strftime("%Y-%m-%d")
                        note = input("  What was their question? ").strip()
                        l["notes"] = l.get("notes", "") + f" | Q: {note}"
                        print("\n  Answer their question, then steer toward booking an audit call.")
                    elif resp == "3":
                        l["status"] = "nurture"
                        l["next_contact_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                        print("\n  Moved to nurture — will resurface in 30 days.")
                    elif resp == "4":
                        l["status"] = "completed"
                        l["next_contact_date"] = None
                        print("\n  Marked as not interested. Moving on.")
                    elif resp == "5":
                        l["status"] = "booked"
                        l["audit_booked"] = True
                        l["next_contact_date"] = None
                        log_activity("booked")
                        print("\n  NICE! Audit call booked. Go close that deal!")

            save_leads(leads)
    except (ValueError, IndexError):
        print("  Invalid selection.")


def show_pipeline():
    leads = load_leads()
    log = load_log()

    print_header("OUTREACH PIPELINE DASHBOARD")

    statuses = {}
    for lead in leads:
        s = lead["status"]
        statuses[s] = statuses.get(s, 0) + 1

    total = len(leads)
    contacted = sum(1 for l in leads if l["last_contacted"])
    responded = sum(1 for l in leads if l["response_received"])
    booked = sum(1 for l in leads if l["audit_booked"])
    closed = sum(1 for l in leads if l["closed"])

    print(f"\n  Total leads:       {total}")
    print(f"  Contacted:         {contacted}")
    print(f"  Responses:         {responded}")
    print(f"  Audits booked:     {booked}")
    print(f"  Clients closed:    {closed}")

    if contacted > 0:
        print(f"\n  Response rate:     {responded/contacted*100:.0f}%")
    if responded > 0:
        print(f"  Book rate:         {booked/responded*100:.0f}%")

    print(f"\n  Messages generated (all time): {log.get('messages_generated', 0)}")

    print_divider("PIPELINE BY STATUS")
    status_labels = {
        "new": "New (not contacted)",
        "contacted": "Contacted (awaiting response)",
        "responded": "Responded (hot lead!)",
        "nurture": "Nurture (follow up later)",
        "booked": "Audit Booked",
        "closed": "Client Closed",
        "completed": "Completed (no interest)",
    }
    for status, label in status_labels.items():
        count = statuses.get(status, 0)
        if count > 0:
            bar = "#" * min(count, 30)
            print(f"  {label:38s} {bar} {count}")

    print_divider("BY INDUSTRY")
    for key, info in INDUSTRIES.items():
        count = sum(1 for l in leads if l["industry"] == key)
        responded_ind = sum(1 for l in leads if l["industry"] == key and l["response_received"])
        if count > 0:
            print(f"  {info['label']:28s} {count} leads | {responded_ind} responses")

    today = datetime.now().strftime("%Y-%m-%d")
    today_stats = log.get("daily_stats", {}).get(today, {})
    if today_stats:
        print_divider("TODAY'S ACTIVITY")
        print(f"  Messages generated: {today_stats.get('generated', 0)}")
        print(f"  Leads added:        {today_stats.get('leads_added', 0)}")
        print(f"  Responses recorded: {today_stats.get('responses', 0)}")
        print(f"  Audits booked:      {today_stats.get('booked', 0)}")


def manage_leads():
    leads = load_leads()
    if not leads:
        print("\n  No leads yet. Add some first!")
        return

    print_divider("ALL LEADS")
    for i, lead in enumerate(leads, 1):
        ind = INDUSTRIES.get(lead["industry"], INDUSTRIES["business"])
        status_icon = {
            "new": "[ ]", "contacted": "[~]", "responded": "[!]",
            "booked": "[*]", "closed": "[$]", "completed": "[x]",
            "nurture": "[z]",
        }.get(lead["status"], "[ ]")
        print(f"  {i}. {status_icon} @{lead['instagram']} — {lead['name']}")
        print(f"      {lead['business_name']} | {ind['label']} | {lead['status']}")

    print("\n  Actions:")
    print("    e [num] — Edit lead notes")
    print("    d [num] — Delete lead")
    print("    v [num] — View full lead details")
    print("    0 — Back")

    action = input("\n  > ").strip().lower()
    parts = action.split()

    if len(parts) == 2:
        cmd = parts[0]
        try:
            idx = int(parts[1]) - 1
            if 0 <= idx < len(leads):
                if cmd == "d":
                    name = leads[idx]["name"]
                    confirm = input(f"  Delete {name}? (y/n): ").strip().lower()
                    if confirm == "y":
                        leads.pop(idx)
                        save_leads(leads)
                        print(f"  Deleted {name}.")
                elif cmd == "e":
                    new_notes = input(f"  New notes for {leads[idx]['name']}: ").strip()
                    leads[idx]["notes"] = new_notes
                    save_leads(leads)
                    print("  Notes updated.")
                elif cmd == "v":
                    lead = leads[idx]
                    print(f"\n  Name:         {lead['name']}")
                    print(f"  Instagram:    @{lead['instagram']}")
                    print(f"  Business:     {lead['business_name']}")
                    print(f"  Industry:     {INDUSTRIES.get(lead['industry'], {}).get('label', lead['industry'])}")
                    print(f"  Relationship: {lead['relationship']}")
                    print(f"  Location:     {lead.get('location', 'N/A')}")
                    print(f"  Notes:        {lead.get('notes', 'N/A')}")
                    print(f"  Status:       {lead['status']}")
                    print(f"  Stage:        {lead['current_stage']}")
                    print(f"  Added:        {lead['added_date']}")
                    print(f"  Last contact: {lead['last_contacted'] or 'Never'}")
                    print(f"  Next contact: {lead.get('next_contact_date') or 'N/A'}")
                    if lead["message_history"]:
                        print(f"\n  Message History:")
                        for msg in lead["message_history"]:
                            print(f"    [{msg['sent_date']}] {msg['stage']}:")
                            print(wrap_message(msg["content"], indent=6))
                            print()
        except (ValueError, IndexError):
            print("  Invalid selection.")


def generate_reply():
    """Generate a reply to a lead who responded with a specific message."""
    leads = load_leads()
    responded = [l for l in leads if l["status"] == "responded"]

    if not responded:
        print("\n  No responded leads to reply to.")
        return

    print_divider("GENERATE REPLY")
    for i, lead in enumerate(responded, 1):
        print(f"  {i}. @{lead['instagram']} — {lead['name']} ({lead['business_name']})")

    choice = input("\n  Select lead: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(responded):
            lead = responded[idx]
            their_reply = input(f"\n  What did @{lead['instagram']} say? Paste their message:\n  > ").strip()

            if not their_reply:
                print("  Cancelled.")
                return

            if HAS_ANTHROPIC and os.environ.get("ANTHROPIC_API_KEY"):
                client = anthropic.Anthropic()
                industry_info = INDUSTRIES.get(lead["industry"], INDUSTRIES["business"])
                history_text = "\n".join(
                    f"  You ({msg['stage']}): {msg['content']}" for msg in lead.get("message_history", [])
                )

                prompt = f"""Write a reply to this lead's Instagram DM response.

Lead info:
- Name: {lead['name']}
- Business: {lead['business_name']}
- Industry: {industry_info['label']}

Conversation so far:
{history_text}

Their response: "{their_reply}"

Rules:
- Respond naturally to what they said
- If they're interested: steer toward booking a Free Automation Audit call, mention you can show them exactly what you'd automate in their business
- If they asked a question: answer it concisely, then tie back to booking a call
- If they said something positive about a pain point: validate it, share a quick relevant result, suggest a call
- Keep it under 80 words
- Sound human and conversational
- Include your Calendly link placeholder: [CALENDLY_LINK]"""

                try:
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=300,
                        system=SYSTEM_PROMPT,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    message = response.content[0].text.strip().strip('"').strip("'")
                    log_activity("generated")
                except Exception as e:
                    print(f"\n  [AI Error: {e}]")
                    message = (
                        f"That's exactly what I hear from a lot of {industry_info['label'].lower()}s. "
                        f"One of my clients {industry_info['results'][0]} after we set things up.\n\n"
                        f"Would you be down for a quick 10-min call? I'll show you exactly "
                        f"what I'd build for {lead['business_name']} — no commitment.\n\n"
                        f"Here's my calendar: [CALENDLY_LINK]"
                    )
            else:
                industry_info = INDUSTRIES.get(lead["industry"], INDUSTRIES["business"])
                message = (
                    f"That's exactly what I hear from a lot of {industry_info['label'].lower()}s. "
                    f"One of my clients {industry_info['results'][0]} after we set things up.\n\n"
                    f"Would you be down for a quick 10-min call? I'll show you exactly "
                    f"what I'd build for {lead['business_name']} — no commitment.\n\n"
                    f"Here's my calendar: [CALENDLY_LINK]"
                )

            print(f"\n  {'.' * 58}")
            print(f"  REPLY TO COPY & SEND:")
            print(f"  {'.' * 58}\n")
            print(wrap_message(message))
            print(f"\n  {'.' * 58}")
            print("\n  (Replace [CALENDLY_LINK] with your actual Calendly link)")

    except (ValueError, IndexError):
        print("  Invalid selection.")


def main_menu():
    print_header("EMPOWERAUTOMATE — IG OUTREACH AGENT")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y')}")

    queue = get_todays_queue()
    leads = load_leads()
    hot = sum(1 for l in leads if l["status"] == "responded")

    print(f"\n  Leads in queue today:  {len(queue)}")
    print(f"  Total leads:           {len(leads)}")
    if hot > 0:
        print(f"  HOT LEADS (responded): {hot}  <-- Follow up NOW!")

    print(f"""
  {'=' * 58}
  OUTREACH
    1. Show today's queue & generate messages
    2. Generate ALL messages (batch mode)
    3. Generate a reply to a response

  LEADS
    4. Add a lead
    5. Bulk add leads
    6. Manage leads (view/edit/delete)

  TRACKING
    7. Record a response
    8. Pipeline dashboard

  0. Exit
  {'=' * 58}""")

    choice = input("\n  Enter choice: ").strip()

    if choice == "1":
        show_daily_queue()
    elif choice == "2":
        generate_batch()
    elif choice == "3":
        generate_reply()
    elif choice == "4":
        add_lead()
    elif choice == "5":
        add_leads_bulk()
    elif choice == "6":
        manage_leads()
    elif choice == "7":
        record_response()
    elif choice == "8":
        show_pipeline()
    elif choice == "0":
        print("\n  Go get those clients. Talk tomorrow.\n")
        sys.exit(0)
    else:
        print("  Invalid choice.")

    input("\n  Press Enter to continue...")
    main_menu()


if __name__ == "__main__":
    if not HAS_ANTHROPIC:
        print("\n  NOTE: 'anthropic' package not installed.")
        print("  Using template-based messages (still good!).")
        print("  For AI-personalized messages: pip install anthropic")
        print("  Then: export ANTHROPIC_API_KEY='your-key'\n")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  NOTE: ANTHROPIC_API_KEY not set.")
        print("  Using template-based messages (still good!).")
        print("  For AI-personalized messages: export ANTHROPIC_API_KEY='your-key'\n")

    main_menu()
