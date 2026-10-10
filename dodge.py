#!/usr/bin/env python3
"""
LoL Champ-Select Dodge Tool

Verlässt die Champion-Auswahl ("dodge") über die lokale League-Client-API (LCU),
ohne den Client komplett beenden zu müssen.

Nutzung:
    python dodge.py                 # sofort dodgen (falls in Champ Select)
    python dodge.py --last-second   # warten und kurz vor Ende des Timers dodgen
    python dodge.py --watch         # im Hintergrund laufen, Enter = dodge
    python dodge.py --status        # nur aktuellen Status anzeigen
    python dodge.py --team          # Infos zu den Mitspielern anzeigen

Hinweis: Ein Dodge zählt wie ein normaler Queue-Dodge (LP-Verlust / Wartezeit).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import re
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DODGE_ENDPOINT = (
    "/lol-login/v1/session/invoke"
    "?destination=lcdsServiceProxy&method=call"
    '&args=["","teambuilder-draft","quitV2",""]'
)

DEFAULT_INSTALL_PATHS = [
    r"C:\Riot Games\League of Legends",
    r"D:\Riot Games\League of Legends",
    r"C:\Program Files\Riot Games\League of Legends",
    r"C:\Program Files (x86)\Riot Games\League of Legends",
    "/Applications/League of Legends.app/Contents/LoL",
]


@dataclass
class LcuCredentials:
    port: int
    password: str
    protocol: str = "https"


class LcuError(Exception):
    pass


# ---------------------------------------------------------------------------
# Zugangsdaten finden
# ---------------------------------------------------------------------------

def _credentials_from_process() -> LcuCredentials | None:
    """Liest Port und Token aus der Kommandozeile des LeagueClientUx-Prozesses."""
    system = platform.system()
    try:
        if system == "Windows":
            cmd = [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"name='LeagueClientUx.exe'\" "
                "| Select-Object -ExpandProperty CommandLine",
            ]
        else:
            cmd = ["ps", "-A", "-ww", "-o", "args"]
        output = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None

    for line in output.splitlines():
        if "LeagueClientUx" not in line:
            continue
        port = re.search(r"--app-port=(\d+)", line)
        token = re.search(r"--remoting-auth-token=([\w-]+)", line)
        if port and token:
            return LcuCredentials(int(port.group(1)), token.group(1))
    return None


def _credentials_from_lockfile(install_dir: str | None) -> LcuCredentials | None:
    """Liest die 'lockfile' im Installationsordner des Clients."""
    candidates = [install_dir] if install_dir else DEFAULT_INSTALL_PATHS
    for directory in candidates:
        if not directory:
            continue
        lockfile = Path(directory) / "lockfile"
        if lockfile.is_file():
            # Format: name:pid:port:password:protocol
            parts = lockfile.read_text().strip().split(":")
            if len(parts) >= 5:
                return LcuCredentials(int(parts[2]), parts[3], parts[4])
    return None


def find_credentials(install_dir: str | None = None) -> LcuCredentials:
    creds = _credentials_from_lockfile(install_dir) or _credentials_from_process()
    if creds is None:
        raise LcuError(
            "League Client nicht gefunden. Läuft der Client? "
            "Ggf. Installationsordner mit --path angeben."
        )
    return creds


# ---------------------------------------------------------------------------
# LCU-Client
# ---------------------------------------------------------------------------

class LcuClient:
    def __init__(self, creds: LcuCredentials):
        self.base_url = f"{creds.protocol}://127.0.0.1:{creds.port}"
        token = base64.b64encode(f"riot:{creds.password}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        # Der Client nutzt ein selbstsigniertes Riot-Zertifikat auf localhost.
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    def request(self, method: str, path: str, body: object | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.base_url + path, data=data, headers=self.headers, method=method
        )
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=5) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise LcuError(f"HTTP {e.code} bei {method} {path}: {e.read()!r}") from e
        except urllib.error.URLError as e:
            raise LcuError(f"Keine Verbindung zum Client: {e.reason}") from e

    def gameflow_phase(self) -> str:
        return self.request("GET", "/lol-gameflow/v1/gameflow-phase") or "None"

    def champ_select_session(self) -> dict | None:
        return self.request("GET", "/lol-champ-select/v1/session")

    def summoner_name(self) -> str:
        me = self.request("GET", "/lol-summoner/v1/current-summoner") or {}
        return me.get("gameName") or me.get("displayName") or "?"

    def dodge(self) -> None:
        self.request("POST", DODGE_ENDPOINT, body={})


# ---------------------------------------------------------------------------
# Logik
# ---------------------------------------------------------------------------

def remaining_seconds(session: dict) -> float | None:
    timer = session.get("timer") or {}
    total_ms = timer.get("adjustedTimeLeftInPhase")
    if total_ms is None:
        return None
    # internalNowInEpochMs = Zeitpunkt, an dem der Timer-Wert gemessen wurde
    measured = timer.get("internalNowInEpochMs")
    if measured:
        elapsed = time.time() * 1000 - measured
        total_ms = max(0.0, total_ms - elapsed)
    return total_ms / 1000


def is_final_phase(session: dict) -> bool:
    return (session.get("timer") or {}).get("phase") == "FINALIZATION"


def do_dodge(client: LcuClient) -> bool:
    if client.gameflow_phase() != "ChampSelect":
        print("Du bist gerade nicht in der Champion-Auswahl.")
        return False
    client.dodge()
    time.sleep(0.5)
    if client.gameflow_phase() == "ChampSelect":
        print("Dodge-Anfrage gesendet, aber Champ Select ist noch aktiv.")
        return False
    print("Gedodged! ✔")
    return True


def cmd_status(client: LcuClient) -> None:
    phase = client.gameflow_phase()
    print(f"Spieler: {client.summoner_name()}")
    print(f"Phase:   {phase}")
    if phase == "ChampSelect":
        session = client.champ_select_session() or {}
        timer = session.get("timer") or {}
        left = remaining_seconds(session)
        print(f"Champ-Select-Phase: {timer.get('phase')}")
        if left is not None:
            print(f"Restzeit: {left:.1f}s")


def cmd_last_second(client: LcuClient, margin: float) -> None:
    """Wartet bis zur Finalisierungsphase und dodged `margin` Sekunden vor Ende."""
    print(f"Warte auf Champ Select ... (Dodge {margin:.1f}s vor Spielstart, Strg+C = Abbruch)")
    while True:
        if client.gameflow_phase() != "ChampSelect":
            time.sleep(1)
            continue
        session = client.champ_select_session()
        if not session:
            time.sleep(0.5)
            continue
        left = remaining_seconds(session)
        if is_final_phase(session) and left is not None:
            print(f"\rFinalisierung – noch {left:5.1f}s ", end="", flush=True)
            if left <= margin:
                print()
                if do_dodge(client):
                    return
        time.sleep(0.1 if left is not None and left < margin + 2 else 0.5)


def cmd_watch(client: LcuClient) -> None:
    """Läuft dauerhaft; Enter drücken dodged sofort."""
    print("Watch-Modus aktiv. [Enter] = dodge, 'q' + [Enter] = beenden.")
    state = {"phase": None}

    def monitor():
        while True:
            try:
                phase = client.gameflow_phase()
            except LcuError:
                phase = "Offline"
            if phase != state["phase"]:
                state["phase"] = phase
                print(f"[Phase] {phase}")
            time.sleep(1)

    threading.Thread(target=monitor, daemon=True).start()
    for line in sys.stdin:
        if line.strip().lower() in {"q", "quit", "exit"}:
            return
        try:
            do_dodge(client)
        except LcuError as e:
            print(f"Fehler: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="League of Legends Champ-Select Dodge Tool")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--status", action="store_true", help="nur Status anzeigen")
    mode.add_argument("--team", action="store_true",
                      help="Infos zu den Mitspielern in Champ Select anzeigen")
    mode.add_argument("--last-second", action="store_true",
                      help="automatisch kurz vor Spielstart dodgen")
    mode.add_argument("--watch", action="store_true",
                      help="dauerhaft laufen, Enter drücken zum Dodgen")
    parser.add_argument("--margin", type=float, default=1.5,
                        help="Sekunden vor Ende für --last-second (Standard: 1.5)")
    parser.add_argument("--games", type=int, default=20,
                        help="Anzahl letzter Spiele für --team (Standard: 20)")
    parser.add_argument("--path", default=os.environ.get("LOL_PATH"),
                        help="Installationsordner von League of Legends")
    args = parser.parse_args()

    try:
        client = LcuClient(find_credentials(args.path))
        if args.status:
            cmd_status(client)
        elif args.team:
            from team_info import cmd_team
            cmd_team(client, args.games)
        elif args.last_second:
            cmd_last_second(client, args.margin)
        elif args.watch:
            cmd_watch(client)
        else:
            return 0 if do_dodge(client) else 1
    except LcuError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
