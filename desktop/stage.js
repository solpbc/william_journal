/* stage.js — assemble one moment of William's year from the journal feed (feed.js).
   Tooling only: it reads ?frame=<YYYY-MM-DD>/<segment> or ?call=<YYYY-MM-DD>/<segment>
   and sets what is on each surface at that moment. It adds nothing to the screen itself.
   Load after data.js and feed.js, before core.js. */
(function () {
  const D = window.W1595, J = window.JOURNAL, q = new URLSearchParams(location.search);
  const fr = q.get("frame"), cl = q.get("call");
  if (!J || (!fr && !cl)) return;
  let cur = null, call = null, at;
  if (fr) {
    const [day, seg] = fr.split("/"); cur = J.frames.find(f => f.day === day && f.seg === seg);
    if (!cur) return; at = `${day}T${cur.t}`;
  } else {
    const [day, seg] = cl.split("/"); call = J.calls.find(c => c.day === day && c.seg === seg);
    if (!call) return; const ln = call.lines[Math.min(5, call.lines.length - 1)]; at = `${day}T${(ln && ln.at || call.t).slice(0, 5)}`;
  }
  const day = at.slice(0, 10);
  if (cur && cur.surface === "glass" && !call) { // a frame of the glass shows the call he was on then
    const m = t => +t.slice(0, 2) * 60 + +t.slice(3, 5);
    call = J.calls.filter(c => c.day === day && m(c.t) <= m(cur.t) + 5 && m(cur.t) - m(c.t) <= 40).pop() || null;
  }
  const upto = J.frames.filter(f => `${f.day}T${f.t}` <= at);
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const ROMAN = n => { const m = [[10, "x"], [9, "ix"], [5, "v"], [4, "iiij"], [1, "i"]]; let o = ""; for (const [v, r] of m) while (n >= v) { o += r; n -= v; } return o.replace(/i$/, "j"); };
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const short = d => { const x = new Date(d + "T12:00"); return `${WD[x.getDay()]} ${x.getDate() > 30 ? "xxxj" : ROMAN(x.getDate())} ${MON[x.getMonth()]}`; };
  const html = f => f.text.map(t => `<p>${esc(t).replace(/\n/g, "<br>")}</p>`).join("");
  const isPaper = s => ["draft", "tables", "part", "plot", null].includes(s);
  const appFor = f => f.surface === "glass" ? "glass" : f.surface === "commonplace" ? "commonplace" : isPaper(f.surface) ? "papers" : f.surface === "ledger" ? "accounts" : f.surface === "letter" ? "letters" : ["book", "bill", "pamphlet", "proof"].includes(f.surface) ? "wheel" : f.surface === "almanac" ? "almanac" : null;

  /* the papers on the board: the latest state of each work, newest first */
  const key = f => f.surface === "tables" ? "tables" : `${f.surface || "leaf"}:${f.work || "loose"}`;
  const title = f => f.surface === "tables" ? "The tables" : f.surface === "plot" ? `The plot · ${f.work || ""}`.trim() : f.surface === "part" ? (cap(f.work) || "A part") : (cap(f.work) || "A loose leaf");
  const latest = new Map();
  upto.filter(f => isPaper(f.surface)).forEach(f => latest.set(key(f), f));
  const docs = [...latest.values()].sort((a, b) => `${b.day}${b.t}`.localeCompare(`${a.day}${a.t}`)).slice(0, 7);
  if (cur && isPaper(cur.surface) && !docs.includes(cur)) docs.unshift(cur);
  const sid = f => key(f).replace(/[^a-z0-9]+/gi, "-").toLowerCase();
  D.sheets = docs.map(f => ({ id: sid(f), bundle: "board", title: title(f), meta: f.day === day ? `today, ${f.t}` : short(f.day), html: `<div class="kind-${f.surface || "leaf"}">${html(f)}</div>` }));

  /* the account book: every line he has entered, to this moment */
  const money = s => { const m = [...s.matchAll(/(\d+|\b[ivxlcdmj]+)\s*(li|s|d)\b\.?/gi)]; if (!m.length) return null; const [, n, u] = m[m.length - 1]; const v = /\d/.test(n) ? +n : [...n.toLowerCase()].reduce((a, c, i, A) => { const V = { i: 1, j: 1, v: 5, x: 10, l: 50, c: 100, d: 500, m: 1000 }; return a + (V[c] < (V[A[i + 1]] || 0) ? -V[c] : V[c]); }, 0); return u.toLowerCase().startsWith("l") ? v * 240 : u.toLowerCase() === "s" ? v * 12 : v; };
  const rows = [];
  upto.filter(f => f.surface === "ledger").forEach(f => f.text.forEach(t => { const p = money(t), inc = /recd|receiv|came|paid me/i.test(t); rows.push({ date: short(f.day), item: t, rec: inc ? p : null, paid: inc ? null : p }); }));
  D.ledger = rows.slice(-14); D.ledgerTitle = "The account booke";

  /* letters: what he has read and written, by whom */
  const who = f => {
    const t = f.text.join(" ");
    if (/^(Husband|Good husband|Will[.,])/.test(t) || /\bAnne\b/.test(t) || /\bAnne'?s?\b/.test(f.activity || "") || f.people.includes("Anne Shakespeare")) return ["anne", "Anne Shakespeare", "Henley Street, Stratford"];
    const m = t.match(/^Good Master (\w+)/); if (m) return [m[1].toLowerCase(), "Master " + m[1], ""];
    if (/^Susanna[.,]/.test(t)) return ["susanna", "Susanna Shakespeare", "Henley Street, Stratford"];
    if (f.people[0]) return [f.people[0].toLowerCase().replace(/\W+/g, "_"), f.people[0], ""];
    return ["unknown", "A letter, no name", ""];
  };
  const threads = new Map();
  upto.filter(f => f.surface === "letter").forEach(f => {
    const [id, name, where] = who(f);
    if (!threads.has(id)) threads.set(id, { id, who: name, where, via: id === "anne" || id === "susanna" ? "carrier" : "boy", cost: id === "anne" || id === "susanna" ? "ij d" : "j d", seal: id === "anne" ? "#8a2a1c" : "#2a3a5a", letters: [], replies: [] });
    if (f.day === day && f.kind === "writing" && cur && cur.surface === "letter" && cur.kind === "writing" && who(f)[0] === who(cur)[0]) return; // still on the board, being written
    threads.get(id).letters.push({ dir: f.kind === "writing" ? "out" : "in", date: short(f.day), via: f.kind === "writing" ? "kept copy" : "received", body: f.text.join("\n\n"), state: f.kind === "writing" ? "kept" : undefined });
  });
  D.threads = [...threads.values()].reverse();
  let compose = null, thread = null;
  if (cur && cur.surface === "letter") {
    thread = who(cur)[0];
    if (cur.kind === "writing") { // the letter so far: this morning's sheets to the same hand, in order
      const parts = upto.filter(f => f.day === day && f.surface === "letter" && f.kind === "writing" && who(f)[0] === thread).flatMap(f => f.text);
      const uniq = [...new Set(parts)];
      compose = uniq.filter((p, i) => !uniq.slice(i + 1).some(q => q !== p && q.startsWith(p))).join("\n\n");
    }
  }

  /* the almanack: the journal's calendar, and his own marks */
  D.almanac = {}; for (const [d, evs] of Object.entries(J.calendar)) D.almanac[d] = evs.map(e => e.title);
  D.marks = {}; upto.filter(f => f.surface === "almanac").forEach(f => { D.marks[f.day] = f.text.join("\n").split("\n").filter(Boolean); });

  /* the bookwheel: what he has read, the current page last */
  const onWheel = f => ["book", "bill", "pamphlet", "proof"].includes(f.surface);
  const pages = upto.filter(onWheel).slice(-3);
  if (cur && onWheel(cur) && !pages.includes(cur)) pages.push(cur);
  const pid = f => `j-${f.day}-${f.seg}`;
  pages.forEach(f => {
    const lines = f.text.join("\n").split("\n").filter(Boolean);
    D.pages[pid(f)] = f.surface === "bill"
      ? { sign: "the post", title: "On the post", body: [["bill1", lines[0], lines.slice(1).join(" ")]] }
      : { sign: f.surface === "pamphlet" ? "the stall in Paul's" : (f.work || "a booke"), title: cap(f.work) || lines[0] || "A booke", body: [["verse", lines.join("\n") || " "]] };
  });

  D.commonplace = D.commonplace.filter(e => !e.day || e.day <= day);
  const HEADS = ["Of Kings", "Of Love", "Of Time", "Words", "Faces", "Prices"];
  let cpHead = null;
  upto.filter(f => f.surface === "commonplace").forEach(f => {
    const blob = f.text.join("\n");
    const head = HEADS.find(h => blob.includes(h)) || "Words";
    const text = blob.split("\n").filter(l => l.trim() && !HEADS.includes(l.trim())).join("\n");
    if (text) D.commonplace.push({ day: f.day, head, text, src: "the book" });
    if (cur && f === cur) cpHead = head;
  });

  /* which cabinets are open: the frame's own, and the last other thing he had out today */
  const open = [];
  let front = null, behind = null;
  if (cur) {
    front = appFor(cur);
    const prev = [...upto].reverse().find(f => f !== cur && f.day === day && appFor(f) && appFor(f) !== front);
    if (prev) { behind = appFor(prev); open.push(behind === "papers" ? `papers:${sid(prev)}` : behind); }
    if (front === "papers") open.push(`papers:${sid(cur)}`);
    else if (front === "wheel") pages.forEach(p => open.push(`wheel:${pid(p)}`));
    else if (front === "letters") open.push(`letters:${thread}`);
    else if (front) open.push(front);
  } else { front = "glass"; open.push("glass"); }

  D.scene = {
    id: fr || cl, frame: cur, call, open, focus: front, front, behind, cpHead,
    after(os) {
      if (compose) { const ta = document.querySelector(".win[data-app=letters] textarea"); if (ta) { ta.value = compose; ta.style.height = "200px"; } }
    }
  };
  D.start = `${at}:30`;
  D.threads = D.threads.length ? D.threads : [];
})();
