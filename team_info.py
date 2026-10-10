"""
Infos zu den Mitspielern in der Champion-Auswahl.

Zeigt pro Mitspieler Rang, Winrate und KDA der letzten Spiele, meistgespielte
Champions und einen op.gg-Link. Alle Daten kommen aus der lokalen Client-API.

In Ranked Solo/Duo blendet Riot die Namen der Mitspieler bis zum Spielstart aus.
Diese Mitspieler werden als "verborgen" angezeigt – das Tool umgeht das nicht.
"""

from __future__ import annotations

import time
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field

POSITIONS = {
    "top": "Top", "jungle": "Jungle", "middle": "Mid",
    "bottom": "ADC", "utility": "Support",
}


@dataclass
class PlayerInfo:
    position: str
    champion: str
    is_me: bool = False
    hidden: bool = False
    riot_id: str = ""
    level: int | None = None
    rank: str = "Unranked"
    games: int = 0
    wins: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    top_champs: list[tuple[str, int]] = field(default_factory=list)
    champ_games: int = 0
    champ_wins: int = 0
    opgg: str = ""

    @property
    def winrate(self) -> str:
        return f"{self.wins / self.games:.0%}" if self.games else "-"

    @property
    def kda(self) -> str:
        if not self.games:
            return "-"
        return f"{(self.kills + self.assists) / max(1, self.deaths):.2f}"


class TeamInspector:
    def __init__(self, client, history_size: int = 20):
        self.client = client
        self.history_size = history_size
        self._champions: dict[int, str] | None = None
        self._region: str | None = None

    # -- Hilfsdaten ---------------------------------------------------------

    def champion_name(self, champ_id: int) -> str:
        if self._champions is None:
            data = self.client.request(
                "GET", "/lol-game-data/assets/v1/champion-summary.json") or []
            self._champions = {c["id"]: c["name"] for c in data if c.get("id", -1) > 0}
        return self._champions.get(champ_id, "-") if champ_id else "-"

    def region(self) -> str:
        if self._region is None:
            data = self.client.request("GET", "/riotclient/region-locale") or {}
            self._region = (data.get("region") or "euw").lower()
        return self._region

    # -- Daten eines Spielers -------------------------------------------------

    def _rank(self, puuid: str) -> str:
        stats = self.client.request("GET", f"/lol-ranked/v1/ranked-stats/{puuid}") or {}
        solo = (stats.get("queueMap") or {}).get("RANKED_SOLO_5x5") or {}
        tier = solo.get("tier")
        if not tier or tier in ("NONE", ""):
            return "Unranked"
        division = solo.get("division")
        division = "" if division in (None, "NA") else f" {division}"
        return f"{tier.title()}{division} {solo.get('leaguePoints', 0)} LP"

    def _history(self, info: PlayerInfo, puuid: str, champ_id: int) -> None:
        path = (f"/lol-match-history/v1/products/lol/{puuid}/matches"
                f"?begIndex=0&endIndex={self.history_size - 1}")
        data = self.client.request("GET", path) or {}
        champs: Counter[int] = Counter()
        for game in (data.get("games") or {}).get("games") or []:
            participant = self._find_participant(game, puuid)
            if participant is None:
                continue
            stats = participant.get("stats") or {}
            win = bool(stats.get("win"))
            info.games += 1
            info.wins += win
            info.kills += stats.get("kills", 0)
            info.deaths += stats.get("deaths", 0)
            info.assists += stats.get("assists", 0)
            played = participant.get("championId", 0)
            champs[played] += 1
            if champ_id and played == champ_id:
                info.champ_games += 1
                info.champ_wins += win
        info.top_champs = [(self.champion_name(c), n) for c, n in champs.most_common(3)]

    @staticmethod
    def _find_participant(game: dict, puuid: str) -> dict | None:
        participants = game.get("participants") or []
        for ident in game.get("participantIdentities") or []:
            if (ident.get("player") or {}).get("puuid") == puuid:
                pid = ident.get("participantId")
                for p in participants:
                    if p.get("participantId") == pid:
                        return p
        return participants[0] if len(participants) == 1 else None

    def player(self, member: dict, local_cell: int) -> PlayerInfo:
        champ_id = member.get("championId") or member.get("championPickIntent") or 0
        info = PlayerInfo(
            position=POSITIONS.get(member.get("assignedPosition") or "", "-"),
            champion=self.champion_name(champ_id),
            is_me=member.get("cellId") == local_cell,
        )
        puuid = member.get("puuid") or ""
        if not info.is_me and (not puuid or member.get("nameVisibilityType") == "HIDDEN"):
            info.hidden = True
            return info

        summoner = self.client.request("GET", f"/lol-summoner/v2/summoners/puuid/{puuid}") or {}
        name, tag = summoner.get("gameName", ""), summoner.get("tagLine", "")
        info.riot_id = f"{name}#{tag}" if tag else (name or summoner.get("displayName", "?"))
        info.level = summoner.get("summonerLevel")
        if name and tag:
            slug = urllib.parse.quote(f"{name}-{tag}")
            info.opgg = f"https://www.op.gg/summoners/{self.region()}/{slug}"
        info.rank = self._rank(puuid)
        self._history(info, puuid, champ_id)
        return info

    def team(self) -> list[PlayerInfo]:
        session = self.client.champ_select_session() or {}
        local_cell = session.get("localPlayerCellId")
        return [self.player(m, local_cell) for m in session.get("myTeam") or []]


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def format_team(players: list[PlayerInfo], history_size: int) -> str:
    lines = [f"{'Pos':<8}{'Spieler':<26}{'Rang':<22}{'WR':>5}{'KDA':>7}  "
             f"{'Champion (WR)':<22}Meistgespielt (letzte {history_size})"]
    lines.append("-" * len(lines[0]) + "-" * 20)
    for p in players:
        if p.hidden:
            lines.append(f"{p.position:<8}{'(verborgen)':<26}{'':<22}{'':>5}{'':>7}  {p.champion}")
            continue
        name = ("» " if p.is_me else "") + p.riot_id
        champ = p.champion
        if p.champ_games:
            champ += f" ({p.champ_wins}/{p.champ_games})"
        top = ", ".join(f"{c} {n}x" for c, n in p.top_champs) or "-"
        lines.append(f"{p.position:<8}{name[:25]:<26}{p.rank:<22}{p.winrate:>5}"
                     f"{p.kda:>7}  {champ:<22}{top}")
    links = [f"  {p.riot_id}: {p.opgg}" for p in players if p.opgg and not p.is_me]
    if links:
        lines += ["", "op.gg:"] + links
    if any(p.hidden for p in players):
        lines += ["", "Hinweis: Riot blendet in Ranked die Namen bis Spielstart aus."]
    return "\n".join(lines)


def cmd_team(client, history_size: int = 20, wait: bool = True) -> None:
    """Zeigt die Mitspieler an; wartet bei Bedarf, bis Champ Select beginnt."""
    if client.gameflow_phase() != "ChampSelect":
        if not wait:
            print("Du bist gerade nicht in der Champion-Auswahl.")
            return
        print("Warte auf Champ Select ... (Strg+C = Abbruch)")
        while client.gameflow_phase() != "ChampSelect":
            time.sleep(1)
        time.sleep(1)  # Session-Daten kurz vollständig laden lassen
    print("Lade Spielerdaten ...\n")
    inspector = TeamInspector(client, history_size)
    print(format_team(inspector.team(), history_size))
