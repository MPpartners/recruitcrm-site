/*
 * Recruit CRM — свой счётчик посещений сайта (T99). Шлёт в CRM: какую страницу открыли, сколько она была на экране,
 * докуда пролистали, сколько смотрели видео, что нажимали, откуда пришли. Посетитель — случайный id в localStorage,
 * без отпечатков браузера и cookie. IP-адрес CRM не хранит: по нему один раз определяется город.
 * Не считать свои визиты: открыть сайт с ?nostats=1 (вернуть — ?nostats=0).
 */
(function () {
  "use strict";
  var URL_ = window.RC_STATS_URL || "https://app.recruitcrm.pro/api/site/event";
  var ls = function (k, v) { try { if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { return null; } };
  var ss = function (k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } };
  var params = new URLSearchParams(location.search);
  if (params.get("nostats") === "1") ls("rc_nostats", "1");
  if (params.get("nostats") === "0") ls("rc_nostats", null);
  if (ls("rc_nostats") === "1" || navigator.webdriver || !navigator.sendBeacon) return;

  var uuid = function () {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    var b = new Uint8Array(16); crypto.getRandomValues(b); b[6] = (b[6] & 15) | 64; b[8] = (b[8] & 63) | 128;
    var h = Array.prototype.map.call(b, function (x) { return (x + 256).toString(16).slice(1); }).join("");
    return h.slice(0, 8) + "-" + h.slice(8, 12) + "-" + h.slice(12, 16) + "-" + h.slice(16, 20) + "-" + h.slice(20);
  };
  var vid = ls("rc_vid") || uuid(); ls("rc_vid", vid);
  // A visit is one browser tab session: pages opened from each other in it are one visit.
  var sid = ss("rc_sid"), n;
  if (!sid) { sid = uuid(); ss("rc_sid", sid); n = (parseInt(ls("rc_n") || "0", 10) || 0) + 1; ls("rc_n", String(n)); ss("rc_vn", String(n)); }
  n = parseInt(ss("rc_vn") || "1", 10) || 1;
  var pid = uuid();
  var send = function (o) { try { navigator.sendBeacon(URL_, new Blob([JSON.stringify(o)], { type: "text/plain" })); } catch (e) {} };

  var q = {};
  ["utm_source", "utm_medium", "utm_campaign"].forEach(function (k) { if (params.get(k)) q[k] = params.get(k).slice(0, 100); });
  var ref = params.get("от") || params.get("ref"); if (ref) q.ref = ref.slice(0, 60);
  var tz = ""; try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
  send({ k: "view", vid: vid, sid: sid, pid: pid, n: n, path: location.pathname, title: document.title.slice(0, 200),
    ref: document.referrer.slice(0, 500), q: q, tz: tz, lang: (navigator.language || "").slice(0, 35),
    sw: screen.width | 0, sh: screen.height | 0 });

  // Time on screen: only while the tab is visible.
  var active = 0, shownAt = document.visibilityState === "visible" ? Date.now() : 0;
  var seconds = function () { return Math.round((active + (shownAt ? Date.now() - shownAt : 0)) / 1000); };
  var scroll = 0;
  var onScroll = function () {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var p = h > 0 ? Math.round((window.scrollY / h) * 100) : 100;
    if (p > scroll) scroll = Math.min(100, p);
  };
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();

  var video = 0;
  document.querySelectorAll("video").forEach(function (v) {
    var last = 0;
    v.addEventListener("timeupdate", function () { var d = v.currentTime - last; if (d > 0 && d < 2) video += d; last = v.currentTime; });
    v.addEventListener("seeked", function () { last = v.currentTime; });
    v.addEventListener("play", function () { ev("play", ""); }, { once: true });
  });

  var queue = [], sent = 0;
  var ev = function (t, l) { if (sent + queue.length < 50) queue.push({ t: t, l: (l || "").replace(/\s+/g, " ").trim().slice(0, 80), s: seconds() }); };
  // Only what the visitor did: a section the search opened is not a click.
  document.addEventListener("click", function (e) {
    if (!e.target.closest) return;
    var sum = e.target.closest("summary");
    if (sum) { if (!sum.parentElement.open) ev("open", sum.textContent); return; }
    var a = e.target.closest("a.btn, button, nav a, .footerlinks a, .kb-toc a");
    if (a) ev("click", a.textContent);
    // T100: the demo knows it is the same visitor (its own counter takes ?rcv=…). Straight to /login: the demo's «/»
    // redirects there without the query.
    var d = e.target.closest('a[href^="https://demo.recruitcrm.pro"]');
    if (d) { try { var u = new URL(d.href); if (u.pathname === "/") u.pathname = "/login"; u.searchParams.set("rcv", vid); d.href = u.toString(); } catch (x) {} }
  });
  var kb = document.getElementById("kb-q"), kbTimer;
  if (kb) kb.addEventListener("input", function () { clearTimeout(kbTimer); kbTimer = setTimeout(function () { if (kb.value.trim().length > 2) ev("search", kb.value); }, 1500); });

  var lastSent = "";
  var ping = function () {
    var o = { k: "ping", sid: sid, pid: pid, act: seconds(), scroll: scroll, video: Math.round(video), ev: queue.splice(0, 20) };
    var key = o.act + "|" + o.scroll + "|" + o.video;
    if (key === lastSent && !o.ev.length) return;
    lastSent = key; sent += o.ev.length; send(o);
  };
  setInterval(function () { if (document.visibilityState === "visible") ping(); }, 15000);
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") { if (shownAt) { active += Date.now() - shownAt; shownAt = 0; } ping(); }
    else shownAt = Date.now();
  });
  window.addEventListener("pagehide", ping);
})();
