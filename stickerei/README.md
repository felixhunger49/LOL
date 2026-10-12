# Bild → Stickdatei (SVG)

`bild_zu_stick.py` wandelt ein Bild (PNG, JPG, …) in eine Stickdatei im SVG-Format um.

## Voraussetzungen

```bash
pip install pillow numpy
```

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
