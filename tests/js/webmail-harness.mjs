// Lädt die Webmail-Content-Scripts in ein jsdom-Fenster mit gefälschter browser-API.
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

const DIR = new URL("../../extensions/webmail/", import.meta.url).pathname;

export const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

export function loadAdapter(adapterFile, html, { respond, url = "https://mail.google.com/mail/u/0/", beforeScripts } = {}) {
  const dom = new JSDOM(html, { url, runScripts: "dangerously" });
  const { window } = dom;
  const sent = [];
  window.browser = {
    runtime: {
      sendMessage: async (message) => {
        sent.push(JSON.parse(JSON.stringify(message)));
        if (message.type === "ping") return { ok: true, lock_on_detect: false };
        if (message.type === "notify") return { ok: true };
        return respond(message);
      },
    },
  };
  window.setInterval = () => 0; // Hintergrund-Prüfungen im Test nicht laufen lassen
  if (beforeScripts) beforeScripts(window);
  for (const file of ["shared/flow.js", "shared/dom.js", adapterFile]) {
    // Als <script> statt eval: nur so werden Top-Level-"var" wie in Firefox-Content-Scripts global
    const script = window.document.createElement("script");
    script.textContent = readFileSync(DIR + file, "utf8");
    window.document.head.append(script);
  }
  return { window, document: window.document, sent, adapter: window.KuchenmailAdapter };
}

export const requests = (sent, type = "before_send") => sent.filter((m) => m.type === type);
export const notices = (sent) => sent.filter((m) => m.type === "notify");
