// Blood on the Clocktower – Rollen-App (ohne Server, alles im Browser).

(function () {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const view = $("#view");

  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- Speicher ----------
  const store = {
    get(key, fallback) {
      try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* privater Modus */ }
    },
    del(key) {
      try { localStorage.removeItem(key); } catch (e) { /* ignorieren */ }
    }
  };

  // ---------- Zufall ----------
  function randInt(n) {
    const a = new Uint32Array(1);
    crypto.getRandomValues(a);
    return a[0] % n;
  }
  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = randInt(i + 1);
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }
  const pick = (arr, k) => shuffle(arr).slice(0, k);

  // ---------- Spieler-Codes (5 Zeichen) ----------
  // 25 Bit: Rolle (7) | Gesinnung (2) | Platz (5) | Salz (5) | Prüfsumme (6), verwürfelt per Multiplikation.
  const ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";
  const MOD = 2 ** 25;
  const MUL = 0x1A3B5C9; // ungerade -> umkehrbar modulo 2^25
  const mulmod = (a, b) => (a * b) % MOD;
  const MUL_INV = (() => {
    let x = MUL;
    for (let i = 0; i < 6; i++) x = mulmod(x, (2 - mulmod(MUL, x) + MOD) % MOD);
    return x;
  })();
  const check6 = p => { const h = Math.imul(p ^ 0x5bd1e995, 0x01000193) >>> 0; return (h ^ (h >>> 13)) & 63; };

  function makeCode(roleIdx, align, seat, salt) {
    const p = roleIdx | (align << 7) | (seat << 9) | (salt << 14);
    let v = mulmod(p * 64 + check6(p), MUL);
    let s = "";
    for (let i = 0; i < 5; i++) { s = ALPHABET[v & 31] + s; v = Math.floor(v / 32); }
    return s;
  }
  function readCode(code) {
    code = code.toUpperCase().replace(/[^0-9A-Z]/g, "");
    if (code.length !== 5) return null;
    let v = 0;
    for (const ch of code) {
      const d = ALPHABET.indexOf(ch);
      if (d < 0) return null;
      v = v * 32 + d;
    }
    v = mulmod(v, MUL_INV);
    const p = Math.floor(v / 64);
    if ((v & 63) !== check6(p)) return null;
    const role = ROLES[p & 127];
    if (!role) return null;
    const align = (p >> 7) & 3;
    return { r: role.id, s: (p >> 9) & 31, a: align === 1 ? "g" : align === 2 ? "e" : undefined };
  }

  // ---------- Links (verschleiert, damit man die Rolle nicht in der URL liest) ----------
  const KEY = new TextEncoder().encode("clocktower-grimoire");
  function encodeLink(obj) {
    const bytes = new TextEncoder().encode(JSON.stringify(obj));
    let bin = "";
    bytes.forEach((b, i) => { bin += String.fromCharCode(b ^ KEY[i % KEY.length]); });
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function decodeLink(str) {
    try {
      const bin = atob(str.replace(/-/g, "+").replace(/_/g, "/"));
      const bytes = Uint8Array.from(bin, (c, i) => c.charCodeAt(0) ^ KEY[i % KEY.length]);
      const obj = JSON.parse(new TextDecoder().decode(bytes));
      return ROLE_BY_ID[obj.r] ? obj : null;
    } catch (e) { return null; }
  }
  const baseUrl = () => location.href.split("#")[0];

  // ---------- Hilfen zu Rollen ----------
  const isGood = (role, align) => role.t === "traveller" ? align !== "e" : TEAMS[role.t].good;
  const teamClass = (role, align) => role.t === "traveller" ? (align === "e" ? "t-evil-trav" : "t-traveller") : "t-" + role.t;
  const rolesOf = (ed, team) => ROLES.filter(r => r.ed === ed && r.t === team);
  const roleName = id => ROLE_BY_ID[id] ? ROLE_BY_ID[id].de : "?";

  // ---------- Rollenkarte ----------
  function cardHtml(info) {
    const role = ROLE_BY_ID[info.r];
    const good = isGood(role, info.a);
    const team = TEAMS[role.t];
    let evil = "";
    if (info.x) {
      const x = info.x;
      evil = `<div class="box evilinfo"><h4>🤫 Geheime Info deines Teams</h4>`;
      if (x.d) evil += `<p>Dein Dämon ist: <b>${esc(x.d)}</b></p>`;
      if (x.m && x.m.length) evil += `<p>${x.d ? "Weitere Schergen" : "Deine Schergen"}: <b>${x.m.map(esc).join(", ")}</b></p>`;
      if (x.m && !x.m.length && !x.d) evil += `<p>Du hast keine Schergen.</p>`;
      if (x.l) evil += `<p>Der Wahnsinnige (glaubt, Dämon zu sein): <b>${esc(x.l)}</b></p>`;
      if (x.b && x.b.length) evil += `<p>Deine Bluffs (gute Rollen, die nicht im Spiel sind):</p><ul>${x.b.map(id => `<li><b>${esc(roleName(id))}</b> – ${esc(ROLE_BY_ID[id].a)}</li>`).join("")}</ul>`;
      evil += `</div>`;
    }
    return `
      <div class="rolecard ${teamClass(role, info.a)}">
        <div class="rc-head">
          ${info.n ? `<div class="rc-for">Für: ${esc(info.n)}</div>` : ""}
          <div class="rc-name">${esc(role.de)}</div>
          <div class="rc-en">${esc(role.en)}</div>
          <div class="rc-team">${team.name} · ${good ? "Gut 😇" : "Böse 😈"}</div>
        </div>
        <div class="rc-body">
          <div class="box ability"><h4>Deine Fähigkeit</h4><p>${esc(role.a)}</p></div>
          <div class="box"><h4>So funktioniert's</h4><p>${esc(role.e)}</p></div>
          ${role.tip ? `<div class="box"><h4>💡 Tipp</h4><p>${esc(role.tip)}</p></div>` : ""}
          ${evil}
          <div class="box win"><h4>🏆 Dein Ziel</h4><p>${good
            ? "Du bist <b>gut</b>. Finde den Dämon und lass ihn hinrichten. Gut gewinnt, wenn der Dämon stirbt."
            : "Du bist <b>böse</b>. Lüge, täusche und schütze den Dämon. Böse gewinnt, wenn nur noch 2 Spieler leben."}</p></div>
          <p class="small">Edition: ${esc(EDITIONS[role.ed].name)}</p>
        </div>
      </div>`;
  }

  // ---------- Modal ----------
  const modal = $("#modal");
  function openModal(html, cls = "") {
    $("#modal-content").innerHTML = html;
    modal.className = "modal " + cls;
    document.body.classList.add("noscroll");
  }
  function closeModal() {
    modal.className = "modal hidden";
    $("#modal-content").innerHTML = "";
    document.body.classList.remove("noscroll");
  }
  $(".modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });

  function toast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2200);
  }

  // =====================================================================
  //  MEINE ROLLE (Spieler)
  // =====================================================================
  function renderPlayer() {
    const mine = store.get("botc.myrole", null);
    if (!mine) {
      view.innerHTML = `
        <section class="panel">
          <h2>Deine Rolle</h2>
          <p>Scanne den <b>QR-Code</b> beim Spielleiter, öffne den Link, den er dir geschickt hat, oder gib hier deinen <b>Code</b> ein.</p>
          <form id="codeform" class="codeform" autocomplete="off">
            <input id="codein" maxlength="7" placeholder="z. B. K7QX2" autocapitalize="characters" spellcheck="false" inputmode="text">
            <button class="btn primary" type="submit">Rolle anzeigen</button>
          </form>
          <p id="codeerr" class="error hidden">Dieser Code ist ungültig. Bitte prüfe die Eingabe.</p>
        </section>
        <section class="panel muted">
          <h3>Du bist der Spielleiter?</h3>
          <p>Wechsle unten zu <a href="#/sl">Spielleiter</a>, um ein Spiel aufzusetzen und die Rollen zu verteilen.</p>
        </section>`;
      $("#codeform").addEventListener("submit", e => {
        e.preventDefault();
        const info = readCode($("#codein").value);
        if (!info) { $("#codeerr").classList.remove("hidden"); return; }
        store.set("botc.myrole", info);
        renderPlayer();
      });
      return;
    }
    view.innerHTML = `
      <section class="reveal-wrap">
        <div id="cover" class="cover" role="button" tabindex="0">
          <div class="cover-icon">🕰️</div>
          <div class="cover-title">${mine.n ? esc(mine.n) + ", deine" : "Deine"} Rolle ist verdeckt</div>
          <div class="cover-sub">Achte darauf, dass niemand mitschaut.<br>Dann tippe hier, um sie anzuzeigen.</div>
        </div>
        <div id="card" class="hidden">${cardHtml(mine)}
          <div class="row center"><button id="hide" class="btn">🙈 Wieder verdecken</button></div>
        </div>
      </section>
      <section class="panel muted">
        <div class="row center wrap">
          <a class="btn" href="#/rollen">📖 Alle Rollen ansehen</a>
          <button id="forget" class="btn danger">Andere Rolle laden</button>
        </div>
      </section>`;
    const show = () => { $("#cover").classList.add("hidden"); $("#card").classList.remove("hidden"); };
    $("#cover").addEventListener("click", show);
    $("#cover").addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") show(); });
    $("#hide").addEventListener("click", () => { $("#card").classList.add("hidden"); $("#cover").classList.remove("hidden"); window.scrollTo(0, 0); });
    $("#forget").addEventListener("click", () => {
      if (confirm("Deine gespeicherte Rolle wirklich entfernen?")) { store.del("botc.myrole"); renderPlayer(); }
    });
  }

  // =====================================================================
  //  SPIELLEITER
  // =====================================================================
  function newGame() {
    return { step: "setup", edition: "tb", count: 7, names: [], selected: [], seats: [], bluffs: [],
      drunkShown: null, lunaticShown: null, evilInfo: false, assignedKey: "", night: "first", done: {} };
  }
  let game = store.get("botc.game", null) || newGame();
  const save = () => store.set("botc.game", game);

  const playerSeats = () => game.seats.filter(s => !s.trav);
  function names() {
    const out = [];
    for (let i = 0; i < game.count; i++) out.push((game.names[i] || "").trim() || `Spieler ${i + 1}`);
    return out;
  }

  // Erlaubte Außenseiter-Anzahlen für die aktuell gewählten bösen Rollen.
  function expected() {
    const base = SETUP_COUNTS[game.count];
    let outs = [base[1]];
    game.selected.forEach(id => {
      const m = OUTSIDER_MODS[id];
      if (m) outs = [...new Set(outs.flatMap(o => m.map(d => o + d)))];
    });
    outs = outs.map(o => Math.max(0, o)).sort((a, b) => a - b);
    return { townsfolk: outs.map(o => game.count - base[2] - base[3] - o), outsider: outs, minion: base[2], demon: base[3] };
  }
  function counts() {
    const c = { townsfolk: 0, outsider: 0, minion: 0, demon: 0 };
    game.selected.forEach(id => c[ROLE_BY_ID[id].t]++);
    return c;
  }

  function autoPick() {
    const ed = game.edition, base = SETUP_COUNTS[game.count];
    const demon = pick(rolesOf(ed, "demon"), 1);
    const minions = pick(rolesOf(ed, "minion"), base[2]);
    let outs = base[1];
    [...demon, ...minions].forEach(r => { const m = OUTSIDER_MODS[r.id]; if (m) outs += m[randInt(m.length)]; });
    const outsiderPool = rolesOf(ed, "outsider");
    outs = Math.max(0, Math.min(outs, outsiderPool.length));
    const tf = game.count - outs - base[2] - base[3];
    const sel = [...demon, ...minions, ...pick(outsiderPool, outs), ...pick(rolesOf(ed, "townsfolk"), tf)];
    game.selected = sel.map(r => r.id);
    refreshHidden();
  }

  // Säufer / Wahnsinniger: welche Rolle sie angezeigt bekommen. Außerdem Bluffs.
  function refreshHidden() {
    const ed = game.edition;
    const inPlay = new Set(game.selected);
    if (inPlay.has("drunk")) {
      const free = rolesOf(ed, "townsfolk").filter(r => !inPlay.has(r.id)).map(r => r.id);
      if (!game.drunkShown || inPlay.has(game.drunkShown) || !free.includes(game.drunkShown)) game.drunkShown = pick(free, 1)[0] || null;
    } else game.drunkShown = null;
    if (inPlay.has("lunatic")) {
      const demons = rolesOf(ed, "demon").map(r => r.id);
      if (!game.lunaticShown || !demons.includes(game.lunaticShown)) game.lunaticShown = game.selected.find(id => ROLE_BY_ID[id].t === "demon") || demons[0];
    } else game.lunaticShown = null;
    // Säufer und Wahnsinniger sind keine sinnvollen Bluffs: Niemand kann behaupten, sie zu sein.
    const blocked = id => inPlay.has(id) || id === game.drunkShown || id === "drunk" || id === "lunatic";
    if (game.bluffs.length !== 3 || game.bluffs.some(blocked)) {
      const pool = ROLES.filter(r => r.ed === ed && (r.t === "townsfolk" || r.t === "outsider") && !blocked(r.id)).map(r => r.id);
      game.bluffs = pick(pool, 3);
    }
  }

  function shownRole(roleId) {
    if (roleId === "drunk" && game.drunkShown) return game.drunkShown;
    if (roleId === "lunatic" && game.lunaticShown) return game.lunaticShown;
    return roleId;
  }

  function assignSeats() {
    const roles = shuffle(game.selected);
    const nm = names();
    const travellers = game.seats.filter(s => s.trav);
    game.seats = roles.map((r, i) => ({ name: nm[i], role: r, alive: true, ghost: true, note: "", salt: randInt(32) }));
    game.seats.push(...travellers);
    game.assignedKey = game.selected.slice().sort().join(",") + "|" + game.count;
    game.done = {};
  }

  function evilInfoFor(seat) {
    if (!game.evilInfo || playerSeats().length < 7 || seat.trav) return undefined;
    const ps = playerSeats();
    const t = ROLE_BY_ID[seat.role].t;
    const demon = ps.find(s => ROLE_BY_ID[s.role].t === "demon");
    const minions = ps.filter(s => ROLE_BY_ID[s.role].t === "minion");
    const lunatic = ps.find(s => s.role === "lunatic");
    if (t === "minion") return { d: demon && demon.name, m: minions.filter(s => s !== seat).map(s => s.name) };
    if (t === "demon") return { m: minions.map(s => s.name), b: game.bluffs, l: lunatic && lunatic.name };
    if (seat.role === "lunatic") {
      // Der Wahnsinnige bekommt plausible, aber falsche Schergen.
      const fake = pick(ps.filter(s => s !== seat), minions.length).map(s => s.name);
      if (!seat.fake || seat.fake.length !== fake.length) { seat.fake = fake; save(); }
      return { m: seat.fake, b: game.bluffs };
    }
    return undefined;
  }

  function seatInfo(seat, i) {
    const shown = shownRole(seat.role);
    const info = { r: shown, n: seat.name, s: i };
    if (seat.trav) info.a = seat.align;
    const x = evilInfoFor(seat);
    if (x) info.x = x;
    return info;
  }
  function seatCode(seat, i) {
    const align = seat.trav ? (seat.align === "e" ? 2 : 1) : 0;
    return makeCode(ROLE_BY_ID[shownRole(seat.role)].idx, align, i, seat.salt);
  }
  const seatLink = (seat, i) => baseUrl() + "#k=" + encodeLink(seatInfo(seat, i));

  // ----- Darstellung -----
  const STEPS = [["setup", "1 · Spiel"], ["roles", "2 · Rollen"], ["assign", "3 · Verteilen"], ["grim", "4 · Grimoire"]];

  function renderSL() {
    const stepper = `<div class="stepper">${STEPS.map(([k, l]) =>
      `<button class="step ${game.step === k ? "active" : ""}" data-step="${k}">${l}</button>`).join("")}</div>`;
    let body = "";
    if (game.step === "setup") body = slSetup();
    else if (game.step === "roles") body = slRoles();
    else if (game.step === "assign") body = slAssign();
    else body = slGrim();
    view.innerHTML = stepper + body;
    $$(".step").forEach(b => b.addEventListener("click", () => goStep(b.dataset.step)));
    bindSL();
  }

  function goStep(step) {
    if ((step === "assign" || step === "grim") && game.selected.length !== game.count) {
      if (!game.selected.length) autoPick();
      else { toast(`Bitte genau ${game.count} Rollen wählen.`); step = "roles"; }
    }
    if ((step === "assign" || step === "grim") && game.selected.length === game.count) {
      const key = game.selected.slice().sort().join(",") + "|" + game.count;
      if (game.assignedKey !== key) { refreshHidden(); assignSeats(); }
    }
    game.step = step;
    save();
    renderSL();
    window.scrollTo(0, 0);
  }

  function slSetup() {
    const nm = [];
    for (let i = 0; i < game.count; i++) nm.push(`<input class="name" data-i="${i}" placeholder="Spieler ${i + 1}" value="${esc(game.names[i] || "")}">`);
    return `
      <section class="panel">
        <h2>Neues Spiel</h2>
        <h3>Edition</h3>
        <div class="chips">${Object.entries(EDITIONS).map(([k, e]) =>
          `<button class="chip ${game.edition === k ? "on" : ""}" data-ed="${k}">${e.name}</button>`).join("")}</div>
        <p class="small">${esc(EDITIONS[game.edition].desc)}</p>
        <h3>Anzahl Spieler (ohne Spielleiter)</h3>
        <div class="counter">
          <button class="btn round" id="minus">−</button>
          <span class="count">${game.count}</span>
          <button class="btn round" id="plus">+</button>
        </div>
        <p class="small center">${setupLine(game.count)}</p>
        <h3>Namen in Sitzreihenfolge (im Uhrzeigersinn)</h3>
        <div class="names">${nm.join("")}</div>
        <div class="row end"><button class="btn primary" id="next1">Weiter: Rollen wählen →</button></div>
      </section>
      <section class="panel muted">
        <div class="row wrap">
          <button class="btn danger" id="reset">🗑️ Komplett neues Spiel</button>
        </div>
      </section>`;
  }
  const setupLine = n => { const c = SETUP_COUNTS[n]; return `${c[0]} Dorfbewohner · ${c[1]} Außenseiter · ${c[2]} Schergen · ${c[3]} Dämon`; };

  function slRoles() {
    const exp = expected(), c = counts();
    const fmt = arr => Array.isArray(arr) ? arr.join(" oder ") : arr;
    const ok = (team) => Array.isArray(exp[team]) ? exp[team].includes(c[team]) : exp[team] === c[team];
    const teamBlock = team => {
      const rs = rolesOf(game.edition, team);
      return `<h3 class="team-h t-${team}-text">${TEAMS[team].plural} <span class="cnt ${ok(team) ? "ok" : "bad"}">${c[team]} / ${fmt(exp[team])}</span></h3>
        <div class="tiles">${rs.map(r => `<button class="tile t-${team} ${game.selected.includes(r.id) ? "on" : ""}" data-role="${r.id}">
          <b>${esc(r.de)}</b><small>${esc(r.a)}</small>${r.setup ? `<em>${esc(r.setup)}</em>` : ""}</button>`).join("")}</div>`;
    };
    const total = game.selected.length;
    let extra = "";
    if (game.selected.includes("drunk")) {
      const free = rolesOf(game.edition, "townsfolk").filter(r => !game.selected.includes(r.id));
      extra += `<label class="field">Der <b>Säufer</b> glaubt, er sei:
        <select id="drunkShown">${free.map(r => `<option value="${r.id}" ${r.id === game.drunkShown ? "selected" : ""}>${esc(r.de)}</option>`).join("")}</select></label>`;
    }
    if (game.selected.includes("lunatic")) {
      extra += `<label class="field">Der <b>Wahnsinnige</b> glaubt, er sei:
        <select id="lunaticShown">${rolesOf(game.edition, "demon").map(r => `<option value="${r.id}" ${r.id === game.lunaticShown ? "selected" : ""}>${esc(r.de)}</option>`).join("")}</select></label>`;
    }
    const warn = total !== game.count ? `<p class="error">Du hast ${total} von ${game.count} Rollen gewählt.</p>`
      : (["townsfolk", "outsider", "minion", "demon"].every(ok) ? `<p class="okmsg">✓ Die Verteilung passt.</p>` : `<p class="warnmsg">Die Anzahl stimmt, weicht aber von der Standard-Verteilung ab. Das ist erlaubt, wenn du es so willst.</p>`);
    return `
      <section class="panel">
        <h2>Rollen für ${game.count} Spieler</h2>
        <p class="small">${esc(EDITIONS[game.edition].name)} · Tippe Rollen an, um sie hinzuzufügen oder zu entfernen.</p>
        <div class="row wrap"><button class="btn primary" id="auto">🎲 Zufällig auswählen</button><button class="btn" id="clear">Auswahl leeren</button></div>
        ${warn}
        ${extra}
        ${["townsfolk", "outsider", "minion", "demon"].map(teamBlock).join("")}
        <div class="row end"><button class="btn primary" id="next2" ${total === game.count ? "" : "disabled"}>Weiter: Verteilen →</button></div>
      </section>`;
  }

  function roleChip(id, extra = "") {
    const r = ROLE_BY_ID[id];
    return `<span class="rchip t-${r.t}">${esc(r.de)}${extra}</span>`;
  }

  function slAssign() {
    const ps = game.seats;
    const allowEvil = playerSeats().length >= 7;
    const rows = ps.map((s, i) => {
      const r = ROLE_BY_ID[s.role];
      const shown = shownRole(s.role);
      const sel = s.trav
        ? roleChip(s.role, s.align === "e" ? " (böse)" : " (gut)")
        : `<select class="seatrole" data-i="${i}">${game.selected.map(id => `<option value="${id}" ${id === s.role ? "selected" : ""}>${esc(roleName(id))}</option>`).join("")}</select>`;
      return `<div class="seat t-${r.t}-border">
        <div class="seat-top"><span class="seatno">${i + 1}</span><b class="seatname">${esc(s.name)}</b>
          ${shown !== s.role ? `<span class="small">sieht: ${esc(roleName(shown))}</span>` : ""}</div>
        <div class="seat-mid">${sel}</div>
        <div class="seat-bot"><code class="code">${seatCode(s, i)}</code>
          <button class="btn sm" data-qr="${i}">📱 QR / Link</button>
          ${s.trav ? `<button class="btn sm danger" data-deltrav="${i}">✕</button>` : ""}</div>
      </div>`;
    }).join("");
    const travOpts = ROLES.filter(r => r.t === "traveller").map(r => `<option value="${r.id}">${esc(r.de)} (${esc(EDITIONS[r.ed].name)})</option>`).join("");
    return `
      <section class="panel">
        <h2>Rollen verteilen</h2>
        <p>Jeder Spieler holt sich seine Rolle: <b>QR-Code scannen</b>, <b>Link</b> öffnen oder in der App unter „Meine Rolle“ den <b>Code</b> eingeben. Oder gib dein Handy reihum.</p>
        <div class="row wrap">
          <button class="btn primary" id="pass">🔄 Handy weitergeben</button>
          <button class="btn" id="reshuffle">🎲 Neu mischen</button>
        </div>
        ${location.protocol === "file:" ? `<p class="warnmsg">Die App läuft gerade als lokale Datei. QR-Codes und Links funktionieren auf anderen Handys nur, wenn die App im Internet liegt (z. B. GitHub Pages). Die Codes funktionieren trotzdem.</p>` : ""}
        <label class="switch ${allowEvil ? "" : "disabled"}"><input type="checkbox" id="evilinfo" ${game.evilInfo && allowEvil ? "checked" : ""} ${allowEvil ? "" : "disabled"}>
          <span>Böse-Infos auf die Karten schreiben (Schergen sehen den Dämon, der Dämon sieht Schergen &amp; Bluffs). ${allowEvil ? "Ersetzt das Aufwecken in der ersten Nacht. Funktioniert nur über QR/Link/Handy weitergeben, nicht über Codes." : "Erst ab 7 Spielern."}</span></label>
        <div class="seats">${rows}</div>
        <div class="box"><h4>Bluffs für den Dämon</h4><p>${game.bluffs.map(id => roleChip(id)).join(" ")}</p>
          <button class="btn sm" id="rebluff">🎲 Andere Bluffs</button></div>
      </section>
      <section class="panel">
        <h3>Reisenden hinzufügen</h3>
        <p class="small">Reisende kommen später dazu oder gehen früher. Du legst fest, ob sie gut oder böse sind.</p>
        <div class="travform">
          <input id="travname" placeholder="Name">
          <select id="travrole">${travOpts}</select>
          <select id="travalign"><option value="g">Gut</option><option value="e">Böse</option></select>
          <button class="btn" id="addtrav">+ Hinzufügen</button>
        </div>
      </section>
      <div class="row end"><button class="btn primary" id="next3">Weiter: Grimoire →</button></div>`;
  }

  function slGrim() {
    const ps = game.seats;
    const seats = ps.map((s, i) => {
      const shown = shownRole(s.role);
      return `<div class="gseat ${s.alive ? "" : "dead"}">
        <div class="g-top">
          <span class="seatno">${i + 1}</span>
          <b>${esc(s.name)}</b>
          ${roleChip(s.role, s.trav ? (s.align === "e" ? " · böse" : " · gut") : "")}
          ${shown !== s.role ? `<span class="small">(glaubt: ${esc(roleName(shown))})</span>` : ""}
        </div>
        <div class="g-ctl">
          <button class="btn sm" data-alive="${i}">${s.alive ? "❤️ lebt" : "💀 tot"}</button>
          ${s.alive ? "" : `<button class="btn sm" data-ghost="${i}">${s.ghost ? "👻 Stimme frei" : "🚫 Stimme verbraucht"}</button>`}
          <button class="btn sm" data-info="${s.role}">ℹ️</button>
        </div>
        <input class="note" data-note="${i}" placeholder="Notiz (z. B. vergiftet, geschützt, Ablenker …)" value="${esc(s.note)}">
      </div>`;
    }).join("");
    const alive = ps.filter(s => s.alive && !s.trav).length;
    const night = game.night === "first" ? NIGHT_FIRST : NIGHT_OTHER;
    const key = game.night === "first" ? "n1" : "n";
    const steps = [];
    night.forEach(id => {
      if (NIGHT_STEPS[id]) {
        if ((id === "minioninfo" || id === "demoninfo") && playerSeats().length < 7) return;
        if (NIGHT_STEPS[id][key]) steps.push({ id, name: NIGHT_STEPS[id].de, text: NIGHT_STEPS[id][key], who: "" });
        return;
      }
      const role = ROLE_BY_ID[id];
      if (!role || !role[key]) return;
      const holders = ps.filter(s => s.role === id);
      const drunks = ps.filter(s => s.role === "drunk" && shownRole("drunk") === id);
      if (!holders.length && !drunks.length) return;
      const who = [...holders.map(s => esc(s.name) + (s.alive ? "" : " †")), ...drunks.map(s => esc(s.name) + " (Säufer – Info darf falsch sein)")].join(", ");
      steps.push({ id, name: role.de, text: role[key], who, t: role.t });
    });
    const done = game.done[game.night] || [];
    return `
      <section class="panel">
        <h2>Grimoire</h2>
        <p class="small">${alive} von ${playerSeats().length} Spielern leben · Für eine Hinrichtung nötig: <b>${Math.ceil(alive / 2)}</b> Stimmen</p>
        <div class="gseats">${seats}</div>
        <div class="box"><h4>Bluffs</h4><p>${game.bluffs.map(id => roleChip(id)).join(" ")}</p></div>
      </section>
      <section class="panel">
        <h2>Nachtreihenfolge</h2>
        <div class="chips">
          <button class="chip ${game.night === "first" ? "on" : ""}" data-night="first">🌙 Erste Nacht</button>
          <button class="chip ${game.night === "other" ? "on" : ""}" data-night="other">🌑 Andere Nächte</button>
        </div>
        <ol class="nightlist">${steps.map(s => `
          <li class="${done.includes(s.id) ? "done" : ""} ${s.t ? "t-" + s.t + "-border" : ""}" data-step-id="${s.id}">
            <div class="ns-head"><input type="checkbox" ${done.includes(s.id) ? "checked" : ""}><b>${esc(s.name)}</b>${s.who ? `<span class="who">${s.who}</span>` : ""}</div>
            <p>${esc(s.text)}</p>
          </li>`).join("")}</ol>
        <div class="row"><button class="btn" id="resetnight">Häkchen zurücksetzen</button></div>
      </section>`;
  }

  function bindSL() {
    // Schritt 1
    $$("[data-ed]").forEach(b => b.addEventListener("click", () => {
      if (game.edition !== b.dataset.ed) { game.edition = b.dataset.ed; game.selected = []; game.bluffs = []; }
      save(); renderSL();
    }));
    const setCount = n => {
      game.count = Math.max(5, Math.min(15, n));
      if (game.selected.length && game.selected.length !== game.count) game.selected = [];
      save(); renderSL();
    };
    $("#minus") && $("#minus").addEventListener("click", () => setCount(game.count - 1));
    $("#plus") && $("#plus").addEventListener("click", () => setCount(game.count + 1));
    $$(".name").forEach(inp => inp.addEventListener("input", () => {
      game.names[+inp.dataset.i] = inp.value;
      save();
    }));
    $("#next1") && $("#next1").addEventListener("click", () => {
      // Namen in bestehende Plätze übernehmen
      const nm = names();
      playerSeats().forEach((s, i) => { s.name = nm[i] || s.name; });
      goStep("roles");
    });
    $("#reset") && $("#reset").addEventListener("click", () => {
      if (confirm("Alles zurücksetzen? Namen, Rollen und Grimoire gehen verloren.")) { game = newGame(); save(); renderSL(); }
    });

    // Schritt 2
    $("#auto") && $("#auto").addEventListener("click", () => { autoPick(); save(); renderSL(); });
    $("#clear") && $("#clear").addEventListener("click", () => { game.selected = []; save(); renderSL(); });
    $$(".tile").forEach(t => t.addEventListener("click", () => {
      const id = t.dataset.role;
      game.selected = game.selected.includes(id) ? game.selected.filter(x => x !== id) : [...game.selected, id];
      refreshHidden(); save(); renderSL();
    }));
    $("#drunkShown") && $("#drunkShown").addEventListener("change", e => { game.drunkShown = e.target.value; game.bluffs = game.bluffs.filter(b => b !== game.drunkShown); refreshHidden(); save(); });
    $("#lunaticShown") && $("#lunaticShown").addEventListener("change", e => { game.lunaticShown = e.target.value; save(); });
    $("#next2") && $("#next2").addEventListener("click", () => goStep("assign"));

    // Schritt 3
    $$(".seatrole").forEach(sel => sel.addEventListener("change", () => {
      const i = +sel.dataset.i, id = sel.value;
      const other = game.seats.findIndex((s, j) => j !== i && !s.trav && s.role === id);
      if (other >= 0) game.seats[other].role = game.seats[i].role;
      game.seats[i].role = id;
      save(); renderSL();
    }));
    $$("[data-qr]").forEach(b => b.addEventListener("click", () => showQR(+b.dataset.qr)));
    $$("[data-deltrav]").forEach(b => b.addEventListener("click", () => { game.seats.splice(+b.dataset.deltrav, 1); save(); renderSL(); }));
    $("#pass") && $("#pass").addEventListener("click", () => passMode(0));
    $("#reshuffle") && $("#reshuffle").addEventListener("click", () => {
      if (confirm("Rollen neu auf die Plätze verteilen? Bereits verteilte Codes werden ungültig.")) { assignSeats(); save(); renderSL(); }
    });
    $("#rebluff") && $("#rebluff").addEventListener("click", () => { game.bluffs = []; refreshHidden(); save(); renderSL(); });
    $("#evilinfo") && $("#evilinfo").addEventListener("change", e => { game.evilInfo = e.target.checked; save(); });
    $("#addtrav") && $("#addtrav").addEventListener("click", () => {
      const name = $("#travname").value.trim() || `Reisender ${game.seats.filter(s => s.trav).length + 1}`;
      game.seats.push({ name, role: $("#travrole").value, align: $("#travalign").value, trav: true, alive: true, ghost: true, note: "", salt: randInt(32) });
      save(); renderSL();
    });
    $("#next3") && $("#next3").addEventListener("click", () => goStep("grim"));

    // Schritt 4
    $$("[data-alive]").forEach(b => b.addEventListener("click", () => { const s = game.seats[+b.dataset.alive]; s.alive = !s.alive; if (s.alive) s.ghost = true; save(); renderSL(); }));
    $$("[data-ghost]").forEach(b => b.addEventListener("click", () => { const s = game.seats[+b.dataset.ghost]; s.ghost = !s.ghost; save(); renderSL(); }));
    $$("[data-note]").forEach(inp => inp.addEventListener("input", () => { game.seats[+inp.dataset.note].note = inp.value; save(); }));
    $$("[data-info]").forEach(b => b.addEventListener("click", () => openModal(roleDetail(ROLE_BY_ID[b.dataset.info], true))));
    $$("[data-night]").forEach(b => b.addEventListener("click", () => { game.night = b.dataset.night; save(); renderSL(); }));
    $$(".nightlist li").forEach(li => li.addEventListener("click", () => {
      const id = li.dataset.stepId;
      const d = game.done[game.night] = game.done[game.night] || [];
      game.done[game.night] = d.includes(id) ? d.filter(x => x !== id) : [...d, id];
      save(); renderSL();
    }));
    $("#resetnight") && $("#resetnight").addEventListener("click", () => { game.done[game.night] = []; save(); renderSL(); });
  }

  function showQR(i) {
    const seat = game.seats[i];
    const link = seatLink(seat, i);
    let qrSvg = "";
    try {
      const qr = qrcode(0, "L");
      qr.addData(link);
      qr.make();
      qrSvg = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
    } catch (e) { qrSvg = `<p class="error">QR-Code konnte nicht erzeugt werden.</p>`; }
    openModal(`
      <h2 class="center">${esc(seat.name)}</h2>
      <p class="center small">Mit der Handy-Kamera scannen – die Rolle öffnet sich verdeckt.</p>
      <div class="qr">${qrSvg}</div>
      <p class="center">Code: <code class="code big">${seatCode(seat, i)}</code></p>
      <div class="row center wrap">
        <button class="btn" id="copylink">🔗 Link kopieren</button>
        ${navigator.share ? `<button class="btn primary" id="sharelink">📤 Link teilen</button>` : ""}
      </div>`);
    $("#copylink").addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(link); toast("Link kopiert"); }
      catch (e) { prompt("Link kopieren:", link); }
    });
    $("#sharelink") && $("#sharelink").addEventListener("click", () => {
      navigator.share({ title: "Deine Clocktower-Rolle", text: `${seat.name}, hier ist deine geheime Rolle:`, url: link }).catch(() => {});
    });
  }

  // Handy reihum weitergeben
  function passMode(i) {
    const ps = game.seats;
    if (i >= ps.length) {
      openModal(`<div class="pass center"><div class="cover-icon">✅</div><h2>Alle Rollen verteilt</h2>
        <p>Gib das Handy zurück an den Spielleiter.</p><button class="btn primary" id="passend">Fertig</button></div>`, "full");
      $("#passend").addEventListener("click", closeModal);
      return;
    }
    const seat = ps[i];
    openModal(`<div class="pass center">
        <div class="cover-icon">📱</div>
        <p>Gib das Handy an</p>
        <h2 class="bigname">${esc(seat.name)}</h2>
        <p class="small">Platz ${i + 1} von ${ps.length}</p>
        <button class="btn primary big" id="iam">Ich bin ${esc(seat.name)} – Rolle zeigen</button>
      </div>`, "full");
    $("#iam").addEventListener("click", () => {
      openModal(`${cardHtml(seatInfo(seat, i))}
        <div class="row center"><button class="btn primary big" id="seen">Gesehen – Karte verdecken</button></div>
        <p class="center small">Dein Code, falls du die Rolle später auf deinem Handy öffnen willst: <code class="code">${seatCode(seat, i)}</code></p>`, "full");
      $("#seen").addEventListener("click", () => passMode(i + 1));
    });
  }

  // =====================================================================
  //  ROLLEN-LEXIKON
  // =====================================================================
  let lexFilter = { ed: "all", team: "all", q: "" };

  function roleDetail(r, forST) {
    return `<div class="lex-detail">
      <div class="lex-title t-${r.t}-text"><b>${esc(r.de)}</b> <span class="small">${esc(r.en)} · ${TEAMS[r.t].name} · ${esc(EDITIONS[r.ed].name)}</span></div>
      <p class="ability-line">${esc(r.a)}</p>
      <p>${esc(r.e)}</p>
      ${r.tip ? `<p><b>💡 Tipp:</b> ${esc(r.tip)}</p>` : ""}
      ${r.setup ? `<p><b>⚙️ Aufbau:</b> ${esc(r.setup)}</p>` : ""}
      ${forST || r.st || r.n1 || r.n ? `<div class="st-notes">
        ${r.st ? `<p><b>📜 Spielleiter:</b> ${esc(r.st)}</p>` : ""}
        ${r.n1 ? `<p><b>🌙 Erste Nacht:</b> ${esc(r.n1)}</p>` : ""}
        ${r.n ? `<p><b>🌑 Andere Nächte:</b> ${esc(r.n)}</p>` : ""}
      </div>` : ""}
    </div>`;
  }

  function renderLex() {
    view.innerHTML = `
      <section class="panel">
        <h2>Alle Rollen</h2>
        <input id="lexq" class="search" placeholder="🔍 Rolle suchen …" value="${esc(lexFilter.q)}">
        <div class="chips">
          <button class="chip ${lexFilter.ed === "all" ? "on" : ""}" data-led="all">Alle</button>
          ${Object.entries(EDITIONS).map(([k, e]) => `<button class="chip ${lexFilter.ed === k ? "on" : ""}" data-led="${k}">${e.name}</button>`).join("")}
        </div>
        <div class="chips">
          <button class="chip ${lexFilter.team === "all" ? "on" : ""}" data-lteam="all">Alle Typen</button>
          ${Object.entries(TEAMS).map(([k, t]) => `<button class="chip t-${k}-chip ${lexFilter.team === k ? "on" : ""}" data-lteam="${k}">${t.plural}</button>`).join("")}
        </div>
      </section>
      <div id="lexlist"></div>`;
    const draw = () => {
      const q = lexFilter.q.toLowerCase();
      const list = ROLES.filter(r => (lexFilter.ed === "all" || r.ed === lexFilter.ed)
        && (lexFilter.team === "all" || r.t === lexFilter.team)
        && (!q || (r.de + " " + r.en + " " + r.a).toLowerCase().includes(q)));
      let html = "";
      Object.keys(EDITIONS).forEach(ed => {
        const part = list.filter(r => r.ed === ed);
        if (!part.length) return;
        html += `<section class="panel"><h2>${esc(EDITIONS[ed].name)} <span class="small">(${esc(EDITIONS[ed].de)})</span></h2>`;
        Object.keys(TEAMS).forEach(team => {
          const tp = part.filter(r => r.t === team);
          if (!tp.length) return;
          html += `<h3 class="team-h t-${team}-text">${TEAMS[team].plural}</h3>`;
          html += tp.map(r => `<details class="lex t-${team}-border"><summary><b>${esc(r.de)}</b> <span class="small">${esc(r.en)}</span><span class="lex-a">${esc(r.a)}</span></summary>${roleDetail(r, false)}</details>`).join("");
        });
        html += `</section>`;
      });
      $("#lexlist").innerHTML = html || `<p class="panel">Keine Rolle gefunden.</p>`;
    };
    draw();
    $("#lexq").addEventListener("input", e => { lexFilter.q = e.target.value; draw(); });
    $$("[data-led]").forEach(b => b.addEventListener("click", () => { lexFilter.ed = b.dataset.led; renderLex(); }));
    $$("[data-lteam]").forEach(b => b.addEventListener("click", () => { lexFilter.team = b.dataset.lteam; renderLex(); }));
  }

  // =====================================================================
  //  ANLEITUNG
  // =====================================================================
  function renderGuide() {
    view.innerHTML = `<section class="panel"><h2>Anleitung</h2>
      ${GUIDE.map((g, i) => `<details class="guide" ${i < 2 ? "open" : ""}><summary>${esc(g.title)}</summary><div class="guide-body">${g.html}</div></details>`).join("")}
      </section>`;
    const tbl = $("#setup-table");
    if (tbl) {
      tbl.innerHTML = `<table class="setup"><thead><tr><th>Spieler</th><th class="t-townsfolk-text">Dorfb.</th><th class="t-outsider-text">Außens.</th><th class="t-minion-text">Schergen</th><th class="t-demon-text">Dämon</th></tr></thead><tbody>${
        Object.entries(SETUP_COUNTS).map(([n, c]) => `<tr><td>${n}</td>${c.map(x => `<td>${x}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }
  }

  // =====================================================================
  //  ROUTER
  // =====================================================================
  function route() {
    const h = location.hash;
    if (h.startsWith("#k=")) {
      const info = decodeLink(h.slice(3));
      if (info) store.set("botc.myrole", info);
      history.replaceState(null, "", "#/rolle");
      if (!info) toast("Der Link ist ungültig.");
    }
    const tab = (location.hash.match(/^#\/(\w+)/) || [])[1] || (store.get("botc.myrole", null) ? "rolle" : "anleitung");
    $$(".tabbar a").forEach(a => a.classList.toggle("active", a.dataset.tab === tab));
    closeModal();
    if (tab === "sl") renderSL();
    else if (tab === "rollen") renderLex();
    else if (tab === "anleitung") renderGuide();
    else renderPlayer();
  }
  window.addEventListener("hashchange", route);
  route();

  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  }

  // Für Tests im Browser
  window.__botc = { makeCode, readCode, encodeLink, decodeLink };
})();
