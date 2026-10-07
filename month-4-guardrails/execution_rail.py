"""
Execution rail: path validation for write_log.

This is the piece Month 3 flagged as "excessive agency, noted but not yet
tested, likely folded into Month 4" — this closes that loop.

Deliberately NOT an LLM call. NeMo Guardrails 0.23 does have a native
tool-rail mechanism (IORails, rails.tool_input / rails.tool_output in
config.yml), but as of this version its built-in tool-result/tool-call
flows ("tool result validation" / "tool call validation") only check
structural things — that a tool result links back to a real prior call by
id, that content is well-formed — not the semantic property we actually
care about here, which is "does this path stay inside logs/". Bolting a
semantic check onto that mechanism would mean writing a custom action and
routing around IORails' supported-flow allowlist anyway (see
guardrails/iorails.py: IORails falls back to LLMRails for anything outside
its narrow SUPPORTED_TOOL_* flow sets).

"Is this path inside this directory" is a question with one correct
deterministic answer. Asking an LLM to answer it — with the latency,
cost, and non-zero error rate that implies — would be worse engineering,
not more thorough security. The rail belongs in code. The place an LLM
genuinely earns its keep this month is screening free-text tool content
for injected instructions (see nemo_screens.py), which has no
deterministic answer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from tools import LOGS_DIR


@dataclass
class PathCheckResult:
    allowed: bool
    resolved_path: str
    reason: str


def validate_log_path(filepath: str, allowed_dir: str = LOGS_DIR) -> PathCheckResult:
    """Return whether filepath resolves to somewhere inside allowed_dir.

    Resolves with os.path.realpath so '..' segments, symlinks, and mixed
    relative/absolute forms are all collapsed to a real, comparable path
    before the containment check — the same class of bug Month 3's own
    harness tripped over (a payload path that LOOKED contained but wasn't,
    once actually resolved against the real working directory).
    """
    allowed_root = os.path.realpath(allowed_dir)
    candidate = os.path.realpath(filepath)

    is_inside = candidate == allowed_root or candidate.startswith(allowed_root + os.sep)

    if is_inside:
        return PathCheckResult(
            allowed=True,
            resolved_path=candidate,
            reason=f"resolves inside {allowed_root}",
        )

    return PathCheckResult(
        allowed=False,
        resolved_path=candidate,
        reason=(
            f"'{filepath}' resolves to '{candidate}', which is outside the "
            f"allowed directory '{allowed_root}'"
        ),
    )
