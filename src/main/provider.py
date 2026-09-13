#!/usr/bin/env python
"""
provider.py — the provider registry and active agent environment detection.

A LIBRARY, not a command: nothing here reports. `corpus-yoga provider` and
`corpus-yoga prerequisites` are the reporting surfaces.

Two facts, mirroring machine.py:
  providers()           the declared providers (rsc/provider/providers.csv) — the registry.
  active_signature()    the drafting signature minted from this environment, or the machine fallback.

STDLIB-ONLY, like machine.py and cli.py: importable on a fresh clone before the venv exists.
"""
import csv
import os
import re
import sys
from pathlib import Path

SELF = 'src/main/provider.py'
_file = Path(__file__).resolve()
_root = [p for p in _file.parents if p / SELF == _file]
assert _root, f'{_file} is not at its declared address {SELF}'
REPO = _root[0]
REGISTRY = REPO / 'rsc' / 'provider' / 'providers.csv'

sys.path.insert(0, str(REPO / 'src' / 'main'))
try:
    from machine import bound_machine
except ImportError:
    bound_machine = lambda: 'reading-room'  # fallback if imported outside repo context


def providers() -> list[dict[str, str]]:
    """The declared providers, in registry order."""
    if not REGISTRY.exists():
        return []
    with REGISTRY.open() as f:
        return [r for r in csv.DictReader(f) if r.get('provider', '').strip()]


def provider_names() -> list[str]:
    """The declared provider names."""
    return [p['provider'] for p in providers()]


def get_provider(name: str) -> dict[str, str]:
    """Return the provider row for name, or raise KeyError."""
    for p in providers():
        if p['provider'] == name:
            return p
    raise KeyError(f"unknown provider '{name}' — declared in {REGISTRY.relative_to(REPO)}: {', '.join(provider_names())}")


def live_harness_path(p: dict[str, str]) -> Path:
    """Return the path to the live harness directory in user home."""
    return Path(p['live_harness']).expanduser()


def mount_path(p: dict[str, str]) -> Path:
    """Return the path to the mount under ext/mnt/."""
    return REPO / 'ext' / 'mnt' / p['mount_name']


def store_path(p: dict[str, str], machine: str | None = None) -> Path:
    """Return the path to this machine's store directory."""
    m = machine or bound_machine()
    return REPO / 'data' / 'input' / p['provider'] / p['modality'] / 'machine-transport' / m


def bot_author_patterns() -> list[str]:
    """All declared bot co-author regex patterns to strip from commit messages."""
    return [p['bot_author_pattern'] for p in providers() if p.get('bot_author_pattern')]


def detect_environment(env: dict[str, str] | None = None) -> tuple[str | None, str | None]:
    """Detect (provider_name, session_id_8) from environment variables.
    
    Checks declared providers' session_env_var, plus AI_AGENT / AI_AGENT_SESSION_ID.
    Returns (None, None) if no agent session is active.
    """
    e = os.environ if env is None else env
    declared = providers()

    # Direct session env var checks
    for p in declared:
        var = p.get('session_env_var', '')
        val = e.get(var, '').strip() if var else ''
        if val:
            p_name = p['provider']
            # Allow AI_AGENT to refine provider name if congruent
            agent = e.get('AI_AGENT', '').split('-')[0].strip()
            if agent and agent in (p_name, 'antigravity'):
                p_name = p['provider']
            return p_name, val[:8]

    # Generic AI_AGENT / AI_AGENT_SESSION_ID checks
    ai_agent = e.get('AI_AGENT', '').split('-')[0].strip()
    generic_session = e.get('AI_AGENT_SESSION_ID', '').strip()
    if ai_agent and generic_session:
        for p in declared:
            if p['provider'] == ai_agent:
                return p['provider'], generic_session[:8]
        return ai_agent, generic_session[:8]

    return None, None


def active_signature(machine: str | None = None, env: dict[str, str] | None = None) -> str:
    """The drafting signature minted for this commit.
    
    If an agent session is detected in the environment:
        Signature: <machine>/<provider>/<session8>
    If no agent session is active:
        Signature: <machine>
    """
    m = machine or bound_machine()
    prov, sess = detect_environment(env)
    if prov and sess:
        return f"Signature: {m}/{prov}/{sess}"
    return f"Signature: {m}"
