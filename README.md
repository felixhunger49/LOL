# LoL Dodge Tool

Kleines Python-Script, um in **League of Legends** die Champion-Auswahl zu verlassen
("dodgen"), ohne den Client neu starten zu müssen. Es nutzt die offizielle lokale
Client-API (LCU) – es greift nicht ins laufende Spiel ein.

## Voraussetzungen

- Python 3.9+ (keine zusätzlichen Pakete nötig)
- Laufender League Client (Windows oder macOS)

## Nutzung

```bash
python dodge.py                    # sofort dodgen
python dodge.py --status           # Phase & Restzeit anzeigen
python dodge.py --last-second      # automatisch ~1,5 s vor Spielstart dodgen
python dodge.py --last-second --margin 3
python dodge.py --watch            # läuft im Hintergrund, Enter = dodge
python dodge.py --path "D:\Games\League of Legends"
```

Den Installationsordner kannst du auch über die Umgebungsvariable `LOL_PATH` setzen.
Wird keine `lockfile` gefunden, liest das Script Port und Token direkt aus dem
`LeagueClientUx`-Prozess.

## Wichtig

- Ein Dodge wird ganz normal bestraft (Queue-Sperre, in Ranked LP-Verlust).
- Nutzung auf eigene Verantwortung.
