// Kuchenmail-Guard für Thunderbird: fragt vor jedem Senden den Guard-Host.
"use strict";

const SEND_TIMEOUT_MS = 130_000; // Passwortdialog läuft max. 120 s
const CHECK_TIMEOUT_MS = 5_000;
const CHECK_INTERVAL_MS = 2_000;
const PING_INTERVAL_MS = 60_000;

const guard = new GuardConnection();
let lockOnDetect = false;

function address(entry) {
  if (typeof entry === "string") {
    const match = entry.match(/<([^>]+)>/);
    return (match ? match[1] : entry).trim();
  }
  // Adressbuch-Eintrag oder Verteilerliste ({id, type})
  return entry && entry.type === "mailingList" ? `list:${entry.id}` : `contact:${entry && entry.id}`;
}

function recipientsOf(details) {
  return ["to", "cc", "bcc"]
    .flatMap((field) => [].concat(details[field] || []))
    .map(address)
    .filter(Boolean);
}

function draftMessage(type, details, tab) {
  return {
    type,
    client: "thunderbird",
    draft_id: `tb-${tab.id}`,
    subject: details.subject || "",
    plain_text: details.plainTextBody || "",
    html: details.isPlainText ? null : details.body || null,
    recipients: recipientsOf(details),
  };
}

function notify(title, message) {
  return browser.notifications.create({ type: "basic", title, message }).catch(() => {});
}

async function discard(tab) {
  try {
    await browser.compose.setComposeDetails(tab.id, { body: "", plainTextBody: "", subject: "" });
  } catch (error) {
    console.error("Kuchenmail-Guard: Entwurf konnte nicht geleert werden", error);
  }
  try {
    await browser.tabs.remove(tab.id);
  } catch (error) {
    console.error("Kuchenmail-Guard: Fenster konnte nicht geschlossen werden", error);
  }
}

browser.compose.onBeforeSend.addListener(async (tab, details) => {
  let response;
  try {
    response = await guard.ask(draftMessage("before_send", details, tab), SEND_TIMEOUT_MS);
  } catch (error) {
    // Fail-closed: ohne Guard-Host wird nicht gesendet
    notify(
      "Kuchenmail-Guard nicht erreichbar",
      "Senden blockiert. Zum Senden ohne Schutz die Erweiterung Kuchenmail-Guard deaktivieren."
    );
    console.error("Kuchenmail-Guard:", error);
    return { cancel: true };
  }

  if (response.action === "send") return { cancel: false };
  if (response.action === "discard") {
    // Erst nach dem Abbruch schließen, damit Thunderbird nicht doch noch sendet
    setTimeout(() => discard(tab), 0);
  } else if (response.reason === "auth_unavailable") {
    notify("Kuchenmail-Guard", "Passwortabfrage nicht möglich (zenity fehlt?). Senden blockiert.");
  }
  return { cancel: true };
});

// R4.5: Bildschirm schon beim Schreiben sperren, wenn lock_on_detect aktiv ist
async function checkOpenDrafts() {
  if (!lockOnDetect) return;
  const windows = await browser.windows.getAll({ populate: true, windowTypes: ["messageCompose"] });
  for (const tab of windows.flatMap((w) => w.tabs || [])) {
    try {
      const details = await browser.compose.getComposeDetails(tab.id);
      await guard.ask(draftMessage("check", details, tab), CHECK_TIMEOUT_MS);
    } catch (error) {
      console.error("Kuchenmail-Guard: Prüfung beim Schreiben fehlgeschlagen", error);
    }
  }
}

async function refreshSettings() {
  try {
    const pong = await guard.ask({ type: "ping" }, CHECK_TIMEOUT_MS);
    lockOnDetect = Boolean(pong.lock_on_detect);
  } catch (error) {
    console.error("Kuchenmail-Guard: Guard-Host nicht erreichbar", error);
  }
}

refreshSettings();
setInterval(refreshSettings, PING_INTERVAL_MS);
setInterval(checkOpenDrafts, CHECK_INTERVAL_MS);
