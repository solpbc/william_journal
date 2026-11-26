/* core.js — the engine under William's 1595 desktop.
   Window manager + seven working apps + store. Each desktop supplies only its
   own chrome through an `env` object:
     env.root            element windows live in
     env.frame(win)      -> { el, body }   el holds [data-drag] [data-close] [data-min] [data-max] [data-resize]
     env.place(app, n)   -> { x, y, w, h }  (optional)
     env.onChange(wins)  dock / taskbar refresh (optional)
     env.notice(n)       show { title, body, app } (optional)
   Staging (tooling, never drawn): ?frame=<day>/<segment>, ?call=<day>/<segment>, ?open=a,b&focus=a&t=HH:MM, ?quiet=1, ?reset=1 */
(function () {
  const D = window.W1595;
  const SCENE = new URLSearchParams(location.search).get("scene");
  const LS = SCENE ? "w1595:scene:" + SCENE + ":" : "w1595:";
  if (SCENE) try { Object.keys(localStorage).filter(k => k.startsWith(LS)).forEach(k => localStorage.removeItem(k)); } catch (e) {}
  const $ = (sel, el = document) => el.querySelector(sel);
  const h = (tag, attrs = {}, ...kids) => {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(kid));
    return el;
  };

  /* ---------- store ---------- */
  const store = {
    get(k, d) { try { const v = localStorage.getItem(LS + k); return v == null ? structuredClone(d) : JSON.parse(v); } catch (e) { return structuredClone(d); } },
    set(k, v) { try { localStorage.setItem(LS + k, JSON.stringify(v)); } catch (e) {} },
    reset() { Object.keys(localStorage).filter(k => k.startsWith(LS)).forEach(k => localStorage.removeItem(k)); }
  };

  /* ---------- period numbers, money, time ---------- */
  function roman(n) {
    if (!n || n < 0) return "";
    const map = [[1000, "m"], [500, "d"], [100, "c"], [90, "xc"], [50, "l"], [40, "xl"], [10, "x"], [9, "ix"], [5, "v"], [4, "iiij"], [1, "i"]];
    let out = "";
    for (const [v, s] of map) while (n >= v) { out += s; n -= v; }
    return out.replace(/i$/, "j");
  }
  function unroman(s) {
    const v = { i: 1, j: 1, v: 5, x: 10, l: 50, c: 100, d: 500, m: 1000 };
    s = s.toLowerCase(); let t = 0;
    for (let i = 0; i < s.length; i++) { const a = v[s[i]], b = v[s[i + 1]] || 0; t += a < b ? -a : a; }
    return t;
  }
  const lsd = {
    split(p) { p = Math.round(p || 0); return { l: Math.floor(p / 240), s: Math.floor((p % 240) / 12), d: p % 12 }; },
    fmt(p, useRoman = true) {
      if (p == null || p === "") return "";
      if (p === 0) return useRoman ? "nil" : "0";
      const { l, s, d } = lsd.split(p), r = [];
      if (useRoman) { if (l) r.push(roman(l) + " li"); if (s) r.push(roman(s) + " s"); if (d) r.push(roman(d) + " d"); }
      else { if (l) r.push("£" + l); if (s) r.push(s + "s"); if (d) r.push(d + "d"); }
      return r.join(" ");
    },
    parse(str) {
      if (str == null) return null;
      str = String(str).trim().toLowerCase();
      if (!str) return null;
      if (str === "nil" || str === "nothing") return 0;
      let total = 0, hit = false;
      str = str.replace(/£\s*(\d+)/g, "$1 li");
      const re = /(\d+|[ivxlcdmj]+)\s*(li|l|s|d)\b/g; let m;
      while ((m = re.exec(str))) {
        hit = true;
        const n = /\d/.test(m[1]) ? parseInt(m[1], 10) : unroman(m[1]);
        total += m[2].startsWith("l") ? n * 240 : m[2] === "s" ? n * 12 : n;
      }
      if (!hit && /^\d+$/.test(str)) return parseInt(str, 10);
      return hit ? total : null;
    }
  };

  const params = new URLSearchParams(location.search);
  if (params.get("reset")) store.reset();
  const loadedAt = Date.now();
  let startAt = new Date(D.start);
  if (params.get("t")) { const [hh, mm] = params.get("t").split(":").map(Number); startAt.setHours(hh, mm || 0, 0); }
  const now = () => new Date(startAt.getTime() + (Date.now() - loadedAt));
  const WEEKDAY = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const MONTH = ["Januarie", "Februarie", "March", "Aprill", "May", "June", "Julie", "August", "September", "October", "November", "December"];
  const NUMW = ["twelve", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven"];
  const time = {
    now,
    dateWords(d = now()) { return `${WEEKDAY[d.getDay()]} the ${roman(d.getDate())} of ${MONTH[d.getMonth()]}, 1595`; },
    shortDate(d = now()) { return `${WEEKDAY[d.getDay()].slice(0, 3)} ${roman(d.getDate())} ${MONTH[d.getMonth()].slice(0, 3)}`; },
    hourWords(d = now()) {
      const H = d.getHours(), M = d.getMinutes();
      let hr = H % 12, part;
      if (M < 8) part = "";
      else if (M < 23) part = "a quarter past ";
      else if (M < 38) part = "half an hour past ";
      else if (M < 53) { part = "a quarter wanting of "; hr = (hr + 1) % 12; }
      else { part = ""; hr = (hr + 1) % 12; }
      const Hh = M >= 38 ? H + 1 : H;
      const when = Hh < 5 ? "in the night" : Hh < 12 ? "in the morning" : Hh < 17 ? "after noone" : Hh < 20 ? "at evening" : "at night";
      return `${part}${NUMW[hr]} of the clock ${when}`;
    },
    moon(d) { // 0 new … 0.5 full
      const ref = new Date("2025-10-22T08:00:00Z").getTime(); // canon: new moon Wed 22 Oct (world.md § 6)
      const syn = 29.530588 * 864e5;
      return (((d.getTime() - ref) % syn) + syn) % syn / syn;
    },
    iso(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; },
    MONTH, WEEKDAY
  };

  /* ---------- glyphs (currentColor line art, 48 grid) ---------- */
  const G = {
    papers: '<path d="M38 5c-9 3-17 11-21 21l-4 10 3 1 4-9c6-1 11-5 13-10-3 1-6 1-8 1 4-2 8-6 10-11z"/><path d="M12 37l-3 7"/><path d="M8 44h20" />',
    wheel: '<circle cx="24" cy="24" r="17"/><circle cx="24" cy="24" r="3"/><path d="M24 7v34M7 24h34M12 12l24 24M36 12L12 36"/><rect x="19" y="3" width="10" height="5"/><rect x="19" y="40" width="10" height="5"/>',
    letters: '<rect x="6" y="12" width="36" height="24"/><path d="M6 12l18 14 18-14"/><circle cx="24" cy="30" r="5"/>',
    accounts: '<path d="M24 6v34M10 14h28M14 40h20"/><path d="M10 14l-5 12h10zM38 14l-5 12h10z"/><path d="M5 26a5 3 0 0010 0M33 26a5 3 0 0010 0"/>',
    almanac: '<circle cx="18" cy="20" r="8"/><path d="M18 6v3M18 31v3M4 20h3M29 20h3M8 10l2 2M26 28l2 2M8 30l2-2M26 12l2-2"/><path d="M38 26a9 9 0 11-9 14 7 7 0 009-14z"/>',
    commonplace: '<path d="M24 12c-6-4-12-4-18-3v28c6-1 12-1 18 3 6-4 12-4 18-3V9c-6-1-12-1-18 3z"/><path d="M24 12v28"/><path d="M10 16h9M10 21h9M10 26h7M29 16h9M29 21h9"/>',
    glass: '<ellipse cx="24" cy="20" rx="12" ry="15"/><ellipse cx="24" cy="20" rx="8" ry="11"/><path d="M24 35v9M18 44h12"/><path d="M19 15c2-2 6-3 8-1"/>',
    coffer: '<path d="M6 20h36v20H6z"/><path d="M6 20c0-8 8-12 18-12s18 4 18 12"/><path d="M6 28h36"/><rect x="13" y="25" width="5" height="7"/><rect x="30" y="25" width="5" height="7"/>'
  };
  const glyph = (id, cls = "glyph") => `<svg class="${cls}" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${G[id]}</svg>`;

  /* ---------- tiny event bus for models ---------- */
  const bus = { subs: {}, on(ev, fn) { (this.subs[ev] ||= []).push(fn); }, emit(ev, x) { (this.subs[ev] || []).forEach(f => f(x)); } };

  /* ---------- models ---------- */
  const letters = {
    state() { return store.get("letters", { added: {}, unread: D.scene ? {} : { heminges: true }, delivered: {} }); },
    save(s) { store.set("letters", s); bus.emit("letters"); },
    thread(id) {
      const t = D.threads.find(x => x.id === id), s = letters.state();
      return { ...t, letters: [...t.letters, ...(s.added[id] || [])] };
    },
    add(id, letter) { const s = letters.state(); (s.added[id] ||= []).push(letter); letters.save(s); },
    setLast(id, patch) { const s = letters.state(); const a = s.added[id]; if (a && a.length) Object.assign(a[a.length - 1], patch); letters.save(s); },
    unread(id, v) { const s = letters.state(); s.unread[id] = v; letters.save(s); },
    unreadCount() { const s = letters.state(); return Object.values(s.unread).filter(Boolean).length; }
  };
  const ledger = {
    rows() { return store.get("ledger", D.ledger); },
    save(r) { store.set("ledger", r); bus.emit("ledger"); },
    totals(r = ledger.rows()) {
      const t = { exp: 0, rec: 0, paid: 0, count: 0 };
      r.forEach(x => { if (x.note === "count") t.count += x.rec || 0; else { t.exp += x.exp || 0; t.rec += x.rec || 0; t.paid += x.paid || 0; } });
      t.hand = t.count + t.rec - t.paid;
      t.owed = r.filter(x => x.note !== "count").reduce((a, x) => a + Math.max(0, (x.exp || 0) - (x.rec || 0)), 0);
      return t;
    }
  };

  /* ---------- apps ---------- */
  const APPS = {};

  APPS.papers = {
    id: "papers", title: "Foul Papers", sub: "the drafts on the board", size: [620, 520],
    render(body, ctx, arg) {
      let cur = arg || store.get("papers:cur", "romeo-4-3");
      const list = h("ul", { class: "sheet-list" });
      const page = h("div", { class: "page", contenteditable: "true", spellcheck: "false" });
      const label = h("div", { class: "page-label" });
      const status = h("div", { class: "status" });
      const tools = h("div", { class: "tools" },
        tool("Italick", "names and directions", () => document.execCommand("italic")),
        tool("Strike", "strike through and write above", () => document.execCommand("strikeThrough")),
        tool("✠", "a cross in the margin, to return", () => document.execCommand("insertHTML", false, '<span class="cross">✠</span>')),
        tool("Speaker", "a speech prefix", () => { const p = prompt("Speech prefix", "Iul."); if (p) document.execCommand("insertHTML", false, `<span class="sp">${p}</span>&nbsp;`); }),
        tool("Blot", "undo", () => document.execCommand("undo")),
        h("span", { class: "spacer" }),
        tool("Sand it", "dry the ink (save)", () => save(true))
      );
      function tool(t, title, fn) { return h("button", { class: "tool", title, onmousedown: e => e.preventDefault(), onclick: fn }, t); }
      const sheets = () => D.sheets.filter(s => !s.locked || store.get("coffer:open", false));
      function drawList() {
        list.replaceChildren(...sheets().map(s => h("li", { class: s.id === cur ? "on" : "", onclick: () => select(s.id) },
          h("b", {}, s.title), s.meta ? h("small", {}, s.meta) : null)));
      }
      let dirty = false, tmr;
      function select(id) {
        if (dirty) save(false);
        cur = id; store.set("papers:cur", id);
        const s = D.sheets.find(x => x.id === id) || D.sheets[0];
        page.innerHTML = store.get("sheet:" + s.id, s.html);
        drawList(); stat("dry");
        ctx.win.setTitle && ctx.win.setTitle(s.title);
      }
      function words() { return (page.innerText.match(/[A-Za-z']+/g) || []); }
      function stat(state) {
        const w = words(), lines = page.innerText.split(/\n/).filter(x => x.trim()).length;
        status.innerHTML = `<span>${roman(lines)} lines · ${w.length} words</span><span class="ink ink-${state}">${state === "wet" ? "the ink is wet" : state === "sanding" ? "sanding…" : "dry"}</span><span class="catch" title="catchword">${(w[w.length - 1] || "").toLowerCase()}</span>`;
      }
      function save(manual) {
        const s = D.sheets.find(x => x.id === cur);
        store.set("sheet:" + s.id, page.innerHTML); dirty = false;
        if (manual) { stat("sanding"); setTimeout(() => stat("dry"), 900); } else stat("dry");
      }
      page.addEventListener("input", () => { dirty = true; stat("wet"); clearTimeout(tmr); tmr = setTimeout(() => save(false), 2500); });
      body.append(h("div", { class: "app app-papers" }, h("aside", { class: "sheets" }, h("div", { class: "aside-head" }, "On the board"), list),
        h("section", { class: "sheet-wrap" }, tools, h("div", { class: "page-scroll" }, page), status)));
      bus.on("coffer", drawList);
      select(cur);
      return { onArg: id => select(id) };
    }
  };

  APPS.wheel = {
    id: "wheel", title: "Bookwheel", sub: "the stalls and the town", size: [680, 540],
    render(body, ctx, arg) {
      let tabs = [{ hist: [arg || "pauls"], i: 0 }], ti = 0;
      const tabBar = h("div", { class: "wheel-tabs" });
      const addr = h("input", { class: "addr", spellcheck: "false", title: "the signe you would go to" });
      const view = h("div", { class: "wheel-page" });
      const back = h("button", { class: "nav", title: "back", onclick: () => go(-1) }, "◂");
      const fwd = h("button", { class: "nav", title: "forward", onclick: () => go(1) }, "▸");
      const home = h("button", { class: "nav", title: "to Paul's", onclick: () => nav("pauls") }, "☩");
      addr.addEventListener("keydown", e => { if (e.key === "Enter") { const q = addr.value.toLowerCase().replace(/^at the signe of /, ""); const key = Object.keys(D.pages).find(k => k.includes(q) || D.pages[k].sign.toLowerCase().includes(q) || D.pages[k].title.toLowerCase().includes(q)); nav(key || "?" + addr.value); } });
      const T = () => tabs[ti];
      function nav(id) { const t = T(); t.hist = t.hist.slice(0, t.i + 1); t.hist.push(id); t.i++; draw(); }
      function go(d) { const t = T(); t.i = Math.max(0, Math.min(t.hist.length - 1, t.i + d)); draw(); }
      function drawTabs() {
        tabBar.replaceChildren(...tabs.map((t, i) => {
          const p = D.pages[t.hist[t.i]];
          return h("div", { class: "wtab" + (i === ti ? " on" : ""), onclick: () => { ti = i; draw(); } },
            h("span", {}, p ? p.title.replace(/^The /, "") : "No such signe"),
            tabs.length > 1 ? h("b", { title: "take the book off the wheel", onclick: e => { e.stopPropagation(); tabs.splice(i, 1); ti = Math.min(ti, tabs.length - 1); draw(); } }, "×") : null);
        }), h("button", { class: "wtab add", title: "set another book on the wheel", onclick: () => { tabs.push({ hist: ["pauls"], i: 0 }); ti = tabs.length - 1; draw(); } }, "+"));
        ctx.win.el.style.setProperty("--wheel-turn", (ti * 360 / Math.max(tabs.length, 1)) + "deg");
      }
      function draw() {
        const id = T().hist[T().i], p = D.pages[id];
        back.disabled = T().i === 0; fwd.disabled = T().i >= T().hist.length - 1;
        drawTabs();
        view.replaceChildren();
        if (!p) { addr.value = id.replace(/^\?/, ""); view.append(h("h2", {}, "No such signe in the City"), h("p", {}, `No stall hangs out "${id.replace(/^\?/, "")}". Try Paul's, the Greyhound, the bills, the Register, or Holinshed.`)); return; }
        addr.value = "At the signe of " + p.sign;
        view.append(h("h2", {}, p.title));
        if (p.search) {
          const q = h("input", { class: "reg-q", placeholder: "a word of the title, or a stationer" });
          const out = h("table", { class: "reg" });
          const run = () => { const v = q.value.toLowerCase(); out.replaceChildren(h("tr", {}, h("th", {}, "Entred"), h("th", {}, "To"), h("th", {}, "Title")), ...p.entries.filter(e => e.join(" ").toLowerCase().includes(v)).map(e => h("tr", {}, ...(e.length === 2 ? [e[0], "—", e[1]] : e).map(c => h("td", {}, c))))); };
          q.addEventListener("input", run); view.append(q); run(); view.append(out);
        }
        for (const b of p.body) {
          if (b[0] === "h") view.append(h("h3", {}, b[1]));
          if (b[0] === "p") view.append(h("p", {}, b[1]));
          if (b[0] === "note") view.append(h("p", { class: "marg" }, b[1]));
          if (b[0] === "link") view.append(h("a", { class: "stall", href: "#", onclick: e => { e.preventDefault(); nav(b[1]); } }, h("b", {}, b[2]), b[3] ? h("span", {}, b[3]) : null));
          if (b[0] === "title") view.append(h("div", { class: "titlepage" }, h("div", { class: "tp-t" }, b[1]), h("div", { class: "tp-m" }, b[2]), h("div", { class: "tp-orn" }, "❦"), h("div", { class: "tp-i" }, b[3])));
          if (b[0] === "bill1") view.append(h("div", { class: "bill-big" }, h("b", {}, b[1]), h("i", {}, b[2])));
          if (b[0] === "verse") view.append(h("p", { class: "verse" }, b[1]));
          if (b[0] === "bills") view.append(h("div", { class: "bills" }, ...b[1].map(x => h("div", { class: "bill" + (x[1] === "The Theatre" ? " ours" : "") }, h("small", {}, x[0] + " · " + x[1]), h("b", {}, x[2]), h("i", {}, "by " + x[3])))));
        }
        view.scrollTop = 0;
      }
      body.append(h("div", { class: "app app-wheel" }, h("div", { class: "wheel-bar" }, back, fwd, home, addr), tabBar, view));
      draw();
      return { onArg: id => nav(id) };
    }
  };

  APPS.letters = {
    id: "letters", title: "Letters", sub: "by carrier, by boy, by hand", size: [700, 540],
    render(body, ctx, arg) {
      let cur = (D.threads.find(t => t.id === arg) || D.threads.find(t => t.id === "anne") || D.threads[0] || {}).id;
      const list = h("ul", { class: "corr" });
      const view = h("div", { class: "thread" });
      const ta = h("textarea", { class: "compose", placeholder: "Write…", rows: 3 });
      const sendBtn = h("button", { class: "seal-btn", onclick: send }, "Seal and send");
      const via = h("div", { class: "via" });
      const extra = h("div", { class: "compose-extra" });
      function drawList() {
        const s = letters.state();
        list.replaceChildren(...D.threads.map(t => {
          const th = letters.thread(t.id), last = th.letters[th.letters.length - 1];
          return h("li", { class: (t.id === cur ? "on " : "") + (s.unread[t.id] ? "unread" : ""), onclick: () => select(t.id) },
            h("i", { class: "wax", style: `--wax:${t.seal}` }), h("b", {}, t.who), h("small", {}, t.where), h("em", {}, last ? (last.dir === "in" ? "" : "you: ") + last.body.slice(0, 48) + "…" : ""));
        }));
      }
      function viaText(t) {
        if (t.via === "carrier") { const nx = D.carrierDays.find(d => d >= time.iso(now())); return `By Hobbins the carrier from the Bell in Carter Lane, ${t.cost} the letter. He rides ${nx === time.iso(now()) ? "today" : nx ? "Thursday " + roman(+nx.slice(8)) + " " + time.MONTH[+nx.slice(5, 7) - 1] : "when he comes"}.`; }
        if (t.via === "boy") return `By Mrs Ansell's boy, ${t.cost}. He runs it within the hour.`;
        return t.id === "lord" ? "By your own hand, to the gate in Holborn." : "Left on the tiring-house peg.";
      }
      function select(id) {
        if (!D.threads.find(t => t.id === id)) { view.replaceChildren(h("p", { class: "empty" }, "No letters.")); return; }
        cur = id; letters.unread(id, false);
        const t = letters.thread(id);
        view.replaceChildren(h("div", { class: "thread-head" }, h("b", {}, t.who), h("span", {}, t.where)),
          ...t.letters.map(l => h("article", { class: "letter " + l.dir },
            h("header", {}, h("span", {}, l.dir === "in" ? "Received " + l.date : "Sent " + l.date), h("small", {}, l.via)),
            h("p", {}, l.body),
            l.dir === "out" ? h("footer", { class: "state" }, stateWord(l.state)) : null)));
        via.textContent = viaText(t);
        extra.replaceChildren();
        if (id === "anne") extra.append(h("button", { class: "small", onclick: () => { const tbl = D.sheets.find(s => s.id === "tables"); const tmp = h("div", { html: store.get("sheet:tables", tbl.html) }); ta.value = tmp.innerText.trim(); } }, "Copy from the tables"));
        const lastOut = [...t.letters].reverse().find(l => l.dir === "out");
        if (t.via === "carrier" && lastOut && lastOut.state === "waits at the Bell") extra.append(h("button", { class: "small hasten", onclick: () => hasten(id) }, "Let Thursday come"));
        view.scrollTop = view.scrollHeight;
        drawList();
      }
      function stateWord(s) { return s ? "· " + s : ""; }
      function send() {
        const body = ta.value.trim(); if (!body) return;
        const t = D.threads.find(x => x.id === cur);
        const st = t.via === "carrier" ? "waits at the Bell" : t.id === "lord" ? "left at the gate · no answer" : t.via === "boy" ? "with the boy" : "left on the peg";
        letters.add(cur, { dir: "out", date: time.shortDate(), via: t.via === "carrier" ? "Hobbins, from the Bell" : t.via === "boy" ? "by the boy" : "by hand", body, state: st });
        ta.value = ""; select(cur);
        if (t.via === "boy") {
          const id = cur;
          setTimeout(() => { letters.setLast(id, { state: "delivered" }); if (cur === id) select(id); }, 2200);
          const rs = t.replies || []; const s = letters.state(); const n = (s.added[id] || []).filter(l => l.dir === "in").length;
          if (rs.length) setTimeout(() => { letters.add(id, { dir: "in", date: time.shortDate(), via: "by the boy", body: rs[n % rs.length] }); if (cur === id) select(id); else letters.unread(id, true); ctx.os.notify({ title: "A boy at the door", body: `A note from ${t.who}.`, app: "letters", arg: id }); }, 6500);
        }
        if (t.via === "hand" && t.id !== "lord" && (t.replies || []).length) setTimeout(() => { letters.add(t.id, { dir: "in", date: time.shortDate(), via: "on the peg", body: t.replies[0] }); letters.unread(t.id, true); ctx.os.notify({ title: "On the tiring-house peg", body: `Something from ${t.who}.`, app: "letters", arg: t.id }); }, 9000);
      }
      function hasten(id) {
        letters.setLast(id, { state: "with Hobbins on the Oxford road" }); select(id);
        setTimeout(() => { letters.setLast(id, { state: "delivered at Henley Street" }); if (cur === id) select(id); }, 2600);
        const t = D.threads.find(x => x.id === id);
        const s = letters.state();
        if (t.reply && !(s.added[id] || []).some(l => l.dir === "in")) setTimeout(() => {
          letters.add(id, { dir: "in", ...t.reply }); if (cur === id) select(id); else letters.unread(id, true);
          ctx.os.notify({ title: "Carrier in at the Bell", body: "Hobbins has a letter from Stratford.", app: "letters", arg: id });
        }, 5200);
      }
      body.append(h("div", { class: "app app-letters" }, h("aside", { class: "corr-wrap" }, h("div", { class: "aside-head" }, "Correspondents"), list),
        h("section", { class: "thread-wrap" }, view, h("div", { class: "compose-wrap" }, ta, h("div", { class: "compose-row" }, via, extra, sendBtn)))));
      bus.on("letters", drawList);
      select(cur);
      return { onArg: id => select(id) };
    }
  };

  APPS.accounts = {
    id: "accounts", title: "Account Book", sub: "Item, and Item", size: [720, 500],
    render(body, ctx) {
      let useRoman = store.get("accounts:roman", true);
      const table = h("table", { class: "ledger" });
      const foot = h("div", { class: "ledger-foot" });
      const toggle = h("button", { class: "small", onclick: () => { useRoman = !useRoman; store.set("accounts:roman", useRoman); draw(); } });
      const add = h("button", { class: "small", onclick: () => { const r = ledger.rows(); r.push({ date: time.shortDate(), item: "Item ", paid: null }); ledger.save(r); draw(); const cells = table.querySelectorAll("td.item"); cells[cells.length - 1].focus(); } }, "Add an Item");
      function cell(r, i, key) {
        const isAmt = ["exp", "rec", "paid"].includes(key);
        const td = h("td", { class: key + (isAmt ? " amt" : ""), contenteditable: "true", spellcheck: "false" }, isAmt ? lsd.fmt(r[key], useRoman) : r[key] || "");
        td.addEventListener("focus", () => { if (isAmt) td.textContent = r[key] == null ? "" : lsd.fmt(r[key], useRoman); });
        td.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); td.blur(); } });
        td.addEventListener("blur", () => {
          const rows = ledger.rows(); const v = td.textContent.trim();
          if (isAmt) { const p = lsd.parse(v); rows[i][key] = p; td.classList.toggle("bad", v !== "" && p == null); }
          else rows[i][key] = v;
          ledger.save(rows); drawFoot(); if (isAmt && lsd.parse(v) != null) td.textContent = lsd.fmt(rows[i][key], useRoman);
        });
        return td;
      }
      function draw() {
        toggle.textContent = useRoman ? "In figures" : "In the old numbers";
        const rows = ledger.rows();
        table.replaceChildren(h("tr", {}, h("th", {}, "Day"), h("th", {}, "Item"), h("th", {}, "Expected"), h("th", {}, "Received"), h("th", {}, "Laid out")),
          ...rows.map((r, i) => h("tr", { class: r.note === "count" ? "count" : r.note === "expected" ? "expected" : "" }, cell(r, i, "date"), cell(r, i, "item"), cell(r, i, "exp"), cell(r, i, "rec"), cell(r, i, "paid"))));
        drawFoot();
      }
      function drawFoot() {
        const t = ledger.totals();
        foot.replaceChildren(
          h("div", {}, h("span", {}, "Received this weeke"), h("b", {}, lsd.fmt(t.rec, useRoman) || "nil")),
          h("div", {}, h("span", {}, "Laid out"), h("b", {}, lsd.fmt(t.paid, useRoman) || "nil")),
          h("div", { class: "owed", title: "expected money has a way of eating dinner" }, h("span", {}, "Expected and not come"), h("b", {}, lsd.fmt(t.owed, useRoman) || "nil")),
          h("div", { class: "hand" }, h("span", {}, "In the coffer, by this reckoning"), h("b", {}, lsd.fmt(t.hand, useRoman))));
      }
      if (D.scene) foot.hidden = true; // a staged moment shows his lines, not totals we would have to invent
      body.append(h("div", { class: "app app-accounts" }, h("div", { class: "ledger-bar" }, h("span", { class: "ledger-title" }, D.ledgerTitle || "The weeke of S. Luke, 1595"), h("span", { class: "spacer" }), add, toggle),
        h("div", { class: "ledger-scroll" }, table), foot));
      draw();
    }
  };

  APPS.almanac = {
    id: "almanac", title: "Almanack", sub: "the penny almanack, with his marks", size: [700, 520],
    render(body, ctx) {
      const today = time.iso(now());
      let ym = [now().getFullYear(), now().getMonth()], sel = today;
      const grid = h("div", { class: "alm-grid" });
      const head = h("div", { class: "alm-head" });
      const side = h("aside", { class: "alm-day" });
      const notes = () => store.get("almanac:notes", {});
      function phaseGlyph(p) { const q = 0.5 / 29.53; for (const [c, g] of [[0, "●"], [1, "●"], [0.25, "◐"], [0.5, "○"], [0.75, "◑"]]) if (Math.abs(p - c) <= q) return g; return ""; }
      function draw() {
        const [y, m] = ym, first = new Date(y, m, 1), days = new Date(y, m + 1, 0).getDate();
        const sign = { 8: "the Sunne in Libra", 9: "the Sunne in Scorpio from the xiij", 10: "the Sunne in Sagittarius from the xij", 11: "the Sunne in Capricorne from the xij" }[m] || "";
        head.replaceChildren(h("button", { class: "nav", onclick: () => { ym = m === 0 ? [y - 1, 11] : [y, m - 1]; draw(); } }, "◂"),
          h("div", { class: "alm-title" }, h("b", {}, time.MONTH[m]), h("span", {}, `MDXCV · hath ${roman(days)} dayes · ${sign}`)),
          h("button", { class: "nav", onclick: () => { ym = m === 11 ? [y + 1, 0] : [y, m + 1]; draw(); } }, "▸"));
        const cells = ["S", "M", "T", "W", "T", "F", "S"].map(d => h("div", { class: "dow" }, d));
        for (let i = 0; i < first.getDay(); i++) cells.push(h("div", { class: "blank" }));
        for (let d = 1; d <= days; d++) {
          const dt = new Date(y, m, d, 12), iso = time.iso(dt), ev = ((D.marks || {})[iso] || []).concat(D.almanac[iso] || [], notes()[iso] || []);
          const carrier = D.carrierDays.includes(iso);
          cells.push(h("div", { class: "day" + (iso === today ? " today" : "") + (iso === sel ? " sel" : "") + (dt.getDay() === 0 ? " sun" : "") + (ev.length ? " has" : ""), onclick: () => { sel = iso; draw(); } },
            h("span", { class: "n" }, roman(d)), h("span", { class: "moon" }, phaseGlyph(time.moon(dt))), carrier ? h("span", { class: "car", title: "carrier in" }, "♞") : null,
            h("span", { class: "ev" }, ev[0] || "")));
        }
        grid.replaceChildren(...cells);
        drawSide();
      }
      function drawSide() {
        const dt = new Date(sel + "T12:00"), i = dt.getDate() + dt.getMonth() * 3;
        const ev = D.almanac[sel] || [], mine = ((D.marks || {})[sel] || []).concat(notes()[sel] || []);
        const inp = h("input", { placeholder: "Make a marke…" });
        inp.addEventListener("keydown", e => { if (e.key === "Enter" && inp.value.trim()) { const n = notes(); (n[sel] ||= []).push(inp.value.trim()); store.set("almanac:notes", n); draw(); } });
        side.replaceChildren(h("h3", {}, time.dateWords(dt)),
          h("div", { class: "prog" }, h("span", {}, D.weather[i % D.weather.length]), h("span", {}, D.physick[(i * 5) % D.physick.length])),
          h("ul", {}, ...ev.map(e => h("li", {}, e)), ...mine.map(e => h("li", { class: "mine" }, e))),
          inp);
      }
      body.append(h("div", { class: "app app-almanac" }, h("section", { class: "alm-main" }, head, grid), side));
      draw();
    }
  };

  APPS.commonplace = {
    id: "commonplace", title: "Commonplace Book", sub: "Of Kings · Of Love · Of Time · Words · Faces · Prices", size: [600, 500],
    render(body) {
      const heads = ["Of Kings", "Of Love", "Of Time", "Words", "Faces", "Prices"];
      let cur = (D.scene && D.scene.cpHead) || "Of Kings", q = "";
      const nav = h("nav", { class: "cp-heads" }), list = h("div", { class: "cp-list" });
      const search = h("input", { class: "cp-q", placeholder: "Seek a word…" });
      const txt = h("textarea", { rows: 2, placeholder: "Copy it out…" }), src = h("input", { placeholder: "whence" });
      const items = () => store.get("commonplace", D.commonplace);
      search.addEventListener("input", () => { q = search.value.toLowerCase(); draw(); });
      function draw() {
        nav.replaceChildren(...heads.map(x => h("button", { class: x === cur && !q ? "on" : "", onclick: () => { cur = x; q = ""; search.value = ""; draw(); } }, x)));
        const all = items().filter(i => i.text && (q ? (i.text + i.src).toLowerCase().includes(q) : i.head === cur));
        list.replaceChildren(h("h2", {}, q ? `“${q}”` : cur), ...(all.length ? all.map(i => h("blockquote", {}, h("p", {}, i.text), i.src ? h("cite", {}, i.src) : null, q ? h("small", {}, i.head) : null)) : [h("p", { class: "empty" }, "Nothing written under this heading yet.")]));
      }
      const add = h("button", { class: "small", onclick: () => { if (!txt.value.trim()) return; const it = items(); it.push({ head: cur, text: txt.value.trim(), src: src.value.trim() }); store.set("commonplace", it); txt.value = src.value = ""; draw(); } }, "Enter it");
      body.append(h("div", { class: "app app-commonplace" }, h("div", { class: "cp-top" }, nav, search), list, h("div", { class: "cp-add" }, txt, h("div", { class: "cp-row" }, src, add))));
      draw();
    }
  };

  APPS.coffer = {
    id: "coffer", title: "Coffer", sub: "oak, with two locks", size: [600, 460],
    render(body, ctx) {
      let cur = null;
      const left = h("div", { class: "bundles" }), right = h("div", { class: "bundle-view" });
      const keys = store.get("coffer:keys", [false, false]);
      const B = [
        { id: "richard", name: "The king", sub: "Richard the second, working copy", tie: "tape" },
        { id: "romeo", name: "Romeo", sub: "the faire bundle, red thred", tie: "red" },
        { id: "verse", name: "Single leaves", sub: "no title, no name", tie: "locked" },
        { id: "household", name: "Household", sub: "letters, and the tables", tie: "string" },
        { id: "money", name: "Money", sub: "the bottom of the coffer", tie: "bag" }
      ];
      function draw() {
        const open = store.get("coffer:open", false);
        left.replaceChildren(...B.map(b => h("button", { class: "bundle tie-" + b.tie + (cur === b.id ? " on" : "") + (b.tie === "locked" && !open ? " shut" : ""), onclick: () => { cur = b.id; draw(); } }, h("b", {}, b.name), h("small", {}, b.sub))));
        right.replaceChildren();
        if (!cur) { right.append(h("p", { class: "empty" }, "Lift a bundle.")); return; }
        const b = B.find(x => x.id === cur);
        right.append(h("h3", {}, b.name));
        if (b.id === "verse" && !open) {
          right.append(h("p", {}, "This lies under the money, and both locks hold it."),
            h("div", { class: "locks" }, ...[0, 1].map(k => h("button", { class: "key" + (keys[k] ? " turned" : ""), onclick: () => { keys[k] = !keys[k]; store.set("coffer:keys", keys); if (keys[0] && keys[1]) { store.set("coffer:open", true); bus.emit("coffer"); } draw(); } }, keys[k] ? "turned" : k ? "the second key" : "the first key"))));
          return;
        }
        if (b.id === "money") { const t = ledger.totals(); right.append(h("p", { class: "coin" }, lsd.fmt(t.hand, true)), h("p", {}, "By the account book's reckoning. Told last on S. Luke's day."), h("button", { class: "small", onclick: () => ctx.os.open("accounts") }, "Open the account book")); return; }
        const sheets = D.sheets.filter(s => s.bundle === b.id);
        const ths = b.id === "household" ? D.threads.filter(t => t.id === "anne") : [];
        right.append(h("ul", { class: "contents" },
          ...sheets.map(s => h("li", { onclick: () => ctx.os.open("papers", s.id) }, h("b", {}, s.title), h("small", {}, s.label))),
          ...ths.map(t => h("li", { onclick: () => ctx.os.open("letters", t.id) }, h("b", {}, "Letters from " + t.who), h("small", {}, letters.thread(t.id).letters.length + " kept")))));
        if (b.id === "verse") right.append(h("button", { class: "small", onclick: () => { store.set("coffer:open", false); store.set("coffer:keys", [false, false]); keys[0] = keys[1] = false; bus.emit("coffer"); draw(); } }, "Lock it againe"));
      }
      body.append(h("div", { class: "app app-coffer" }, left, right));
      draw();
    }
  };


  APPS.glass = {
    id: "glass", title: "The Glass", sub: "faces at a distance", size: [800, 560],
    render(body, ctx) {
      const J = window.JOURNAL || { people: {}, roster: [], calls: [] };
      const P = id => J.people[id] || { name: id, face: null };
      const roster = J.roster.filter(id => P(id).face);
      const nowIso = () => time.iso(now());
      const lastCall = id => [...J.calls].reverse().find(c => c.with.includes(id) && c.day <= nowIso());
      let sel = roster[0], live = null, muted = false, veiled = false, tick = null;
      const list = h("ul", { class: "faces" }), stage = h("section", { class: "glass-stage" });
      const spoke = id => { const c = lastCall(id); if (!c) return ""; const d = new Date(c.day + "T12:00"); return `spoke ${time.WEEKDAY[d.getDay()].slice(0, 3)} ${roman(d.getDate())} ${time.MONTH[d.getMonth()].slice(0, 3)}`; };
      function drawList() {
        list.replaceChildren(...roster.map(id => h("li", { class: (id === sel ? "on " : "") + (live && live.with.includes(id) ? "live" : ""), onclick: () => { sel = id; if (!live) drawStage(); drawList(); } },
          h("img", { src: P(id).face, alt: "" }), h("b", {}, P(id).name), h("small", {}, live && live.with.includes(id) ? "in the glass" : spoke(id)))));
      }
      function self() {
        return h("div", { class: "tile self" + (veiled ? " veiled" : "") + (live && live.speaking === "william_shakespeare" ? " speaking" : "") },
          h("div", { class: "oval" }, h("div", { class: "room" })), h("span", { class: "plate" }, "W. S." + (muted ? " · silent" : "")));
      }
      function drawStage() {
        clearInterval(tick); stage.replaceChildren();
        if (!live) {
          const p = P(sel);
          stage.append(h("div", { class: "glass-idle" },
            h("div", { class: "oval big" }, h("img", { src: p.face, alt: "" })),
            h("b", {}, p.name), h("small", {}, spoke(sel) || "never yet in the glass"),
            h("button", { class: "summon", onclick: () => summon([sel]) }, "Summon")));
          return;
        }
        const tiles = h("div", { class: "tiles n" + (live.with.length + 1) },
          ...live.with.map(id => h("div", { class: "tile" + (live.speaking === id ? " speaking" : "") + (live.ringing ? " ringing" : "") },
            h("div", { class: "oval" }, h("img", { src: P(id).face, alt: "" })), h("span", { class: "plate" }, P(id).name))), self());
        const line = live.lines[live.i];
        const words = h("div", { class: "words" }, line && !live.ringing ? [h("b", {}, (line.who === "william_shakespeare" ? "W. S." : P(line.who).name.split(" ").pop()) + "  "), line.text] : live.ringing ? `Summoning ${live.with.map(id => P(id).name).join(" and ")}…` : "");
        const mins = Math.max(1, Math.round((now() - live.since) / 60000));
        const bar = h("div", { class: "glass-bar" },
          h("span", { class: "dur" }, live.ringing ? "" : `${roman(mins)} minute${mins > 1 ? "s" : ""}`),
          h("button", { onclick: () => { muted = !muted; drawStage(); } }, muted ? "Speak" : "Hold thy tongue"),
          h("button", { onclick: () => { veiled = !veiled; drawStage(); } }, veiled ? "Unveil my glass" : "Veil my glass"),
          h("button", { class: "leave", onclick: () => { live = null; drawStage(); drawList(); bus.emit("glass"); } }, "Take leave"));
        stage.append(tiles, words, bar);
        if (live.lines.length && !live.ringing && !live.staged) tick = setInterval(() => { live.i = Math.min(live.lines.length - 1, live.i + 1); live.speaking = live.lines[live.i].who; drawStage(); }, 4200);
      }
      function summon(ids) {
        live = { with: ids, lines: [], i: 0, ringing: true, since: now(), speaking: null };
        drawStage(); drawList(); bus.emit("glass");
        setTimeout(() => { if (!live) return; live.ringing = false; live.since = now(); live.speaking = ids[0]; drawStage(); bus.emit("glass"); }, 2600);
      }
      // a staged call from the journal: in the glass already, at the line being spoken
      const sc = D.scene && D.scene.call;
      if (sc) {
        const t = time.now(), hhmm = `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}:${String(t.getSeconds()).padStart(2, "0")}`;
        let i = 0; sc.lines.forEach((l, k) => { if (l.at <= hhmm) i = k; });
        live = { with: sc.with, lines: sc.lines, i, ringing: false, staged: true, since: new Date(`${sc.day}T${sc.t}:00`), speaking: sc.lines[i] && sc.lines[i].who };
        sel = sc.with[0];
      }
      os1595glass.state = () => live && !live.ringing ? "in the glass: " + live.with.map(id => P(id).name.split(" ").pop()).join(", ") : live ? "summoning…" : (() => { const c = [...J.calls].reverse().find(c => c.day <= nowIso()); return c && c.with[0] ? P(c.with[0]).name.split(" ").pop() + ", " + spoke(c.with[0]).replace("spoke ", "") : ""; })();
      body.append(h("div", { class: "app app-glass" }, h("aside", {}, h("div", { class: "aside-head" }, "Faces"), list), stage));
      drawList(); drawStage();
    }
  };
  const os1595glass = { state: () => "" };

  const ORDER = ["papers", "wheel", "letters", "accounts", "almanac", "commonplace", "coffer", "glass"];

  /* ---------- window manager ---------- */
  function createOS(env) {
    const root = env.root;
    let z = 20, seq = 0;
    const wins = new Map();
    const os = { apps: APPS, order: ORDER, glyph, time, store, lsd, roman, bus, letters, ledger, h, wins, open, close, focus, minimize, restore, toggleMax, notify, active: null };

    function rootRect() { return root.getBoundingClientRect(); }
    function defaultPlace(app, n) {
      const R = rootRect(), [w, hgt] = app.size;
      const W = Math.min(w, R.width - 40), H = Math.min(hgt, R.height - 40);
      return { x: Math.max(10, Math.min(R.width - W - 10, 60 + n * 34)), y: Math.max(10, Math.min(R.height - H - 10, 30 + n * 28)), w: W, h: H };
    }
    function open(appId, arg) {
      const ex = [...wins.values()].find(w => w.app.id === appId);
      if (ex) { restore(ex); if (arg && ex.api.onArg) ex.api.onArg(arg); return ex; }
      const app = APPS[appId];
      const w = { id: "w" + (++seq), app, minimized: false, max: false };
      w.setTitle = t => { w.subtitle = t; const s = w.el.querySelector("[data-subtitle]"); if (s) s.textContent = t; };
      const f = env.frame(w, os);
      w.el = f.el; w.body = f.body;
      w.el.classList.add("win"); w.el.dataset.app = appId;
      const r = (env.place && env.place(app, wins.size, rootRect())) || defaultPlace(app, wins.size);
      Object.assign(w.el.style, { left: r.x + "px", top: r.y + "px", width: r.w + "px", height: r.h + "px" });
      root.appendChild(w.el);
      wins.set(w.id, w);
      wire(w);
      w.api = app.render(w.body, { os, win: w, env }, arg) || {};
      focus(w);
      env.opened && env.opened(w);
      changed();
      return w;
    }
    function wire(w) {
      const el = w.el;
      el.addEventListener("pointerdown", () => focus(w), true);
      el.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", e => { e.stopPropagation(); close(w); }));
      el.querySelectorAll("[data-min]").forEach(b => b.addEventListener("click", e => { e.stopPropagation(); minimize(w); }));
      el.querySelectorAll("[data-max]").forEach(b => b.addEventListener("click", e => { e.stopPropagation(); toggleMax(w); }));
      el.querySelectorAll("[data-drag]").forEach(bar => {
        bar.addEventListener("dblclick", e => { if (!e.target.closest("button")) toggleMax(w); });
        bar.addEventListener("pointerdown", e => {
          if (e.button !== 0 || e.target.closest("button,input,textarea,[contenteditable]")) return;
          if (w.max) return;
          e.preventDefault();
          const R = rootRect(), sx = e.clientX, sy = e.clientY, ox = el.offsetLeft, oy = el.offsetTop;
          el.classList.add("dragging");
          const mv = ev => {
            const x = Math.max(-el.offsetWidth + 80, Math.min(R.width - 80, ox + ev.clientX - sx));
            const y = Math.max(0, Math.min(R.height - 40, oy + ev.clientY - sy));
            el.style.left = x + "px"; el.style.top = y + "px";
          };
          const up = () => { el.classList.remove("dragging"); window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
          window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
        });
      });
      el.querySelectorAll("[data-resize]").forEach(gr => gr.addEventListener("pointerdown", e => {
        e.preventDefault(); e.stopPropagation();
        const sx = e.clientX, sy = e.clientY, ow = el.offsetWidth, oh = el.offsetHeight;
        const mv = ev => { el.style.width = Math.max(360, ow + ev.clientX - sx) + "px"; el.style.height = Math.max(260, oh + ev.clientY - sy) + "px"; };
        const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
        window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
      }));
    }
    function focus(w) {
      if (os.active === w) return;
      wins.forEach(x => x.el.classList.toggle("active", x === w));
      w.el.style.zIndex = ++z; os.active = w; changed();
    }
    function close(w) {
      const done = () => { w.el.remove(); wins.delete(w.id); if (os.active === w) { os.active = null; const top = [...wins.values()].filter(x => !x.minimized).sort((a, b) => b.el.style.zIndex - a.el.style.zIndex)[0]; if (top) focus(top); } changed(); };
      if (env.closing) env.closing(w, done); else done();
    }
    function minimize(w) {
      if (w.minimized) return;
      w.minimized = true; if (os.active === w) os.active = null;
      const done = () => { w.el.classList.add("minimized"); changed(); };
      if (env.minimizing) env.minimizing(w, done); else done();
    }
    function restore(w) { const was = w.minimized; w.minimized = false; w.el.classList.remove("minimized"); focus(w); changed(); if (was && env.restoring) env.restoring(w); }
    function toggleMax(w) {
      if (!w.max) { w.prev = { l: w.el.style.left, t: w.el.style.top, w: w.el.style.width, h: w.el.style.height }; const R = (env.maxRect && env.maxRect(rootRect())) || { x: 0, y: 0, w: rootRect().width, h: rootRect().height }; Object.assign(w.el.style, { left: R.x + "px", top: R.y + "px", width: R.w + "px", height: R.h + "px" }); }
      else Object.assign(w.el.style, { left: w.prev.l, top: w.prev.t, width: w.prev.w, height: w.prev.h });
      w.max = !w.max; w.el.classList.toggle("max", w.max);
    }
    function changed() { env.onChange && env.onChange([...wins.values()], os); }
    function notify(n) {
      if (env.notice) return env.notice(n, os);
      const t = h("div", { class: "notice", onclick: () => { if (n.app) open(n.app, n.arg); t.remove(); } }, h("b", {}, n.title), h("span", {}, n.body));
      document.body.append(t); setTimeout(() => t.classList.add("out"), 6000); setTimeout(() => t.remove(), 7000);
    }
    // scene staging
    os.boot = (defaults = []) => {
      const sc = D.scene;
      const list = sc ? sc.open : params.get("open") ? params.get("open").split(",") : defaults;
      list.filter(a => APPS[a.split(":")[0]]).forEach(a => { const [id, arg] = a.split(":"); open(id, arg); });
      if (sc && sc.after) setTimeout(() => sc.after(os), 50);
      const f = (D.scene && D.scene.focus) || params.get("focus"); if (f) { const w = [...wins.values()].find(x => x.app.id === f); if (w) focus(w); }
      if (!params.get("quiet") && !D.scene) setTimeout(() => {
        const s = letters.state();
        if (!(s.added.burbage || []).some(l => l.ambient)) {
          letters.add("burbage", { dir: "in", date: time.shortDate(), via: "by the boy", body: "Thou hast a candle burning past nine and the whole lane can see it. Is it the girl and her vial? Bring it Friday. Dick.", ambient: true });
          letters.unread("burbage", true);
          notify({ title: "A boy at the door", body: "A note from Richard Burbage.", app: "letters", arg: "burbage" });
        }
      }, 24000);
    };
    os.reset = () => { store.reset(); location.reload(); };
    return os;
  }

  window.OS1595 = { createOS, APPS, ORDER, glyph, time, store, lsd, roman, h, bus, letters, ledger, glassState: () => os1595glass.state() };
})();
