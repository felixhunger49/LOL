# LoL Dodge Tool

Kleines Python-Script, um in **League of Legends** die Champion-Auswahl zu verlassen
("dodgen"), ohne den Client neu starten zu müssen. Es nutzt die offizielle lokale
Client-API (LCU) – es greift nicht ins laufende Spiel ein.

## Voraussetzungen

- Python 3.9+ (keine zusätzlichen Pakete nötig)
- Laufender League Client (Windows oder macOS)

## Nutzung

**Am einfachsten (Windows):** Doppelklick auf `start.bat` und im Menü auswählen.
Liegt League nicht unter `C:\Riot Games\League of Legends`, trage den Pfad oben in
der `start.bat` bei `LOL_PATH` ein.

Oder über die Kommandozeile:

```bash
python dodge.py                    # sofort dodgen
python dodge.py --status           # Phase & Restzeit anzeigen
python dodge.py --last-second      # automatisch ~3 s vor Spielstart dodgen
python dodge.py --last-second --margin 3
python dodge.py --watch            # läuft im Hintergrund, Enter = dodge
python dodge.py --path "D:\Games\League of Legends"
python dodge.py --team             # Infos zu den Mitspielern
python dodge.py --team --games 50  # Statistik über die letzten 50 Spiele
```

### Mitspieler-Infos (`--team`)

Wartet bei Bedarf auf die Champion-Auswahl und zeigt dann pro Mitspieler:

- Riot-ID, Position und gewählten Champion
- Solo/Duo-Rang mit LP
- Winrate und KDA der letzten Spiele
- Bilanz auf dem aktuell gewählten Champion
- die 3 meistgespielten Champions
- op.gg-Link

In Ranked Solo/Duo blendet Riot die Namen der Mitspieler bis zum Spielstart aus –
diese erscheinen als „(verborgen)“. Das Tool umgeht diese Sperre bewusst nicht.

Den Installationsordner kannst du auch über die Umgebungsvariable `LOL_PATH` setzen.
Wird keine `lockfile` gefunden, liest das Script Port und Token direkt aus dem
`LeagueClientUx`-Prozess.

### Wie gedodged wird

Riot hat den früheren Dodge-Aufruf (`teambuilder-draft quitV2`) abgeschaltet – er
liefert nur noch `RPC_ERROR`. Das Script dodged deshalb, indem es den League Client
sauber beendet; das zählt genauso als Dodge. Mit `--restart` startet es League
danach automatisch neu (im Menü der `start.bat` immer aktiv).

`--method auto` versucht zuerst den alten Aufruf und fragt bei Fehler nach.

## Wichtig

- Ein Dodge wird ganz normal bestraft (Queue-Sperre, in Ranked LP-Verlust).
- Nutzung auf eigene Verantwortung.

---

Außerdem im Repo: [`stickerei/`](stickerei/README.md) – Bilder in Stickdateien (SVG) umwandeln.
