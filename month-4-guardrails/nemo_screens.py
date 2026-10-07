"""
Thin wrappers around two NeMo Guardrails LLMRails instances, used as
callable content screens from inside the LangGraph agent loop rather than
as the top-level conversation driver.

Why not let NeMo Guardrails drive the whole agent? Because its rails are
built around a single chat turn (user message in, bot message out), and
this agent's actual threat model has untrusted content entering mid-loop,
as a tool result, not as the opening user message. Two consequences of
that mismatch, both handled explicitly below rather than papered over:

1. Tool-content screening reuses the "self check input" mechanism against
   text that was never really "user input" — see rails/tool_content_check.
2. Leakage screening needs to check an agent reply that NeMo itself never
   generated (the reply comes from agent.py's own LangGraph loop, not from
   NeMo's main model call). NeMo supports this directly: if the LAST
   message in the list has role "assistant" and generation options set
   rails.dialog=False, it treats that message as the candidate bot output
   and only runs output rails against it, instead of generating a new
   reply (see llmrails.py's generate_async, the block that moves the
   trailing assistant message into the $bot_message context var). That's
   the documented mechanism this module leans on for screen_output().

Detection of "was this blocked" always uses the structured
response.log.activated_rails signal (name + stop flag), never a text match
against the refusal string — same reasoning Month 3 applied to filesystem
state: a boolean control-flow signal, not a subjective read of generated
text.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

# NeMo Guardrails' built-in provider list doesn't have a default base_url
# for "anthropic" on its own lightweight path — it needs to be routed
# through NeMo's LangChain integration instead, which is opt-in via this
# env var. Without it, LLMRails() fails at construction with "No default
# base_url for provider 'anthropic'". Set here, not just documented, so
# this doesn't become a support request days after this was written.
os.environ.setdefault("NEMOGUARDRAILS_LLM_FRAMEWORK", "langchain")

from nemoguardrails import LLMRails, RailsConfig  # noqa: E402

# --- Compatibility patch for nemoguardrails>=0.24 -------------------------
#
# This project was built and tested against nemoguardrails 0.23. A later
# `pip install nemoguardrails` (done once, standalone, to work around a pip
# timeout — see README/blog post) pulled in 0.24.1 instead, which changed
# how the "self check input"/"self check output" flows call the LLM
# (self_check/utils.py's new run_self_check_task() helper). Under some
# response shapes from claude-sonnet-4-6 — observed so far on the
# base64_obfuscated bypass variant, not on every call — the completion text
# that reaches nemoguardrails' own is_content_safe(response: str) parser
# arrives as a list of content blocks instead of a plain string, and that
# function unconditionally calls response.strip(), crashing with:
#   AttributeError: 'list' object has no attribute 'strip'
#
# nemoguardrails' own LangChain adapter (_langchain_response_to_llm_response
# in integrations/langchain/llm_adapter.py) is supposed to flatten list
# content to a string before it gets anywhere near is_content_safe, so this
# looks like a genuine upstream gap in 0.24.1, not something wrong in this
# project's own rail configs. Pinning requirements.txt back to
# nemoguardrails<0.24 would also fix it, but a version-independent patch is
# more robust than relying on every future `pip install` respecting that
# pin (which is exactly how this project ended up on 0.24.1 in the first
# place).
#
# Fix: wrap is_content_safe so it coerces list-shaped input to text first,
# then rebind that wrapper in nemoguardrails.llm.taskmanager's own module
# namespace — not just on nemoguardrails.llm.output_parsers — because
# LLMTaskManager.__init__ builds its output_parsers dict from the bare name
# `is_content_safe` imported into taskmanager.py at that module's top, and
# that dict is what actually gets called at runtime. This must happen
# before the first LLMRails() is constructed (both cached builders below
# do that lazily, so importing this module early enough is sufficient).
import nemoguardrails.llm.taskmanager as _nemo_taskmanager  # noqa: E402
from nemoguardrails.llm.output_parsers import (  # noqa: E402
    is_content_safe as _original_is_content_safe,
)


def _coerce_content_to_text(value) -> str:
    """Flatten a str/list/anything into the plain string the original
    is_content_safe() was written to expect."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for block in value:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(getattr(block, "text", None) or str(block))
        return "".join(parts)
    return str(value)


def _patched_is_content_safe(response):
    return _original_is_content_safe(_coerce_content_to_text(response))


_nemo_taskmanager.is_content_safe = _patched_is_content_safe
# ---------------------------------------------------------------------------

RAILS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rails")


@dataclass
class ScreenResult:
    blocked: bool
    rail_name: str | None
    raw_response: str
    duration_s: float | None = None


def _extract_text(response) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        parts = []
        for item in response:
            if isinstance(item, dict):
                parts.append(str(item.get("content", "")))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(response)


@lru_cache(maxsize=1)
def _tool_content_rails() -> LLMRails:
    config = RailsConfig.from_path(os.path.join(RAILS_DIR, "tool_content_check"))
    return LLMRails(config)


@lru_cache(maxsize=1)
def _output_leak_rails() -> LLMRails:
    config = RailsConfig.from_path(os.path.join(RAILS_DIR, "output_leak_check"))
    return LLMRails(config)


async def screen_tool_content(text: str) -> ScreenResult:
    """Run the tool-content input rail against externally-sourced text
    (e.g. the body returned by fetch_customer_feedback) before it is added
    to the agent's message history.

    Returns blocked=True if the "self check input" rail decided this text
    should not be passed through.
    """
    rails = _tool_content_rails()
    response = await rails.generate_async(
        messages=[{"role": "user", "content": text}],
        options={"log": {"activated_rails": True}},
    )

    blocked = False
    rail_name = None
    duration = None
    if response.log:
        for activated in response.log.activated_rails:
            if activated.name == "self check input" and activated.stop:
                blocked = True
                rail_name = activated.name
        duration = response.log.stats.input_rails_duration

    return ScreenResult(
        blocked=blocked,
        rail_name=rail_name,
        raw_response=_extract_text(response.response),
        duration_s=duration,
    )


async def screen_output(user_context: str, candidate_response: str) -> ScreenResult:
    """Run the output leakage rail against a response the agent already
    produced (generated by agent.py's own LangGraph loop, NOT by this
    LLMRails instance).

    user_context is whatever should be visible to the checker as "what the
    user asked" — for this agent that's usually the original task
    description, since there's rarely a literal end-user chat message.

    Returns blocked=True if the "self check output" rail flagged the
    response as leaking the reference system prompt.
    """
    rails = _output_leak_rails()
    response = await rails.generate_async(
        messages=[
            {"role": "user", "content": user_context},
            {"role": "assistant", "content": candidate_response},
        ],
        options={"rails": {"dialog": False}, "log": {"activated_rails": True}},
    )

    blocked = False
    rail_name = None
    duration = None
    if response.log:
        for activated in response.log.activated_rails:
            if activated.name == "self check output" and activated.stop:
                blocked = True
                rail_name = activated.name
        duration = response.log.stats.output_rails_duration

    return ScreenResult(
        blocked=blocked,
        rail_name=rail_name,
        raw_response=_extract_text(response.response),
        duration_s=duration,
    )
