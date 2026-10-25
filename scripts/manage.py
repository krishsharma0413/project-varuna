#!/usr/bin/env python3
"""Menu-based container manager for varuna. Works on Linux (the droplet), macOS and Windows.

    ./manage.sh                     Linux / macOS
    manage.cmd                      Windows (or double-click)
    python3 scripts/manage.py       anywhere

Pick one or more containers (or ALL), then restart, rebuild or stop them.
Standard library only (Python 3.8+); it shells out to Docker Compose from the repo root.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPOSE: list[str] = []  # ["docker", "compose"] or the older standalone ["docker-compose"]
PREFERRED_ORDER = ["web", "api", "worker", "logger", "searxng", "redis-queue", "redis-cache", "mongo"]
OPTIONAL_PROFILE = {"mongo": "local-mongo"}  # services that only exist under a compose profile
DESCRIPTIONS = {
    "web": "website + /api proxy (Caddy)",
    "api": "FastAPI",
    "worker": "pipeline worker",
    "logger": "log service (SQLite)",
    "searxng": "free search engine (SearXNG)",
    "redis-queue": "queue, locks, rate limits",
    "redis-cache": "read cache",
    "mongo": "local MongoDB (testing only)",
}


def compose(*args: str, profiles: set[str] | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    command = list(COMPOSE)
    for profile in sorted(profiles or ()):
        command += ["--profile", profile]
    command += list(args)
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=capture, check=False)


def _ok(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None


def find_compose() -> str | None:
    """Pick the Compose command. Returns an error message if Docker can't be used."""
    if not shutil.which("docker"):
        return "Docker isn't installed or isn't on PATH."
    info = _ok(["docker", "info"])
    if info is None or info.returncode != 0:
        detail = (info.stderr if info else "").strip().splitlines()
        reason = detail[-1] if detail else "unknown error"
        if "permission denied" in reason.lower():
            return (
                f"Docker refused access: {reason}\n"
                "On Linux, add your user to the docker group (sudo usermod -aG docker $USER, then log out and in),\n"
                "or run this script with sudo."
            )
        return f"Docker isn't running ({reason}). Start Docker (Docker Desktop, or `sudo systemctl start docker`)."
    plugin = _ok(["docker", "compose", "version"])
    if plugin is not None and plugin.returncode == 0:
        COMPOSE[:] = ["docker", "compose"]
        return None
    standalone = _ok(["docker-compose", "version"])
    if standalone is not None and standalone.returncode == 0:
        COMPOSE[:] = ["docker-compose"]
        return None
    return "Docker Compose isn't installed (install the docker-compose-plugin package)."


def all_profiles() -> set[str]:
    return set(OPTIONAL_PROFILE.values())


def list_services() -> list[str]:
    result = compose("config", "--services", profiles=all_profiles(), capture=True)
    names = [n.strip() for n in result.stdout.splitlines() if n.strip()]
    return sorted(names, key=lambda n: PREFERRED_ORDER.index(n) if n in PREFERRED_ORDER else len(PREFERRED_ORDER))


def container_states() -> dict[str, dict[str, str]]:
    """Service name -> {state, status} for existing containers."""
    result = compose("ps", "--all", "--format", "json", profiles=all_profiles(), capture=True)
    text = result.stdout.strip()
    if not text:
        return {}
    try:  # newer compose prints one JSON object per line, older ones a JSON array
        rows = json.loads(text) if text.startswith("[") else [json.loads(line) for line in text.splitlines() if line]
    except json.JSONDecodeError:
        return {}
    return {r.get("Service", ""): {"state": r.get("State", ""), "status": r.get("Status", "")} for r in rows}


def profiles_for(selected: list[str], states: dict[str, dict[str, str]]) -> set[str]:
    """Enable an optional profile only if one of its services is selected or already running."""
    profiles = set()
    for service, profile in OPTIONAL_PROFILE.items():
        if service in selected or states.get(service, {}).get("state") == "running":
            profiles.add(profile)
    return profiles


def show_menu(services: list[str], states: dict[str, dict[str, str]]) -> None:
    print("\n" + "=" * 82)
    print(" varuna - container manager")
    print("=" * 82)
    print(f" {'#':>2}  {'container':<13} {'state':<11} {'status':<28} what it is")
    print(" " + "-" * 80)
    for index, name in enumerate(services, 1):
        info = states.get(name, {"state": "not created", "status": ""})
        print(f" {index:>2}  {name:<13} {info['state']:<11} {info['status'][:28]:<28} {DESCRIPTIONS.get(name, '')}")
    print(" " + "-" * 80)
    print("  A  ALL containers")
    print("  R  refresh status")
    print("  Q  quit")


def parse_selection(raw: str, services: list[str], states: dict[str, dict[str, str]]) -> list[str] | None:
    raw = raw.strip().lower()
    if raw == "a":
        # ALL = every service, minus optional ones that aren't running (e.g. the local MongoDB).
        return [s for s in services if s not in OPTIONAL_PROFILE or states.get(s, {}).get("state") == "running"]
    chosen: list[str] = []
    for part in raw.replace(" ", ",").split(","):
        if not part:
            continue
        if part.isdigit() and 1 <= int(part) <= len(services):
            name = services[int(part) - 1]
        elif part in services:
            name = part
        else:
            print(f"  '{part}' isn't a container number or name.")
            return None
        if name not in chosen:
            chosen.append(name)
    return chosen or None


def choose_action(selected: list[str]) -> str | None:
    print(f"\n Selected: {', '.join(selected)}")
    print("  1  Restart                 fast; applies mongo/redis settings changed in config.yaml")
    print("  2  Rebuild and restart     applies code changes (Python or frontend)")
    print("  3  Stop")
    print("  B  back")
    while True:
        choice = input(" Action: ").strip().lower()
        if choice in {"1", "2", "3"}:
            return choice
        if choice in {"b", ""}:
            return None
        print("  Choose 1, 2, 3 or B.")


def run_action(action: str, selected: list[str], states: dict[str, dict[str, str]]) -> None:
    profiles = profiles_for(selected, states)
    print()
    ok = True
    if action == "1":
        # `restart` only works on running containers; anything stopped or never created is started instead.
        running = [s for s in selected if states.get(s, {}).get("state") == "running"]
        stopped = [s for s in selected if s not in running]
        if running:
            ok = compose("restart", *running, profiles=profiles).returncode == 0
        if ok and stopped:
            ok = compose("up", "-d", *stopped, profiles=profiles).returncode == 0
    elif action == "2":
        ok = compose("up", "-d", "--build", *selected, profiles=profiles).returncode == 0
    else:
        ok = compose("stop", *selected, profiles=profiles).returncode == 0
    print("\n Done." if ok else "\n Something went wrong, see the output above.")


def main() -> int:
    problem = find_compose()
    if problem:
        print(problem)
        return 1
    print("Tip: config.yaml edits apply without a restart, except mongo.uri and redis.* (restart api, worker, logger).")
    while True:
        services = list_services()
        states = container_states()
        show_menu(services, states)
        raw = input("\n Containers (e.g. 2 or 2,3 or A): ").strip()
        if raw.lower() in {"q", "quit", "exit"}:
            return 0
        if raw.lower() in {"r", ""}:
            continue
        selected = parse_selection(raw, services, states)
        if not selected:
            continue
        action = choose_action(selected)
        if action:
            run_action(action, selected, states)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
