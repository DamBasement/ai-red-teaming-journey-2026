AI Red Teaming Journey

A hands-on learning path toward advanced proficiency in red teaming AI systems—agents, benchmarks, and guardrails—running from July to December 2026.

Each month yields a functional, documented project and a technical post describing what was built and what was discovered. The goal is not merely to collect tools, but to build first, gain a deep understanding of internal mechanics, and only then attempt to break the system systematically.

Why this repo?

Red teaming agentic systems requires thinking in terms of dynamic and probabilistic systems, rather than applying traditional pentesting logic. To approach this seriously, the work here follows the same pattern each month: construction → deep understanding → attack attempt → honest documentation of results, including failures.

Repo structure

ai-red-teaming-journey/
├── .gitignore
├── README.md                          (this file)
├── month-01-langgraph-foundations/     July — multi-step agent, tool calling, basic prompt injection
├── month-02-tool-selection/            August — how an LLM chooses between ambiguous tools
├── month-03-owasp-vulnerabilities/     September — OWASP Top 10 for LLMs, direct/indirect injection
├── month-04-guardrails/                October — NeMo Guardrails, systematic bypass
├── month-05-benchmarking/              November — Promptfoo, Giskard, Pytest, testing at scale
└── month-06-offensive-agency/          December — Adversarial Agent, multi-agent dynamics

Each monthly folder contains its own README.md with specific details, the code, and a technical post (blog-post.md). Roadmap

Month/Period | Focus | Status
--- | --- | ---
1 July | LangGraph fundamentals, tool calling, initial prompt injection test | ✅ Completed
2 August | Ambiguous tool selection, misleading docstrings | 🔜 In progress
3 September | OWASP Top 10 for LLMs, systematic direct and indirect injection | ⏳ To do
4 October | NVIDIA NeMo Guardrails: building guardrails and breaking out of them | ⏳ To do
5 November | Automated benchmarking: Promptfoo, Giskard, Pytest | ⏳ To do
6 December | Adversarial Agent: multi-agent manipulation, data exfiltration | ⏳ To do

General Setup

Each monthly project is independent and has its own `requirements.txt`.
You need an Anthropic API key (from console.anthropic.com) to run the
agents.

bashgit clone https://github.com/<your-username>/ai-red-teaming-journey.git
cd ai-red-teaming-journey/mese-01-langgraph-fondamenta   # or the month you're interested in

pip install -r requirements.txt

# Configure your API key:
cp .env.example .env
# Open .env and insert your key, e.g.:
# ANTHROPIC_API_KEY=sk-ant-...

python agent.py

Security note: The `.env` file is never committed (see
`.gitignore` in the root). If you clone the repo, you will only find `.env.example`,
a template without real keys—this is intentional, as everyone uses their
own personal key.

Ethical Note

Some projects from October onwards involve actual offensive capabilities
(attempts to bypass guardrails, agents with access to potentially dangerous
tools). All tests are conducted on agents I built myself, in
local environments or isolated sandboxes—never against third-party systems
without explicit authorization. The same principle applies to anyone
replicating these experiments.

The Full Journey

Each month features a more detailed technical post, linked from the
README in its respective folder. If you want to follow the journey
step-by-step, that is the place to look.

Repo actively maintained from July to December 2026. Feedback, issues, and
discussions are welcome.
