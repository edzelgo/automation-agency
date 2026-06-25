#!/usr/bin/env python3
"""
EmpowerAutomate Daily Action Agent
Run this every morning: python3 daily_agent.py
It tells you your current phase, top 3 priorities, and tracks progress.
"""

import json
import os
from datetime import datetime, timedelta

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_data.json")

PHASES = [
    {
        "name": "Phase 1: Foundation",
        "revenue_target": 4500,
        "client_target": 3,
        "months": "1-2",
        "roles": ["Salesperson", "Builder", "Content Creator"],
        "daily_tasks": {
            "Salesperson": [
                "Send 10 outreach DMs to business owners you know personally",
                "Follow up with every open conversation from yesterday",
                "Book or conduct 1 Free Automation Audit call",
                "Post 1 Instagram story showing your work or a client result",
                "Comment on 10 posts from contractors/lawyers/creators",
            ],
            "Builder": [
                "Build or improve 1 automation system for a client or demo",
                "Record a 60-second Loom showing an automation in action",
                "Document your build process into a reusable SOP/template",
            ],
            "Content Creator": [
                "Create and post 1 Reel or carousel for Instagram",
                "Write 3 captions/hooks for upcoming posts",
                "Engage in 2 Facebook groups (provide value, no pitching)",
            ],
        },
        "milestones": [
            "Listed 30+ business owners I know",
            "Sent outreach to entire warm network",
            "Recorded Loom demo of Mike's project",
            "Rebranded Instagram (bio, pic, pinned posts)",
            "Set up Calendly for Free Automation Audit",
            "Got first paying client",
            "Got second paying client",
            "Got third paying client",
            "Collected first testimonial",
            "Created case study from Mike's project",
        ],
    },
    {
        "name": "Phase 2: Validate & Systematize",
        "revenue_target": 10000,
        "client_target": 6,
        "months": "3-4",
        "roles": ["Salesperson", "Systems Builder", "Content Creator"],
        "daily_tasks": {
            "Salesperson": [
                "Send 20 cold DMs to targeted business owners",
                "Follow up with all open leads",
                "Conduct 1-2 Free Automation Audit calls",
                "Ask 1 existing client for a referral",
                "Upsell 1 existing client on an additional service",
            ],
            "Systems Builder": [
                "Document 1 SOP or template for repeatable delivery",
                "Build automation from template (target: 1 week per client)",
                "Create onboarding checklist for new clients",
            ],
            "Content Creator": [
                "Post 1 Reel showing real automation running",
                "Post 1 carousel with educational content",
                "Share 1 client testimonial or case study",
                "Engage 20 mins: comments, DMs, group posts",
            ],
        },
        "milestones": [
            "Created SOP for client onboarding",
            "Built law firm automation template",
            "Built contractor automation template",
            "Got video testimonial from client",
            "Published first case study with real numbers",
            "Raised prices to full rate for new clients",
            "Hit $10,000/mo MRR",
            "Launched Free Automation Audit as lead magnet",
            "Built email nurture sequence",
            "Signed client #6",
        ],
    },
    {
        "name": "Phase 3: Scale with Systems",
        "revenue_target": 30000,
        "client_target": 15,
        "months": "5-8",
        "roles": ["CEO/Strategist", "Ad Manager", "Team Leader"],
        "daily_tasks": {
            "CEO/Strategist": [
                "Review yesterday's ad performance and leads",
                "Take 1-2 sales calls or review closer's recordings",
                "Plan 1 partnership or referral outreach",
                "Review client retention — check in with 1 client",
                "Work ON the business (systems, hiring, strategy) for 1 hour",
            ],
            "Ad Manager": [
                "Check Meta Ads dashboard — pause losers, scale winners",
                "Test 1 new ad creative or audience",
                "Review cost per booked call (target: under $100)",
            ],
            "Team Leader": [
                "Check VA's completed tasks and assign new ones",
                "Review 1 automation build for quality",
                "Document any new process that's being done manually",
            ],
        },
        "milestones": [
            "Hired first VA",
            "Launched Meta Ads",
            "Cost per booked call under $100",
            "Created niche-specific packages",
            "Upsold 3+ existing clients",
            "Hit $20,000/mo MRR",
            "Hit $30,000/mo MRR",
            "Built email nurture converting 10%+ of cold leads",
            "Signed 15th client",
            "Launched referral program",
        ],
    },
    {
        "name": "Phase 4: Build the Machine",
        "revenue_target": 60000,
        "client_target": 23,
        "months": "9-14",
        "roles": ["CEO", "Growth Lead", "Operations"],
        "daily_tasks": {
            "CEO": [
                "Review daily revenue and pipeline numbers",
                "1 strategic task: partnerships, new channels, or product",
                "Record 1 piece of thought leadership content",
                "Weekly: review P&L and team performance",
            ],
            "Growth Lead": [
                "Review all lead sources — ads, organic, referrals, partners",
                "Optimize best-performing channel",
                "Test 1 new lead generation idea",
                "Review closer's conversion rate and coach if needed",
            ],
            "Operations": [
                "Check client health dashboard — any churn risks?",
                "Review automation builder's output quality",
                "Improve 1 SOP or create 1 new template",
                "Handle escalations only (VA handles routine)",
            ],
        },
        "milestones": [
            "Hired full-time automation builder",
            "Hired commission-based closer",
            "Removed yourself from building",
            "Removed yourself from sales calls",
            "Launched YouTube or second ad channel",
            "Launched referral/partner program",
            "Added high-ticket $10K+ offer",
            "Hit $50,000/mo MRR",
            "Hit $60,000/mo MRR",
            "Team of 5+ running without you daily",
        ],
    },
    {
        "name": "Phase 5: Million-Dollar Run",
        "revenue_target": 83333,
        "client_target": 25,
        "months": "15-20",
        "roles": ["Visionary", "Growth", "Operator"],
        "daily_tasks": {
            "Visionary": [
                "1 hour of strategic thinking — where is the business going?",
                "Build 1 relationship (podcast, partnership, speaking)",
                "Create 1 piece of CEO-level content",
            ],
            "Growth": [
                "Review all channels and double down on top performer",
                "Explore 1 new revenue stream (white-label, SaaS, course)",
                "Review monthly client LTV and churn trends",
            ],
            "Operator": [
                "Weekly team standup and KPI review",
                "Monthly: review financials with accountant",
                "Quarterly: strategic planning session",
            ],
        },
        "milestones": [
            "Hit $83,333/mo ($1M annual run rate)",
            "25+ active clients",
            "3+ lead sources each producing 5+ leads/mo",
            "White-label or productized service launched",
            "Profit margin above 60%",
            "Full team operating independently",
            "Hit $1,000,000 cumulative revenue",
        ],
    },
]


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "current_phase": 0,
        "current_mrr": 0,
        "current_clients": 0,
        "completed_milestones": [],
        "daily_log": [],
    }


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_days_in():
    data = load_data()
    start = datetime.strptime(data["start_date"], "%Y-%m-%d")
    return (datetime.now() - start).days


def print_header():
    print("\n" + "=" * 60)
    print("  EMPOWERAUTOMATE — DAILY ACTION AGENT")
    print("  " + datetime.now().strftime("%A, %B %d, %Y"))
    print("=" * 60)


def print_status(data):
    phase = PHASES[data["current_phase"]]
    days = get_days_in()
    print(f"\n  📍 {phase['name']}")
    print(f"  📅 Day {days} of your journey")
    print(f"  💰 Current MRR: ${data['current_mrr']:,}/mo")
    print(f"  🎯 Target MRR: ${phase['revenue_target']:,}/mo")
    print(f"  👥 Clients: {data['current_clients']}/{phase['client_target']}")
    print(f"  🎭 Your roles right now: {', '.join(phase['roles'])}")

    completed = len([m for m in phase["milestones"] if m in data["completed_milestones"]])
    total = len(phase["milestones"])
    bar = "█" * completed + "░" * (total - completed)
    print(f"  📊 Phase progress: [{bar}] {completed}/{total}")


def get_top_3(data):
    phase = PHASES[data["current_phase"]]
    uncompleted = [m for m in phase["milestones"] if m not in data["completed_milestones"]]

    priorities = []
    if data["current_clients"] == 0:
        priorities = [
            "OUTREACH: Send 10 DMs to business owners you know — use the script in SCALING-ROADMAP.md",
            "PROOF: Record a Loom demo of Mike's automation system (3 min max)",
            "PRESENCE: Rebrand your Instagram bio and post your first Reel",
        ]
    elif data["current_phase"] == 0:
        if data["current_clients"] < 3:
            priorities = [
                f"CLOSE: You need {3 - data['current_clients']} more client(s) — send 10 outreach DMs today",
                "DELIVER: Build/improve automation for your current client(s)",
                "CONTENT: Post 1 Reel or carousel showing your work",
            ]
        else:
            priorities = [
                "COLLECT: Get a video testimonial from your best client",
                "SYSTEMATIZE: Document your build process into a reusable template",
                "ADVANCE: You're ready for Phase 2 — update your phase with option 3",
            ]
    elif data["current_phase"] == 1:
        priorities = [
            f"GROW: Send 20 cold DMs to {['contractors', 'lawyers', 'creators'][days_hash() % 3]} today",
            "DELIVER: Complete 1 client build or upsell an existing client",
            "CONTENT: Post 1 Reel + 1 educational carousel",
        ]
    elif data["current_phase"] == 2:
        priorities = [
            "ADS: Review Meta Ads — pause underperformers, scale winners",
            "TEAM: Check VA tasks and assign today's priorities",
            "STRATEGY: Spend 1 hour working ON the business, not IN it",
        ]
    elif data["current_phase"] == 3:
        priorities = [
            "REVIEW: Check daily revenue, pipeline, and team output",
            "GROWTH: Optimize your best lead channel or test a new one",
            "DELEGATE: If you're doing something twice, create an SOP and hand it off",
        ]
    else:
        priorities = [
            "VISION: 1 hour of strategic thinking — new revenue streams",
            "GROW: Build 1 new partnership or relationship today",
            "SCALE: Review financials and double down on what's working",
        ]

    if uncompleted and len(priorities) < 3:
        priorities.append(f"MILESTONE: {uncompleted[0]}")

    return priorities[:3]


def days_hash():
    return int(datetime.now().strftime("%j"))


def print_top_3(data):
    priorities = get_top_3(data)
    print("\n" + "-" * 60)
    print("  🔥 YOUR TOP 3 PRIORITIES TODAY")
    print("-" * 60)
    for i, p in enumerate(priorities, 1):
        print(f"\n  {i}. {p}")
    print()


def print_daily_roles(data):
    phase = PHASES[data["current_phase"]]
    print("-" * 60)
    print("  📋 DAILY ROLE BREAKDOWN")
    print("-" * 60)
    for role, tasks in phase["daily_tasks"].items():
        print(f"\n  [{role}]")
        for t in tasks:
            print(f"    ☐ {t}")
    print()


def print_next_milestones(data):
    phase = PHASES[data["current_phase"]]
    uncompleted = [m for m in phase["milestones"] if m not in data["completed_milestones"]]
    if uncompleted:
        print("-" * 60)
        print("  🏁 NEXT MILESTONES TO HIT")
        print("-" * 60)
        for m in uncompleted[:5]:
            print(f"    ☐ {m}")
        print()


def interactive_menu():
    data = load_data()

    print_header()
    print_status(data)
    print_top_3(data)
    print_daily_roles(data)
    print_next_milestones(data)

    print("=" * 60)
    print("  ACTIONS")
    print("  1. Complete a milestone")
    print("  2. Update MRR / client count")
    print("  3. Advance to next phase")
    print("  4. Log today's wins")
    print("  5. View full progress report")
    print("  6. Exit")
    print("=" * 60)

    choice = input("\n  Enter choice (1-6): ").strip()

    if choice == "1":
        phase = PHASES[data["current_phase"]]
        uncompleted = [m for m in phase["milestones"] if m not in data["completed_milestones"]]
        if not uncompleted:
            print("\n  ✅ All milestones complete! Consider advancing to next phase.")
            return
        print("\n  Select milestone to mark complete:")
        for i, m in enumerate(uncompleted, 1):
            print(f"    {i}. {m}")
        sel = input("\n  Enter number: ").strip()
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(uncompleted):
                data["completed_milestones"].append(uncompleted[idx])
                save_data(data)
                print(f"\n  ✅ Completed: {uncompleted[idx]}")
        except ValueError:
            print("  Invalid selection.")

    elif choice == "2":
        try:
            mrr = input("  Enter current MRR ($): ").strip().replace(",", "").replace("$", "")
            clients = input("  Enter current client count: ").strip()
            data["current_mrr"] = int(float(mrr))
            data["current_clients"] = int(clients)
            save_data(data)
            print(f"\n  ✅ Updated: ${data['current_mrr']:,}/mo with {data['current_clients']} clients")
        except ValueError:
            print("  Invalid input.")

    elif choice == "3":
        if data["current_phase"] < len(PHASES) - 1:
            data["current_phase"] += 1
            save_data(data)
            print(f"\n  🚀 Advanced to {PHASES[data['current_phase']]['name']}!")
        else:
            print("\n  👑 You're at the final phase! Keep scaling.")

    elif choice == "4":
        win = input("  What did you accomplish today? ").strip()
        if win:
            data["daily_log"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "win": win,
            })
            save_data(data)
            print("\n  ✅ Logged!")

    elif choice == "5":
        print(f"\n  📊 FULL PROGRESS REPORT")
        print(f"  Days active: {get_days_in()}")
        print(f"  Current phase: {PHASES[data['current_phase']]['name']}")
        print(f"  MRR: ${data['current_mrr']:,}")
        print(f"  Clients: {data['current_clients']}")
        print(f"  Milestones completed: {len(data['completed_milestones'])}")
        if data["daily_log"]:
            print(f"\n  Recent wins:")
            for entry in data["daily_log"][-5:]:
                print(f"    [{entry['date']}] {entry['win']}")

    elif choice == "6":
        print("\n  💪 Go execute. See you tomorrow.\n")
        return

    print()
    input("  Press Enter to continue...")
    interactive_menu()


if __name__ == "__main__":
    interactive_menu()
