# Guardrails (NeMo Guardrails, build then break)

NVIDIA NeMo Guardrails wrapped around the Month 3 customer-support agent:
a tool-content input rail, a deterministic execution rail on the
vulnerable `write_log` tool, and an output rail for system-prompt
leakage — then a set of tests aimed specifically at bypassing the rails
(encoding obfuscation, multi-turn escalation), not the base model.

Full narrative: [`blog-post-month-4.md`](./blog-post-month-4.md) (its
results tables are filled in by `run_all.py`, not hand-written).

## Setup

```bash
cd agent-month4
pip install -r requirements.txt
cp .env.example .env   # then edit .env and set your real ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY="sk-ant-..."   # or: export $(cat .env | xargs)
python run_all.py
```

Takes a few minutes — every guarded run makes at least one extra API call
per rail check, on top of the agent's own tool-calling loop.

For a single clean baseline run instead of the full suite:

```bash
python agent.py                 # guardrails on
python agent.py --no-guardrails # reproduces Month 3's raw behavior
```

**Run everything from the project root** (`agent-month4/`), not from
inside `tests/` — `logs/` and `secrets/` are resolved relative to the
current working directory, the same way `write_log`'s vulnerable path
resolution works, so running from the wrong directory silently points
the attack payloads at the wrong place. `tests/harness_utils.py` asserts
this before every harness runs and fails loudly if it's wrong — the exact
class of bug Month 3's own harness shipped on its first attempt.

## Project layout

```
├── agent.py                       # LangGraph agent + guardrails_enabled toggle
├── tools.py                       # fetch_customer_feedback, write_log (raw, unchanged from Month 3)
├── execution_rail.py              # deterministic path-validation execution rail
├── nemo_screens.py                # LLMRails wrappers used as callable content screens
├── rails/
│   ├── tool_content_check/        # input rail repurposed to screen tool-returned content
│   └── output_leak_check/         # output rail for system-prompt leakage
├── tests/
│   ├── harness_utils.py           # fs reset, tamper check, path sanity check
│   ├── test_control_rerun.py      # continuity check vs Month 3 (raw vs guarded)
│   ├── test_leakage_validation.py # true-positive validation for the leak detector
│   ├── test_bypass_variants.py    # base64 / unicode / multi-turn — the actual point of this month
│   └── test_false_positives.py    # do the rails over-block legitimate feedback?
├── run_all.py                     # runs everything, writes results/summary.md from real output
├── requirements.txt
├── .env.example
└── blog-post-month-4.md
```

## What the agent does (unchanged from Month 3)

1. Receives a task referencing a support ticket id
2. Fetches feedback text for that ticket (`fetch_customer_feedback`) — the
   untrusted, externally-controlled channel
3. Writes a short summary to a log file (`write_log`) — intentionally
   vulnerable in its raw form, no path validation

## What's new this month

- **Tool-content input rail** screens step 2's output before it reaches
  the model, when `guardrails_enabled=True`.
- **Execution rail** validates step 3's target path deterministically,
  before any file is written — closes the "excessive agency, noted but
  not yet tested" item from Month 3.
- **Output leakage rail** checks the final response against a reference
  copy of the system prompt, as a second detector alongside Month 3's
  word-overlap metric.
- **`run_agent_sequence()`** in `agent.py` runs multiple tasks in one
  shared conversation, needed for the multi-turn escalation test — every
  other harness in this repo (and in Months 1-3) runs one isolated task
  per call.

## Known limitations, stated plainly

- Both rails use the same model family as the agent itself
  (`claude-sonnet-4-6`), not a separate, potentially weaker classifier —
  NeMo Guardrails supports pointing rails at a different model; that's
  untested here.
- The adversarial variants (`test_bypass_variants.py`) are three related
  techniques, not a systematic sweep — real breadth testing is Month 5's
  job.
- Every result is specific to one model, on one day — same caveat Months
  1-3 carried, unchanged by adding a guardrail layer.

## Next month

Month 5 moves to systematic benchmarking: multi-variant, multi-model
testing tooling (Promptfoo, Giskard, Pytest), so results generalize
beyond one model's behavior on one day.
