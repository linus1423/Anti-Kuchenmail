// Adapter-Tests gegen vereinfachte Nachbauten der Webmail-Oberflächen.
// Sie prüfen die Logik, nicht ob die Selektoren zur echten Seite passen (das klärt T2).
import { test } from "node:test";
import assert from "node:assert/strict";
import { loadAdapter, notices, requests, tick } from "./webmail-harness.mjs";

const GMAIL = `
<div role="dialog" id="compose">
  <div class="chips"><span email="Team@Firma.example">Team</span><div data-hovercard-id="anna@firma.example">Anna</div></div>
  <input type="text" aria-label="Empfänger" value="ben@firma.example">
  <input name="subjectbox" value="Kuchen">
  <div contenteditable="true" role="textbox" id="body">Ich bringe morgen Kuchen mit</div>
  <div role="button" id="send" data-tooltip="Senden (Strg-Eingabetaste)">Senden</div>
  <div role="button" id="schedule" aria-label="Weitere Sendeoptionen"></div>
  <div role="button" id="discard" data-tooltip="Entwurf verwerfen"></div>
</div>`;

function pageClicks(document, id) {
  const counter = { n: 0 };
  document.getElementById(id).addEventListener("click", () => counter.n++);
  return counter;
}

const click = (window, el) => el.dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true }));

test("gmail: click on send is held, draft is read, released mail is sent", async () => {
  const { window, document, sent } = loadAdapter("adapters/gmail.js", GMAIL, { respond: () => ({ action: "send" }) });
  const pageSend = pageClicks(document, "send");
  click(window, document.getElementById("send"));
  assert.equal(pageSend.n, 0, "Gmail darf den ersten Klick nicht sehen");
  await tick();
  const [request] = requests(sent);
  assert.equal(request.client, "gmail");
  assert.equal(request.subject, "Kuchen");
  assert.equal(request.plain_text, "Ich bringe morgen Kuchen mit");
  assert.deepEqual(request.recipients.sort(), ["anna@firma.example", "ben@firma.example", "team@firma.example"]);
  await tick();
  assert.equal(pageSend.n, 1, "nach Freigabe wird erneut geklickt");
});

test("gmail: cancel keeps the mail, discard clicks discard", async () => {
  let action = "cancel";
  const { window, document } = loadAdapter("adapters/gmail.js", GMAIL, { respond: () => ({ action }) });
  const pageSend = pageClicks(document, "send");
  const pageDiscard = pageClicks(document, "discard");
  click(window, document.getElementById("send"));
  await tick(); await tick();
  assert.equal(pageSend.n, 0);
  action = "discard";
  click(window, document.getElementById("send"));
  await tick(); await tick();
  assert.equal(pageDiscard.n, 1);
  assert.equal(pageSend.n, 0);
});

test("gmail: ctrl+enter in the body is held", async () => {
  const { window, document, sent } = loadAdapter("adapters/gmail.js", GMAIL, { respond: () => ({ action: "cancel" }) });
  const event = new window.KeyboardEvent("keydown", { key: "Enter", ctrlKey: true, bubbles: true, cancelable: true });
  document.getElementById("body").dispatchEvent(event);
  assert.equal(event.defaultPrevented, true);
  await tick();
  assert.equal(requests(sent).length, 1);
});

test("gmail: schedule-send button is not treated as send", () => {
  const { document, adapter } = loadAdapter("adapters/gmail.js", GMAIL, { respond: () => ({}) });
  assert.equal(adapter._isSendButton(document.getElementById("schedule")), false);
  assert.equal(adapter._isSendButton(document.getElementById("send")), true);
});

test("gmail: host unreachable blocks and notifies", async () => {
  const { window, document, sent } = loadAdapter("adapters/gmail.js", GMAIL, { respond: () => ({ error: "weg" }) });
  const pageSend = pageClicks(document, "send");
  click(window, document.getElementById("send"));
  await tick(); await tick();
  assert.equal(pageSend.n, 0);
  assert.equal(notices(sent).length, 1);
});

const OUTLOOK = `
<div id="compose">
  <div role="textbox" contenteditable="true" aria-label="An"><span title="Team &lt;team@firma.example&gt;">Team</span></div>
  <div role="textbox" contenteditable="true" aria-label="Cc">carla@firma.example</div>
  <input aria-label="Betreff hinzufügen" value="Freitag">
  <div role="textbox" contenteditable="true" aria-label="Nachrichtentext" id="body"><p>Freitag gebe ich eine Runde Eis aus</p></div>
  <button id="send" aria-label="Senden" title="Senden (Strg+Eingabe)">Senden</button>
  <button id="later" aria-label="Später senden"></button>
  <button id="discard" aria-label="Verwerfen"></button>
</div>`;

test("outlook: picks the message body, not the recipient fields", async () => {
  const { window, document, sent } = loadAdapter("adapters/outlook.js", OUTLOOK, {
    url: "https://outlook.office.com/mail/",
    respond: () => ({ action: "send" }),
  });
  const pageSend = pageClicks(document, "send");
  click(window, document.getElementById("send"));
  await tick();
  const [request] = requests(sent);
  assert.equal(request.client, "outlook");
  assert.equal(request.subject, "Freitag");
  assert.equal(request.plain_text, "Freitag gebe ich eine Runde Eis aus");
  assert.deepEqual(request.recipients.sort(), ["carla@firma.example", "team@firma.example"]);
  await tick();
  assert.equal(pageSend.n, 1);
});

test("outlook: english labels and 'send later' exclusion", () => {
  const html = OUTLOOK.replace('aria-label="Senden"', 'aria-label="Send"').replace('aria-label="An"', 'aria-label="To"');
  const { document, adapter } = loadAdapter("adapters/outlook.js", html, { url: "https://outlook.live.com/mail/", respond: () => ({}) });
  assert.equal(adapter._isSendButton(document.getElementById("send")), true);
  assert.equal(adapter._isSendButton(document.getElementById("later")), false);
  assert.equal(adapter._readDraft(document.getElementById("compose")).recipients.includes("team@firma.example"), true);
});

test("outlook: inline reply without subject field", () => {
  const html = OUTLOOK.replace('<input aria-label="Betreff hinzufügen" value="Freitag">', "");
  const { document, adapter } = loadAdapter("adapters/outlook.js", html, { url: "https://outlook.office.com/mail/", respond: () => ({}) });
  assert.equal(adapter._readDraft(document.getElementById("compose")).subject, "");
});

test("outlook: discard clicks Verwerfen", async () => {
  const { window, document } = loadAdapter("adapters/outlook.js", OUTLOOK, {
    url: "https://outlook.office.com/mail/",
    respond: () => ({ action: "discard" }),
  });
  const pageDiscard = pageClicks(document, "discard");
  click(window, document.getElementById("send"));
  await tick(); await tick();
  assert.equal(pageDiscard.n, 1);
});

function roundcubeWindow(window, { html = true } = {}) {
  window.rcmailCalls = [];
  window.rcmail = {
    env: { action: "compose" },
    editor: {
      is_html: () => html,
      get_content: (o) => (o.format === "text" ? "Morgen bringe ich Muffins mit" : "<p>Morgen bringe ich Muffins mit</p>"),
      set_content: (v) => window.rcmailCalls.push(["set_content", v]),
    },
    command(cmd) {
      window.rcmailCalls.push(["command", cmd]);
      return true;
    },
  };
  window.wrappedJSObject = window;
  window.exportFunction = (fn) => fn;
}

const ROUNDCUBE = `
<form><input name="_subject" value="Info"><textarea name="_to">team@firma.example, Anna &lt;anna@firma.example&gt;</textarea>
<textarea name="_cc"></textarea><textarea name="_message">Morgen bringe ich Muffins mit</textarea></form>`;

test("roundcube: rcmail.command('send') is held and released", async () => {
  const { window, sent } = loadAdapter("adapters/roundcube.js", ROUNDCUBE, {
    url: "https://webmail.example.de/?_task=mail&_action=compose",
    respond: () => ({ action: "send" }),
    beforeScripts: roundcubeWindow,
  });
  assert.equal(window.rcmail.command("send"), false);
  assert.deepEqual(window.rcmailCalls, []);
  await tick();
  const [request] = requests(sent);
  assert.equal(request.client, "roundcube");
  assert.equal(request.subject, "Info");
  assert.equal(request.plain_text, "Morgen bringe ich Muffins mit");
  assert.equal(request.html, "<p>Morgen bringe ich Muffins mit</p>");
  assert.deepEqual(request.recipients, ["team@firma.example", "anna@firma.example"]);
  await tick();
  assert.deepEqual(window.rcmailCalls, [["command", "send"]]);
});

test("roundcube: other commands pass through untouched", () => {
  const { window, sent } = loadAdapter("adapters/roundcube.js", ROUNDCUBE, {
    url: "https://webmail.example.de/",
    respond: () => ({}),
    beforeScripts: roundcubeWindow,
  });
  window.rcmail.command("savedraft");
  assert.deepEqual(window.rcmailCalls, [["command", "savedraft"]]);
  assert.equal(requests(sent).length, 0);
});

test("roundcube: discard empties the draft and leaves compose", async () => {
  const { window } = loadAdapter("adapters/roundcube.js", ROUNDCUBE, {
    url: "https://webmail.example.de/",
    respond: () => ({ action: "discard" }),
    beforeScripts: roundcubeWindow,
  });
  window.rcmail.command("send");
  await tick(); await tick();
  assert.deepEqual(window.rcmailCalls, [["set_content", ""], ["command", "list"]]);
  assert.equal(window.document.querySelector("[name=_subject]").value, "");
});

test("roundcube: plain text editor falls back correctly", async () => {
  const { window, sent } = loadAdapter("adapters/roundcube.js", ROUNDCUBE, {
    url: "https://webmail.example.de/",
    respond: () => ({ action: "cancel" }),
    beforeScripts: (w) => roundcubeWindow(w, { html: false }),
  });
  window.rcmail.command("send");
  await tick();
  assert.equal(requests(sent)[0].html, null);
});

test("roundcube: login page without rcmail does nothing", () => {
  const { window } = loadAdapter("adapters/roundcube.js", "<form id=login></form>", {
    url: "https://webmail.example.de/",
    respond: () => ({}),
    beforeScripts: (w) => { w.wrappedJSObject = w; },
  });
  assert.equal(window.KuchenmailAdapter, undefined);
});
