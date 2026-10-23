// Hintergrundskript: verbindet die Content-Scripts mit dem Guard-Host und
// registriert den Roundcube-Adapter für die eingetragenen Adressen.
"use strict";

const SEND_TIMEOUT_MS = 130_000; // Passwortdialog läuft max. 120 s
const OTHER_TIMEOUT_MS = 5_000;
const ROUNDCUBE_SCRIPTS = ["shared/flow.js", "shared/dom.js", "adapters/roundcube.js"];

const guard = new GuardConnection();
let roundcubeRegistration = null;

function notify(title, message) {
  return browser.notifications.create({ type: "basic", title, message }).catch(() => {});
}

async function handle(message) {
  if (message.type === "notify") {
    await notify(message.title, message.message);
    return { ok: true };
  }
  if (!["ping", "before_send", "check"].includes(message.type)) return { error: "unknown_type" };
  const timeout = message.type === "before_send" ? SEND_TIMEOUT_MS : OTHER_TIMEOUT_MS;
  try {
    return await guard.ask(message, timeout);
  } catch (error) {
    return { error: String(error && error.message ? error.message : error) };
  }
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (sender.id !== browser.runtime.id) return undefined;
  return handle(message);
});

async function registerRoundcube() {
  const { roundcubeOrigins = [] } = await browser.storage.local.get("roundcubeOrigins");
  if (roundcubeRegistration) {
    await roundcubeRegistration.unregister();
    roundcubeRegistration = null;
  }
  const allowed = [];
  for (const origin of roundcubeOrigins) {
    if (await browser.permissions.contains({ origins: [`${origin}/*`] })) allowed.push(`${origin}/*`);
  }
  if (allowed.length === 0) return;
  roundcubeRegistration = await browser.contentScripts.register({
    matches: allowed,
    js: ROUNDCUBE_SCRIPTS.map((file) => ({ file })),
    runAt: "document_idle",
  });
}

browser.storage.onChanged.addListener((changes) => {
  if (changes.roundcubeOrigins) registerRoundcube();
});
browser.permissions.onAdded.addListener(registerRoundcube);
browser.permissions.onRemoved.addListener(registerRoundcube);
registerRoundcube();
