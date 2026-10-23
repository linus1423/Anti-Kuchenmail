// Gemeinsamer Ablauf für alle Webmail-Adapter (Content-Script).
//
// Ein Adapter liefert:
//   client: "gmail" | "outlook" | "roundcube"
//   install(onSendAttempt): fängt Senden ab und ruft onSendAttempt(ctx) auf
//   openDrafts(): Liste offener Entwürfe (für die Prüfung beim Schreiben)
// Ein ctx (ein Entwurf) liefert:
//   key: Objekt, das den Entwurf eindeutig macht (z. B. sein Wurzelelement)
//   readDraft(): {subject, plain_text, html, recipients} oder null
//   resend(): Senden erneut auslösen, diesmal ohne Abfangen
//   discard(): Entwurf verwerfen
"use strict";

// eslint-disable-next-line no-var
var KuchenmailGuard = (() => {
  const CHECK_INTERVAL_MS = 2_000;
  const SETTINGS_INTERVAL_MS = 60_000;
  const busy = new WeakSet();
  const draftIds = new WeakMap();
  let nextDraftId = 1;
  let lockOnDetect = false;

  const ask = (message) => browser.runtime.sendMessage(message);
  const notify = (message) => ask({ type: "notify", title: "Kuchenmail-Guard", message }).catch(() => {});

  function draftId(ctx) {
    if (!draftIds.has(ctx.key)) draftIds.set(ctx.key, `${location.hostname}-${nextDraftId++}`);
    return draftIds.get(ctx.key);
  }

  function safeRead(ctx) {
    try {
      return ctx.readDraft();
    } catch (error) {
      console.error("Kuchenmail-Guard: Entwurf nicht lesbar", error);
      return null;
    }
  }

  async function guardSend(adapter, ctx) {
    if (busy.has(ctx.key)) return "busy";
    busy.add(ctx.key);
    try {
      const draft = safeRead(ctx);
      if (!draft) {
        // Fail-closed: lieber blockieren als ungeprüft senden
        notify("Mail konnte nicht gelesen werden, Senden blockiert. Zum Senden ohne Schutz die Erweiterung deaktivieren.");
        return "unreadable";
      }
      let response;
      try {
        response = await ask({ type: "before_send", client: adapter.client, draft_id: draftId(ctx), ...draft });
      } catch (error) {
        response = { error: String(error) };
      }
      if (!response || response.error) {
        notify("Guard-Host nicht erreichbar, Senden blockiert. Zum Senden ohne Schutz die Erweiterung deaktivieren.");
        return "error";
      }
      if (response.action === "send") {
        ctx.resend();
      } else if (response.action === "discard") {
        ctx.discard();
      } else if (response.reason === "auth_unavailable") {
        notify("Passwortabfrage nicht möglich (zenity fehlt?). Senden blockiert.");
      }
      return response.action;
    } finally {
      busy.delete(ctx.key);
    }
  }

  async function checkOpenDrafts(adapter) {
    if (!lockOnDetect) return;
    for (const ctx of adapter.openDrafts()) {
      if (busy.has(ctx.key)) continue;
      const draft = safeRead(ctx);
      if (!draft) continue;
      try {
        await ask({ type: "check", client: adapter.client, draft_id: draftId(ctx), ...draft });
      } catch (error) {
        console.error("Kuchenmail-Guard: Prüfung beim Schreiben fehlgeschlagen", error);
      }
    }
  }

  async function refreshSettings() {
    try {
      const pong = await ask({ type: "ping" });
      lockOnDetect = Boolean(pong && pong.lock_on_detect);
    } catch (error) {
      lockOnDetect = false;
    }
  }

  function start(adapter) {
    adapter.install((ctx) => guardSend(adapter, ctx));
    refreshSettings();
    setInterval(refreshSettings, SETTINGS_INTERVAL_MS);
    setInterval(() => checkOpenDrafts(adapter), CHECK_INTERVAL_MS);
  }

  return { start, guardSend, checkOpenDrafts, refreshSettings };
})();
