AI Red Teaming Journey

A hands-on learning path toward advanced competency in AI systems red teaming — agents, benchmarks, guardrails — from July to December 2026.

Each month produces a working, documented project and a technical write-up describing what was built and what was discovered. The goal isn't to collect tools, but to build first, deeply understand how things work internally, and only then try to break them systematically.

Why this repo

Red teaming agentic systems requires thinking in terms of dynamic, probabilistic systems, not traditional pentesting logic. To get there seriously, every month in here follows the same pattern: build → understand deeply → attempt an attack → honestly document the results, including the failures.

Repo structure

ai-red-teaming-journey/
├── .gitignore
├── README.md                          (this file)
├── month-01-langgraph-fundamentals/    July — multi-step agent, tool calling, basic prompt injection
├── month-02-tool-selection/            August — how an LLM chooses between ambiguous tools
├── month-03-owasp-vulnerabilities/     September — OWASP Top 10 for LLMs, direct/indirect injection
├── month-04-guardrails/                October — NeMo Guardrails, systematic bypass attempts
├── month-05-benchmarking/              November — Promptfoo, Giskard, Pytest, testing at scale
└── month-06-offensive-agency/          December — Adversarial Agent, multi-agent dynamics

Each monthly folder contains its own README.md with specific details, the code, and a technical write-up (blog-post.md).

Roadmap

MonthPeriodFocusStatus1JulyLangGraph fundamentals, tool calling, first prompt injection test✅ Completed2AugustAmbiguous tool selection, misleading docstrings🔜 In progress3SeptemberOWASP Top 10 for LLMs, systematic direct and indirect injection⏳ To do4OctoberNVIDIA NeMo Guardrails: building rails and breaking out of them⏳ To do5NovemberAutomated benchmarking: Promptfoo, Giskard, Pytest⏳ To do6DecemberAdversarial Agent: multi-agent manipulation, data exfiltration⏳ To do

General setup

Each monthly project is self-contained and has its own requirements.txt. You'll need an Anthropic API key (console.anthropic.com) to run the agents.

bashgit clone https://github.com/<your-username>/ai-red-teaming-journey.git
cd ai-red-teaming-journey/month-01-langgraph-fundamentals   # or whichever month you're interested in

pip install -r requirements.txt

# Set up your API key:
cp .env.example .env
# open .env and add your key, e.g.:
# ANTHROPIC_API_KEY=sk-ant-...

python agent.py

Security note: .env is never committed (see the root .gitignore). If you clone the repo you'll only find .env.example, a template with no real keys — this is intentional; everyone uses their own personal key.

Ethical note

Some projects from October onward involve real offensive capabilities (guardrail bypass attempts, agents with access to potentially dangerous tools). All tests are conducted against agents I built myself, in local or isolated sandbox environments — never against third-party systems without explicit authorization. The same principle applies to anyone reproducing these experiments.

Following the full journey

Each month has a longer technical write-up, linked from that month's README. If you want to follow the journey step by step, that's the place to read.


Repo actively maintained from July to December 2026. Feedback, issues, and discussion are welcome.
