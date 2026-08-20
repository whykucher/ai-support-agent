/**
 * Northwind chat widget - drop-in, no build step, no framework.
 *
 *   <script src="https://your-host/static/widget.js"
 *           data-api="https://your-host"
 *           data-accent="#7c4a2d" defer></script>
 *
 * Everything is configured from data-attributes on that tag, so a client can
 * install it by pasting one line into their theme.
 */
(function () {
  "use strict";

  var script = document.currentScript ||
    document.querySelector('script[src*="widget.js"]');
  var cfg = {
    api: (script && script.dataset.api) || window.location.origin,
    title: (script && script.dataset.title) || "Northwind Support",
    agent: (script && script.dataset.agent) || "Nora",
    accent: (script && script.dataset.accent) || "",
    site: (script && script.dataset.site) || "demo",
    leadTitle: (script && script.dataset.leadTitle) || "Want a specialist to follow up?",
    leadNote: (script && script.dataset.leadNote) ||
      "Leave your details and we reply within one business day.",
    greeting: (script && script.dataset.greeting) ||
      "Hi! I can help with orders, shipping, subscriptions and wholesale. What do you need?",
    quick: ((script && script.dataset.quick) ||
      "How fast is shipping?|What is your return policy?|I need wholesale pricing").split("|")
  };

  // Stylesheet lives next to this script, whatever host it is served from.
  if (script && script.src) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = script.src.replace(/widget\.js(\?.*)?$/, "widget.css");
    document.head.appendChild(link);
  }

  var storeKey = function () { return "nw_conversation_id_" + cfg.site; };
  var conversationId = null;
  try { conversationId = localStorage.getItem(storeKey()); } catch (e) { /* private mode */ }

  var root = document.createElement("div");
  root.className = "nw-widget";
  root.setAttribute("data-open", "false");
  if (cfg.accent) root.style.setProperty("--nw-accent", cfg.accent);

  root.innerHTML = [
    '<button class="nw-launcher" type="button" aria-label="Open chat">',
    '  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">',
    '    <path d="M21 11.5a8.4 8.4 0 0 1-9 8.4 9 9 0 0 1-4-.9L3 21l1.9-4.6A8.4 8.4 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3 8.5 8.5 0 0 1 21 11.5z"/>',
    '  </svg><span>Ask us</span>',
    '</button>',
    '<div class="nw-panel" role="dialog" aria-label="Support chat">',
    '  <div class="nw-head">',
    '    <div class="nw-avatar">' + cfg.agent.charAt(0).toUpperCase() + '</div>',
    '    <div><h3>' + esc(cfg.title) + '</h3><p>Replies instantly</p></div>',
    '    <button class="nw-close" type="button" aria-label="Close chat">&times;</button>',
    '  </div>',
    '  <div class="nw-log" id="nw-log"></div>',
    '  <div class="nw-quick" id="nw-quick"></div>',
    '  <div id="nw-lead-slot"></div>',
    '  <form class="nw-form" id="nw-form">',
    '    <textarea id="nw-input" rows="1" placeholder="Ask anything..." aria-label="Message"></textarea>',
    '    <button class="nw-send" type="submit" aria-label="Send">',
    '      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>',
    '    </button>',
    '  </form>',
    '  <div class="nw-foot">Answers come from the company knowledge base</div>',
    '</div>'
  ].join("");

  document.body.appendChild(root);

  var log = root.querySelector("#nw-log");
  var quickBar = root.querySelector("#nw-quick");
  var leadSlot = root.querySelector("#nw-lead-slot");
  var form = root.querySelector("#nw-form");
  var input = root.querySelector("#nw-input");
  var sendBtn = root.querySelector(".nw-send");

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function scroll() { log.scrollTop = log.scrollHeight; }

  function bubble(text, who) {
    var el = document.createElement("div");
    el.className = "nw-msg " + who;
    el.textContent = text;
    log.appendChild(el);
    scroll();
    return el;
  }

  function showSources(sources) {
    if (!sources || !sources.length) return;
    var wrap = document.createElement("div");
    wrap.className = "nw-sources";
    sources.slice(0, 3).forEach(function (s) {
      var chip = document.createElement("span");
      chip.className = "nw-chip";
      chip.textContent = s;
      wrap.appendChild(chip);
    });
    log.appendChild(wrap);
    scroll();
  }

  function typing(on) {
    var existing = log.querySelector(".nw-typing");
    if (!on) { if (existing) existing.remove(); return; }
    if (existing) return;
    var el = document.createElement("div");
    el.className = "nw-typing";
    el.innerHTML = "<span></span><span></span><span></span>";
    log.appendChild(el);
    scroll();
  }

  function renderQuick() {
    quickBar.innerHTML = "";
    cfg.quick.forEach(function (q) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = q;
      b.addEventListener("click", function () { send(q); });
      quickBar.appendChild(b);
    });
  }

  function hideQuick() { quickBar.innerHTML = ""; }

  /** Inline lead form - appears only when the backend says intent is commercial. */
  function showLeadForm() {
    if (leadSlot.firstChild) return;
    var box = document.createElement("div");
    box.className = "nw-lead";
    box.innerHTML = [
      "<h4>" + esc(cfg.leadTitle) + "</h4>",
      "<p>" + esc(cfg.leadNote) + "</p>",
      '<input id="nw-l-name" placeholder="Name" autocomplete="name">',
      '<input id="nw-l-email" type="email" placeholder="Email" autocomplete="email">',
      '<button type="button" id="nw-l-send">Send my details</button>'
    ].join("");
    leadSlot.appendChild(box);

    box.querySelector("#nw-l-send").addEventListener("click", function () {
      var email = box.querySelector("#nw-l-email").value.trim();
      if (!email) { box.querySelector("#nw-l-email").focus(); return; }
      var btn = box.querySelector("#nw-l-send");
      btn.disabled = true;
      btn.textContent = "Sending...";
      fetch(cfg.api + "/api/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId || "",
          site: cfg.site,
          name: box.querySelector("#nw-l-name").value.trim(),
          email: email,
          message: "Requested follow-up from chat widget",
          page_url: window.location.href
        })
      }).then(function () {
        box.innerHTML = '<div class="nw-done">Thanks! Our team has your details.</div>';
      }).catch(function () {
        btn.disabled = false;
        btn.textContent = "Try again";
      });
    });
  }

  function send(text) {
    text = (text || input.value).trim();
    if (!text) return;
    // A page can call send() from its own button. Opening first means the
    // visitor actually sees the answer instead of nothing appearing to happen.
    open();
    hideQuick();
    bubble(text, "user");
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    typing(true);

    fetch(cfg.api + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        site: cfg.site,
        conversation_id: conversationId,
        page_url: window.location.href
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        typing(false);
        if (data.error) { bubble(data.error, "bot"); return; }
        conversationId = data.conversation_id;
        try { localStorage.setItem(storeKey(), conversationId); } catch (e) { /* noop */ }
        bubble(data.answer, "bot");
        showSources(data.sources);
        if (data.show_lead_form) showLeadForm();
        if (data.lead) {
          bubble("Got it - I passed your contact to the team.", "bot");
        }
      })
      .catch(function () {
        typing(false);
        bubble("I could not reach the server. Please try again in a moment.", "bot");
      })
      .finally(function () {
        sendBtn.disabled = false;
        input.focus();
      });
  }

  form.addEventListener("submit", function (e) { e.preventDefault(); send(); });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });

  input.addEventListener("input", function () {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 96) + "px";
  });

  function open() {
    root.setAttribute("data-open", "true");
    if (!log.children.length) { bubble(cfg.greeting, "bot"); renderQuick(); }
    input.focus();
  }

  root.querySelector(".nw-launcher").addEventListener("click", open);
  root.querySelector(".nw-close").addEventListener("click", function () {
    root.setAttribute("data-open", "false");
  });

  /**
   * Point the widget at a different tenant without a page reload.
   * Used by the industry picker: one widget, several businesses. Each site
   * keeps its own conversation, so switching back does not lose the thread.
   */
  function setSite(site, opts) {
    opts = opts || {};
    if (site === cfg.site && !opts.force) return;

    cfg.site = site;
    if (opts.title) cfg.title = opts.title;
    if (opts.agent) cfg.agent = opts.agent;
    if (opts.greeting) cfg.greeting = opts.greeting;
    if (opts.quick) cfg.quick = opts.quick;
    cfg.leadTitle = opts.leadTitle || "Want a specialist to follow up?";
    cfg.leadNote = opts.leadNote ||
      "Leave your details and we reply within one business day.";
    if (opts.accent) root.style.setProperty("--nw-accent", opts.accent);
    if (opts.accentDark) root.style.setProperty("--nw-accent-d", opts.accentDark);

    root.querySelector(".nw-head h3").textContent = cfg.title;
    root.querySelector(".nw-avatar").textContent = cfg.agent.charAt(0).toUpperCase();

    conversationId = null;
    try { conversationId = localStorage.getItem(storeKey()); } catch (e) { /* noop */ }

    log.innerHTML = "";
    leadSlot.innerHTML = "";
    hideQuick();

    // If the panel is already open, re-greet as the new business. Clearing the
    // log without this leaves the visitor staring at an empty window after
    // switching industries.
    var isOpen = root.getAttribute("data-open") === "true";
    if (opts.open !== false || isOpen) open();
  }

  window.NorthwindChat = { open: open, send: send, setSite: setSite };
})();
