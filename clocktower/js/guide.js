// Anleitung für Spielleiter und Spieler (HTML-Abschnitte).

const GUIDE = [
  { id: "ziel", title: "Worum geht es?", html: `
    <p><b>Blood on the Clocktower</b> ist ein Bluff- und Deduktionsspiel für 5–15 Spieler (plus bis zu 5 Reisende) und einen <b>Spielleiter</b> (Storyteller).</p>
    <p>Im Dorf versteckt sich ein <b>Dämon</b>, der jede Nacht tötet, unterstützt von seinen <b>Schergen</b>. Die guten Spieler – <b>Dorfbewohner</b> und <b>Außenseiter</b> – versuchen herauszufinden, wer der Dämon ist, und ihn hinzurichten.</p>
    <ul>
      <li><b>Gut gewinnt</b>, wenn der Dämon stirbt.</li>
      <li><b>Böse gewinnt</b>, wenn nur noch 2 Spieler leben (Reisende zählen nicht).</li>
    </ul>
    <p>Tote Spieler bleiben im Spiel: Sie reden weiter mit, dürfen aber nicht mehr nominieren und haben nur noch <b>eine einzige Stimme</b> für den Rest des Spiels.</p>` },

  { id: "app", title: "So funktioniert diese App", html: `
    <ol>
      <li>Der Spielleiter öffnet <b>Spielleiter</b>, wählt Edition und Spielerzahl und trägt die Namen ein.</li>
      <li>Die App wählt passende Rollen aus (oder du wählst sie selbst) und verteilt sie zufällig auf die Plätze.</li>
      <li>Jeder Spieler bekommt seine Rolle auf sein eigenes Handy – auf drei Wegen:
        <ul>
          <li><b>QR-Code scannen:</b> Der Spieler scannt den QR-Code vom Handy des Spielleiters mit seiner Kamera.</li>
          <li><b>Link teilen:</b> Den persönlichen Link per Messenger an den Spieler schicken.</li>
          <li><b>Code eingeben:</b> Der Spieler öffnet die App, tippt auf „Meine Rolle“ und gibt seinen 5-stelligen Code ein.</li>
        </ul>
      </li>
      <li>Alternativ: <b>Handy weitergeben</b> – das Spielleiter-Handy geht reihum, jeder sieht nur seine eigene Rolle.</li>
      <li>Auf seinem Handy kann jeder Spieler seine Rolle und Fähigkeit in Ruhe nachlesen. Die Karte ist verdeckt und wird erst durch Antippen sichtbar – so kann niemand über die Schulter schauen.</li>
      <li>Im <b>Grimoire</b> verwaltet der Spielleiter Leben, Tod, Geisterstimmen und Notizen und hat die <b>Nachtreihenfolge</b> für genau die Rollen im Spiel.</li>
    </ol>
    <p class="hint">Damit QR-Codes und Links auf anderen Handys funktionieren, muss die App online erreichbar sein (z. B. über GitHub Pages). Die Codes funktionieren auch ohne Internet, wenn alle die App geöffnet haben.</p>` },

  { id: "vorbereitung", title: "Spielleiter: Vorbereitung", html: `
    <ol>
      <li><b>Edition wählen.</b> Für Anfänger immer <i>Trouble Brewing</i>.</li>
      <li><b>Rollen nach Spielerzahl wählen</b> (siehe Tabelle unten). Manche Rollen verändern den Aufbau, z. B. der Baron (+2 Außenseiter).</li>
      <li><b>Säufer:</b> Der Säufer-Spieler bekommt eine Dorfbewohner-Rolle gezeigt, die <i>nicht</i> im Spiel ist. Die App macht das automatisch.</li>
      <li><b>Wahrsager:</b> Lege einen guten Spieler als Ablenker (Red Herring) fest.</li>
      <li><b>Bluffs:</b> Lege 3 gute Rollen beiseite, die nicht im Spiel sind. Der Dämon erfährt sie in der ersten Nacht.</li>
      <li><b>Rollen verteilen</b> und das <b>Grimoire</b> (dein geheimer Überblick) vorbereiten.</li>
    </ol>
    <div id="setup-table"></div>` },

  { id: "ablauf", title: "Spielleiter: Spielablauf", html: `
    <h4>1. Die erste Nacht</h4>
    <p>Alle schließen die Augen. Du weckst die Spieler einzeln in der <b>Nachtreihenfolge</b> (siehe Grimoire). Bei 7+ Spielern lernen sich die Bösen kennen: Die Schergen sehen den Dämon, der Dämon sieht seine Schergen und bekommt 3 Bluffs. In der ersten Nacht tötet der Dämon normalerweise nicht.</p>
    <h4>2. Der Tag</h4>
    <p>Alle wachen auf, du verkündest die Toten der Nacht. Dann folgt freie Diskussion: Spieler gehen in kleinen Gruppen herum und tauschen (wahre oder gelogene) Infos aus. Nimm dir je nach Spieleranzahl 5–10 Minuten, später weniger.</p>
    <h4>3. Nominierungen</h4>
    <ul>
      <li>Rufe alle zurück in den Kreis. Jeder <b>lebende</b> Spieler darf pro Tag <b>einmal nominieren</b>, und jeder Spieler darf pro Tag <b>einmal nominiert werden</b>.</li>
      <li>Nominierender und Nominierter dürfen kurz etwas sagen.</li>
      <li><b>Abstimmung:</b> Du gehst im Uhrzeigersinn um den Kreis, beginnend beim Spieler neben dem Nominierten. Wer die Hand hebt, stimmt dafür. Tote Spieler dürfen ihre einzige Geisterstimme benutzen.</li>
      <li>Ein Spieler kommt „auf den Block“, wenn er <b>mindestens die Hälfte der lebenden Spieler</b> an Stimmen bekommt <b>und mehr</b> als der bisher Höchste. Bei Gleichstand ist niemand auf dem Block.</li>
    </ul>
    <h4>4. Hinrichtung</h4>
    <p>Am Ende des Tages wird hingerichtet, wer auf dem Block liegt (höchstens eine Hinrichtung pro Tag). Es muss niemand hingerichtet werden. Dann beginnt die Nacht.</p>
    <h4>5. Weitere Nächte</h4>
    <p>Wie die erste Nacht, aber mit der Reihenfolge „Andere Nächte“: Jetzt tötet der Dämon. Wiederhole Tag und Nacht, bis eine Seite gewinnt.</p>
    <h4>Ende</h4>
    <p>Stirbt der Dämon (und keine Rolle rettet das Spiel, z. B. Scharlachrote Frau), gewinnt sofort Gut. Leben nur noch 2 Spieler, gewinnt Böse. Decke danach das Grimoire auf – das ist oft der lustigste Teil!</p>` },

  { id: "begriffe", title: "Wichtige Begriffe", html: `
    <dl>
      <dt>Betrunken / Vergiftet</dt><dd>Die Fähigkeit wirkt nicht. Der Spieler merkt davon nichts und kann vom Spielleiter falsche Informationen bekommen.</dd>
      <dt>Geisterstimme</dt><dd>Tote Spieler haben noch genau eine Stimme für den Rest des Spiels.</dd>
      <dt>Registrieren als …</dt><dd>Manche Rollen (Spion, Einsiedler) können für Fähigkeiten anders erscheinen, als sie sind.</dd>
      <dt>„Jede Nacht*“</dt><dd>Jede Nacht außer der ersten.</dd>
      <dt>Grimoire</dt><dd>Der geheime Überblick des Spielleiters über alle Rollen und Marker.</dd>
      <dt>Bluffs</dt><dd>Drei gute Rollen, die nicht im Spiel sind. Der Dämon kann sie gefahrlos behaupten.</dd>
      <dt>Verrückt sein (Madness)</dt><dd>Ein Spieler muss überzeugend so tun, als hätte er eine bestimmte Rolle – sonst kann er hingerichtet werden (Cerenovus, Mutant).</dd>
      <dt>Reisende</dt><dd>Spieler, die später dazukommen oder früher gehen. Sie können gut oder böse sein; der Spielleiter legt das fest. Sie können verbannt statt hingerichtet werden.</dd>
    </dl>` },

  { id: "tipps", title: "Tipps für den Spielleiter", html: `
    <ul>
      <li><b>Du bist auf keiner Seite.</b> Dein Ziel ist ein spannendes Spiel, das bis zum Schluss knapp ist.</li>
      <li><b>Falsche Infos</b> an betrunkene/vergiftete Spieler sollten glaubwürdig sein – nicht völlig absurd.</li>
      <li><b>Leise und gleichmäßig</b> in der Nacht: Gehe auch zu Spielern, die nicht aufwachen, damit niemand anhand von Geräuschen etwas erkennt.</li>
      <li><b>Notizen machen:</b> Nutze das Grimoire der App für Tote, Geisterstimmen und Marker (Vergiftet, Geschützt …).</li>
      <li><b>Erklären, nicht lenken:</b> Beantworte Regelfragen, gib aber keine Hinweise auf Rollen.</li>
      <li><b>Zeit im Blick:</b> Ein Spiel dauert etwa 60–90 Minuten. Kürze die Diskussionsphasen später im Spiel.</li>
      <li><b>Anfänger:</b> Erlaube in der ersten Runde ausdrücklich, Fragen zu stellen, und gehe die Spieler-Infos langsam durch.</li>
    </ul>` },

  { id: "spieler", title: "Tipps für Spieler", html: `
    <ul>
      <li><b>Gute Spieler</b> sollten reden, Infos teilen und Widersprüche suchen. Lügen ist erlaubt, aber meist schlecht für Gut.</li>
      <li><b>Böse Spieler</b> lügen über ihre Rolle. Nutze die Bluffs (Dämon) oder behaupte etwas Plausibles.</li>
      <li>Du darfst über deine Rolle sagen, was du willst – aber niemandem dein Handy oder deine Karte zeigen.</li>
      <li>Auch tot bist du wichtig: Diskutiere weiter und setze deine Geisterstimme klug ein.</li>
    </ul>` }
];
