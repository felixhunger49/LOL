# Bild → Stickdatei (SVG für Inkscape/Ink/Stitch)

Die Programme erzeugen SVG-Dateien mit **Ink/Stitch-Objekten** – Satinsäulen und
Füllflächen. Die eigentlichen Stiche berechnet [Ink/Stitch](https://inkstitch.org)
in Inkscape; dort lassen sich alle Parameter (Dichte, Unterlage, Winkel …) noch
anpassen und die Datei als DST, PES, JEF, EXP … für die Stickmaschine exportieren.

## Voraussetzungen

```bash
pip install -r requirements.txt
```

## Allgemein: `bild_zu_stick.py`

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
| `--reihenabstand` | Ink/Stitch: Abstand der Füllreihen in mm | 0.25 |
| `--stichlaenge` | Ink/Stitch: maximale Stichlänge in mm | 3.0 |
| `--min-flaeche` | kleinere Flächen weglassen (mm²) | 4 |
| `--glaetten` | Durchgänge des Glättungsfilters | 2 |

Ablauf: Bild skalieren → Farben per k-Means reduzieren → Störflecken glätten,
Hintergrund (häufigste Randfarbe) entfernen → jede Farbe als Ink/Stitch-Füllfläche
(Tatami mit Unterlage) in eine eigene Ebene. Helle Farben zuerst, dunkle zuletzt.

Logos und Grafiken mit klaren Flächen liefern deutlich bessere Ergebnisse als Fotos.

## Beispiel: Applikations-Pinguin (`pinguin.py`)

Erzeugt aus `beispiele/pinguin.jpg` die Datei `beispiele/pinguin.svg` (plus
Vorschau `beispiele/pinguin.png`). Motiv 100 mm hoch, Datei inkl. 2 mm Rand
ca. 74 × 104 mm. Für einen 10×10-Rahmen `--hoehe 95` verwenden.

```bash
python pinguin.py                # Standard: 100 mm hoch
python pinguin.py --hoehe 90     # kleiner
```

- **Satinsäulen** an allen Rändern: Körperumriss (grau), Gesicht und Bauch
  (creme), Halstuch (blau), Füße (orange), dazu Flügelnähte, Zehen, Knoten und
  Augenbrauen. Ränder, die von einem darüberliegenden Teil verdeckt werden,
  entfallen.
- **Keine Füllung** auf Körper, Gesicht, Bauch, Halstuch und Füßen –
  diese Flächen sind als Stoff (Applikation) gedacht.
- **Füllflächen** nur für Schnabel und Augen (mit weißem Lichtpunkt).

Stickreihenfolge = Reihenfolge der Ebenen: Grau → Creme → Blau → Orange →
Schwarz → Weiß (5 Farbwechsel).

## Aufbau der SVG

- Eine Inkscape-Ebene pro Garnfarbe, Maße in mm.
- **Satinsäule:** Pfad ohne Füllung mit `inkstitch:satin_column="True"`,
  bestehend aus zwei Schienen (gleiche Richtung, nicht mit `Z` geschlossen) und
  mindestens drei Querstreben. Unterlage: Mittellinie
  (`center_walk_underlay`), Dichte 0.4 mm. Geschlossene Ränder sind an einer
  Stelle aufgebrochen, die Schienen enden dort, wo sie beginnen. In engen
  Innenkurven wird die Breite automatisch verringert, damit keine Schlaufen
  entstehen.
- **Füllfläche:** geschlossener Pfad mit Füllfarbe, ohne Kontur
  (`fill_method="tatami_fill"`, mit Unterlage).

| Datei | Inhalt |
|---|---|
| `inkstitch.py` | Satinsäulen, Füllflächen und SVG-Dokument für Ink/Stitch |
| `stiche.py` | Geometrie-Helfer (Linien glätten, gleichmäßig verteilen, Normalen) |
| `bild_zu_stick.py` | allgemeines Bild → Füllflächen |
| `pinguin.py` | Applikations-Pinguin mit Satinrändern |
