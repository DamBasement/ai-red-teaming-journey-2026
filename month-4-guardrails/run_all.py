"""
Runs the full Month 4 suite end to end and writes results/summary.md with
real tables generated from actual run output — nothing in that file is
hand-typed, so there's no transcription step where a number could drift
from what the harness actually measured.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python run_all.py

Takes a few minutes: each variant makes several real API calls (the agent
loop itself, plus one or two rail checks per guarded run).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))

import test_bypass_variants  # noqa: E402
import test_control_rerun  # noqa: E402
import test_false_positives  # noqa: E402
import test_leakage_validation  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def build_summary_md(control, leakage, bypass, false_positives) -> str:
    parts = []
    parts.append(f"# Month 4 — results summary\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n")

    parts.append("## Control rerun (raw vs guarded)\n")
    rows = []
    for r in control:
        rows.append([
            r["variant"],
            "guarded" if r["guardrails_enabled"] else "raw",
            "yes" if r["secrets_tampered"] else "no",
            "yes" if r["log_written_correctly"] else "no",
            "yes" if r["tool_content_blocked"] else "no",
        ])
    parts.append(_md_table(
        ["variant", "condition", "secrets tampered", "log written correctly", "tool-content rail fired"],
        rows,
    ))

    parts.append("\n## Leakage detector validation\n")
    a = leakage["part_a_detector_validation"]
    parts.append(_md_table(
        ["check", "blocked", "word overlap"],
        [
            ["synthetic obvious leak", a["obvious_leak_blocked"], a["obvious_leak_word_overlap"]],
            ["synthetic obvious safe reply", a["obvious_safe_blocked"], a["obvious_safe_word_overlap"]],
        ],
    ))
    parts.append(f"\n**Detector validated (catches the leak, passes the safe reply): {a['detector_validated']}**\n")

    parts.append("\n### Live-agent leak attempts\n")
    rows = []
    for r in leakage["part_b_live_attempts"]:
        rows.append([
            r["scenario"],
            "guarded" if r["guardrails_enabled"] else "raw",
            r.get("output_leak_blocked"),
            r.get("tool_content_blocked", "n/a"),
            r.get("word_overlap"),
        ])
    parts.append(_md_table(
        ["scenario", "condition", "output rail blocked", "tool-content rail blocked", "word overlap"],
        rows,
    ))

    parts.append("\n## Bypass-focused adversarial variants (guarded agent only)\n")
    rows = []
    for r in bypass:
        rows.append([
            r["variant"],
            r.get("rail_level_blocked", "n/a"),
            "yes" if r["end_to_end_secrets_tampered"] else "no",
            "yes" if r.get("end_to_end_log_written_correctly") else (
                "yes" if r.get("logs_written") else "no"
            ),
        ])
    parts.append(_md_table(
        ["variant", "rail-level blocked", "secrets tampered end-to-end", "log written correctly"],
        rows,
    ))

    parts.append("\n## False positives (legitimate requests, guarded agent)\n")
    rows = []
    for r in false_positives:
        rows.append([r["variant"], r["rail_blocked_legitimate_content"], r["log_written_correctly"]])
    fp_count = sum(1 for r in false_positives if r["false_positive"])
    parts.append(_md_table(["variant", "rail blocked (should be No)", "log written correctly (should be Yes)"], rows))
    parts.append(f"\n**{fp_count}/{len(false_positives)} legitimate requests incorrectly blocked.**\n")

    return "\n".join(parts)


async def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("\n########## CONTROL RERUN ##########")
    control = await test_control_rerun.main()

    print("\n########## LEAKAGE VALIDATION ##########")
    await test_leakage_validation.main()
    with open(os.path.join(RESULTS_DIR, "leakage_validation.json")) as f:
        leakage = json.load(f)

    print("\n########## BYPASS VARIANTS ##########")
    await test_bypass_variants.main()
    with open(os.path.join(RESULTS_DIR, "bypass_variants.json")) as f:
        bypass = json.load(f)

    print("\n########## FALSE POSITIVES ##########")
    await test_false_positives.main()
    with open(os.path.join(RESULTS_DIR, "false_positives.json")) as f:
        false_positives = json.load(f)

    summary = build_summary_md(control, leakage, bypass, false_positives)
    summary_path = os.path.join(RESULTS_DIR, "summary.md")
    with open(summary_path, "w") as f:
        f.write(summary)

    print(f"\n\nAll done. Full summary written to {summary_path}")
    print("Send this file (or the whole results/ folder) back to finish the write-up.")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set. export it first, e.g.:")
        print('  export ANTHROPIC_API_KEY="sk-ant-..."')
        sys.exit(1)
    asyncio.run(main())
