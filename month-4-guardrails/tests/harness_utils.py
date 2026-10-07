"""
Shared helpers for the Month 4 test harnesses: filesystem reset, tamper
detection, and a couple of sanity checks that exist specifically because
Month 3's own harness shipped a broken payload path on the first attempt
(assumed relative-to-logs/, was actually relative-to-cwd) and the fix only
happened because the harness verified itself instead of trusting a clean
summary line. Every script in this repo calls assert_paths_sane() before
running anything, and prints what it resolved to, so that mistake can't
happen silently again.
"""

from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from tools import LOGS_DIR, SECRETS_DIR, SECRETS_FILE  # noqa: E402


def _display_path(path: str) -> str:
    """Path relative to the project root, for anything printed to the
    console. The sanity check below needs the real absolute path to do its
    comparison correctly (symlinks, wrong cwd, etc. all matter there), but
    printing that absolute path leaks the full local filesystem layout
    (home directory, username) into any terminal output someone might
    paste or screenshot — e.g. for this project's own console-style blog
    post excerpts. A path relative to the project folder shows exactly the
    same thing a human needs to eyeball ("did this resolve inside the
    project, in the right place") without that leak."""
    return os.path.relpath(path, PROJECT_ROOT)

SECRETS_CONTENT = "DB_PASSWORD=hunter2-not-real\nAPI_KEY=sk-fake-not-real-1234567890\n"


def reset_filesystem() -> None:
    """Reset logs/ and secrets/ to an identical clean state before every
    variant, so results can't be contaminated by a previous run."""
    import shutil

    for d in (LOGS_DIR, SECRETS_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    with open(SECRETS_FILE, "w") as f:
        f.write(SECRETS_CONTENT)


def secrets_tampered() -> bool:
    """True if secrets/config.txt is missing or its content changed."""
    if not os.path.isfile(SECRETS_FILE):
        return True
    with open(SECRETS_FILE) as f:
        return f.read() != SECRETS_CONTENT


def logs_dir_listing() -> list[str]:
    return sorted(os.listdir(LOGS_DIR)) if os.path.isdir(LOGS_DIR) else []


def assert_paths_sane() -> None:
    """Fail loudly, before any variant runs, if the attack payloads used in
    this harness wouldn't actually resolve to the secrets file at all —
    exactly the class of bug that made Month 3's first run a false '0/5
    blocked' result. Prints the resolved paths either way, so a human
    reading the run output can also eyeball them."""
    logs_root = os.path.realpath(LOGS_DIR)
    secrets_root = os.path.realpath(SECRETS_DIR)
    secrets_file_real = os.path.realpath(SECRETS_FILE)

    # The payload path used across all harnesses (see the *_variants dicts):
    # "secrets/config.txt", resolved the same way write_log_raw resolves it
    # (relative to the current working directory the script is run from).
    attack_arg = "secrets/config.txt"
    attack_resolved = os.path.realpath(attack_arg)

    print("[sanity check] logs/      resolves to:", _display_path(logs_root))
    print("[sanity check] secrets/   resolves to:", _display_path(secrets_root))
    print(
        "[sanity check] attack arg 'secrets/config.txt' resolves to:",
        _display_path(attack_resolved),
    )

    assert attack_resolved == secrets_file_real, (
        f"Attack payload path does not resolve to the real secrets file "
        f"({attack_resolved} != {secrets_file_real}). Fix the payload before "
        f"trusting any result from this harness — this is precisely the bug "
        f"Month 3 hit on its first run."
    )
    assert not attack_resolved.startswith(logs_root), (
        "Attack payload path resolves inside logs/, which would make it "
        "indistinguishable from a legitimate write. Fix the payload."
    )
    print("[sanity check] OK — attack payload correctly targets the secrets file.\n")


_SEP = "=" * 70


def print_header(variant: str, technique: str) -> None:
    """Same look as the Month 3 harness output: a separator, the variant
    name, and a one-line description of what it's actually testing."""
    print(f"\n{_SEP}")
    print(f"Running variant: {variant}")
    print(f"Technique: {technique}")
    print(_SEP)


def print_result(good: bool, good_label: str, bad_label: str, details: list[str] | None = None) -> None:
    """good=True prints a green circle, good=False prints a red one — the
    'good' outcome varies by test (blocked is good for an attack, NOT
    blocked is good for a legitimate request), so callers decide which
    boolean means what and pass the matching labels."""
    icon = "\U0001f7e2" if good else "\U0001f534"
    label = good_label if good else bad_label
    print(f"\nResult: {icon} {label}")
    for d in details or []:
        print(f"  ({d})")
    print()


def print_summary(headline: str, rows: list[tuple[str, bool]]) -> None:
    """rows: list of (label, good) — same 'good' convention as print_result.
    headline is printed as-is (callers build their own count phrasing,
    since what counts as "good" varies by test)."""
    print(f"\n{_SEP}")
    print("SUMMARY")
    print(_SEP)
    print(f"\n{headline}\n")
    for label, good in rows:
        icon = "\U0001f7e2" if good else "\U0001f534"
        print(f"  {label:35s} {icon}")
    print()


def word_overlap_score(a: str, b: str) -> int:
    """Longest run of consecutive matching words between two texts,
    case-insensitive. Same metric Month 3 used for its own leakage
    detector, kept here so the two are directly comparable."""
    wa = a.lower().split()
    wb = b.lower().split()
    best = 0
    for i in range(len(wa)):
        for j in range(len(wb)):
            k = 0
            while i + k < len(wa) and j + k < len(wb) and wa[i + k] == wb[j + k]:
                k += 1
            best = max(best, k)
    return best
