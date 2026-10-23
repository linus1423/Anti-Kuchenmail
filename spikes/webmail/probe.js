// Probe für Gmail, Outlook im Web und Roundcube.
// Fängt Klicks auf mögliche Senden-Buttons und Strg+Enter ab, blockiert den Versand
// und protokolliert, welche Felder gefunden wurden. Freigabe: Alt gedrückt halten
// und erneut senden.
(() => {
  const host = location.hostname;
  const client = host === "mail.google.com" ? "gmail"
    : /(^|\.)outlook\.(office|office365|live)\.com$|^outlook\.cloud\.microsoft$/.test(host) ? "outlook"
    : document.querySelector("#rcmloginuser, #messagestack, body.task-mail") ? "roundcube"
    : null;
  if (!client) return;

  const report = (type, data) => browser.runtime.sendMessage({ type, client, ...data });
  const text = (el) => (el ? (el.value ?? el.innerText ?? "").slice(0, 300) : null);
  const describe = (el) => el && {
    tag: el.tagName.toLowerCase(),
    name: el.getAttribute("name"),
    role: el.getAttribute("role"),
    ariaLabel: el.getAttribute("aria-label"),
    tooltip: el.getAttribute("data-tooltip"),
    command: el.getAttribute("data-command") || el.getAttribute("onclick"),
    classes: el.className && String(el.className).slice(0, 120),
  };

  const probes = {
    gmail: () => ({
      subject: text(document.querySelector("input[name=subjectbox]")),
      body: text(document.querySelector("div[role=textbox][contenteditable=true]")),
      recipients: [...document.querySelectorAll("[role=dialog] [email], .aoD [email], [data-hovercard-id]")]
        .map((e) => e.getAttribute("email") || e.getAttribute("data-hovercard-id")),
    }),
    outlook: () => ({
      subject: text(document.querySelector(
        "input[aria-label='Betreff hinzufügen'], input[aria-label='Add a subject'], input[placeholder='Betreff hinzufügen'], input[placeholder='Add a subject']")),
      body: text(document.querySelector("div[role=textbox][contenteditable=true]")),
      recipients: [...document.querySelectorAll("[role=textbox] span[class] , div[aria-label^='An'] span, div[aria-label^='To'] span")]
        .map((e) => e.textContent).filter((t) => t && t.includes("@")).slice(0, 20),
    }),
    roundcube: () => {
      const rc = window.wrappedJSObject && window.wrappedJSObject.rcmail;
      const tiny = window.wrappedJSObject && window.wrappedJSObject.tinymce;
      return {
        rcmailPresent: Boolean(rc),
        rcversion: rc && rc.env ? String(rc.env.rcversion || rc.env.version || "") : null,
        skin: rc && rc.env ? String(rc.env.skin || "") : null,
        editor: rc && rc.env ? String(rc.env.editor_type || "") : null,
        subject: text(document.querySelector("input[name=_subject]")),
        body: text(document.querySelector("textarea[name=_message]")),
        tinymceBody: tiny && tiny.activeEditor ? String(tiny.activeEditor.getContent({ format: "text" })).slice(0, 300) : null,
        recipients: ["_to", "_cc", "_bcc"].map((n) => text(document.querySelector(`[name=${n}]`))),
      };
    },
  };

  const isSendButton = (el) => {
    const b = el.closest("button, [role=button], a");
    if (!b) return null;
    const label = `${b.getAttribute("aria-label") || ""} ${b.getAttribute("data-tooltip") || ""} ${b.textContent || ""} ${b.getAttribute("onclick") || ""} ${b.getAttribute("data-command") || ""} ${b.className || ""}`;
    return /(^|\W)(senden|send)(\W|$)/i.test(label) ? b : null;
  };

  const intercept = (event, trigger, button) => {
    if (event.altKey) {
      report("released", { trigger });
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    report("send_attempt", { trigger, button: describe(button), found: probes[client]() });
    console.warn("[Kuchenmail-Spike] Senden blockiert. Mit gedrückter Alt-Taste erneut senden.");
  };

  document.addEventListener("click", (e) => {
    const b = isSendButton(e.target);
    if (b) intercept(e, "click", b);
  }, true);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) intercept(e, "ctrl+enter", null);
  }, true);

  if (client === "roundcube") {
    // rcmail.command('send') umhüllen, um auch Menü und Tastenkürzel zu sehen.
    const page = window.wrappedJSObject;
    const rc = page && page.rcmail;
    if (rc && typeof rc.command === "function") {
      const original = rc.command;
      rc.command = exportFunction(function (cmd, ...args) {
        if (cmd === "send") report("rcmail_command_send", { found: probes.roundcube() });
        return original.call(this, cmd, ...args);
      }, page);
    }
  }

  report("loaded", { found: probes[client]() });
})();
