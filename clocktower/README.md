# Blood on the Clocktower – Rollen-App

Eine Web-App (läuft im Browser jedes Handys, keine Installation, kein Server nötig) für
*Blood on the Clocktower*:

- **Rollen-Lexikon:** Alle 87 Rollen der drei Grund-Editionen (Trouble Brewing, Bad Moon Rising,
  Sects & Violets) inkl. Reisende – mit Fähigkeit, Erklärung, Tipp und Spielleiter-Hinweisen.
- **Rollen auf jedes Handy:** Der Spielleiter verteilt die Rollen, jeder Spieler bekommt seine
  Rolle per **QR-Code**, **Link** oder **5-stelligem Code** auf sein eigenes Handy und kann sie dort
  verdeckt aufrufen und in Ruhe nachlesen. Alternativ: **Handy weitergeben**.
- **Spielleiter-Bereich:** Edition und Spielerzahl wählen, Rollen automatisch (regelkonform, inkl.
  Baron/Pate/Fang Gu/Vigormortis) oder von Hand wählen, Säufer & Wahnsinniger werden korrekt
  behandelt, Bluffs für den Dämon, Reisende hinzufügen.
- **Grimoire:** Leben/Tod, Geisterstimmen, Notizen und die **Nachtreihenfolge** (erste Nacht /
  andere Nächte) mit Anweisungen für genau die Rollen im Spiel.
- **Anleitung:** Spielablauf, Nominierungen, Abstimmungen, Begriffe und Tipps für Spielleiter.

## Starten

Lokal testen:

```bash
cd clocktower
python3 -m http.server 8000
# dann http://localhost:8000 im Browser öffnen
```

Damit QR-Codes und Links auf **anderen** Handys funktionieren, muss die App im Internet liegen.
Am einfachsten über GitHub Pages:

1. Im Repository: **Settings → Pages → Source: „GitHub Actions“**.
2. Den Workflow **„Clocktower App veröffentlichen“** unter *Actions* starten (oder auf `main` pushen).
3. Die angezeigte Adresse auf allen Handys öffnen. Tipp: „Zum Startbildschirm hinzufügen“ –
   danach funktioniert die App auch offline.

Die 5-stelligen Codes funktionieren auch ohne Internet, solange die App auf dem Handy geöffnet ist.

*Blood on the Clocktower* ist ein Spiel von The Pandemonium Institute. Diese App ist ein inoffizielles
Fan-Hilfsmittel; die Rollentexte sind eigene, sinngemäße Beschreibungen.
