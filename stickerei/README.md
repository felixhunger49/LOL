# Bild → Stickdatei (SVG)

`bild_zu_stick.py` wandelt ein Bild (PNG, JPG, …) in eine Stickdatei im SVG-Format um.

## Voraussetzungen

```bash
pip install -r requirements.txt
```

(`bild_zu_stick.py` braucht nur `pillow` und `numpy`.)

## Nutzung

```bash
python bild_zu_stick.py logo.png                 # 80 mm breit, 6 Farben -> logo.svg
python bild_zu_stick.py logo.png -b 100 -f 4     # 100 mm breit, 4 Farben
python bild_zu_stick.py foto.jpg -o motiv.svg --mit-hintergrund
```

| Option | Bedeutung | Standard |
|---|---|---|
| `-b`, `--breite` | Breite des Motivs in mm | 80 |
| `-f`, `--farben` | Anzahl Garnfarben (inkl. Hintergrund) | 6 |
| `--mit-hintergrund` | Hintergrundfarbe auch sticken | aus |
| `--reihenabstand` | Abstand der Füllreihen in mm (Dichte) | 0.4 |
| `--stichlaenge` | maximale Stichlänge in mm | 3.0 |
| `--min-flaeche` | kleinere Flächen weglassen (mm²) | 4 |
| `--max-verbindung` | bis zu diesem Abstand weitersticken statt springen (mm) | 2.0 |
| `--glaetten` | Durchgänge des Glättungsfilters | 2 |

## Wie es funktioniert

1. Bild auf die Zielgröße skalieren (10 Rasterpunkte pro mm)
2. Farben per k-Means auf wenige Garnfarben reduzieren
3. Kleine Störflecken glätten; Hintergrund (häufigste Randfarbe) entfernen
4. Jede Farbfläche mit Tatami-Füllstichen füllen (Zickzack-Reihen, versetzte
   Einstichpunkte gegen Rillenbildung)
5. Helle Farben zuerst, dunkle zuletzt – Konturen liegen obenauf

## Ausgabe

- Eine Ebene (`<g>`) pro Garnfarbe, Maße in mm
- Jeder Punkt eines Pfads ist ein Einstichpunkt, ein neuer Pfad = Sprungstich
- Pfade sind als „manuelle Stiche“ für [Ink/Stitch](https://inkstitch.org) markiert:
  SVG in Inkscape öffnen und über Ink/Stitch als DST, PES, JEF, EXP … für die
  Stickmaschine exportieren.

Fotos funktionieren, Logos und Grafiken mit klaren Flächen liefern aber deutlich
bessere Stickergebnisse.

## Beispiel: Applikations-Pinguin (`pinguin.py`)

Erzeugt aus `beispiele/pinguin.jpg` die Stickdatei `beispiele/pinguin.svg`
(plus Vorschau `beispiele/pinguin.png`), Motiv 100 mm hoch, Datei inkl. 2 mm
Rand ca. 74 × 104 mm. Für einen 10×10-Rahmen `--hoehe 95` verwenden.

```bash
python pinguin.py                # Standard: 100 mm hoch
python pinguin.py --hoehe 90     # kleiner
```

- **Satinstich** an allen Rändern: Körperumriss (grau), Gesicht und Bauch
  (creme), Halstuch (blau), Füße (orange), dazu Flügelnähte, Zehen und Knoten.
  Ränder, die von einem darüberliegenden Teil verdeckt werden, entfallen.
- **Keine Füllung** auf Körper, Gesicht, Bauch, Halstuch und Füßen –
  diese Flächen sind als Stoff (Applikation) gedacht.
- **Füllstich** nur für Schnabel und Augen (mit weißem Lichtpunkt),
  Augenbrauen als schmale Satinraupe.
- Jeder Satinrand hat eine Geradstich-Unterlage, jeder Pfad wird am Anfang und
  Ende vernäht.

Stickreihenfolge: Grau → Creme → Blau → Orange → Schwarz → Weiß (5 Farbwechsel).
Für eine echte Applikation in Ink/Stitch vor jedem Satinrand eine
Platzierungs- und Heftlinie einfügen und den Stoff dazwischen auflegen.
