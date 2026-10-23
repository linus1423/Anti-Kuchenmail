import { test } from "node:test";
import assert from "node:assert/strict";
import { event, fakeNative, loadScripts } from "./load-extension.mjs";

const DIR = new URL("../../extensions/thunderbird/", import.meta.url).pathname;

function setup(answer) {
  const native = fakeNative(answer);
  const calls = { notifications: [], removed: [], setDetails: [] };
  const browser = {
    runtime: { connectNative: native.connectNative },
    compose: {
      onBeforeSend: event(),
      setComposeDetails: async (id, d) => calls.setDetails.push([id, d]),
      getComposeDetails: async () => ({}),
    },
    tabs: { remove: async (id) => calls.removed.push(id) },
    windows: { getAll: async () => [] },
    notifications: { create: async (n) => calls.notifications.push(n) },
  };
  loadScripts([DIR + "native.js", DIR + "background.js"], browser);
  const send = (details) => browser.compose.onBeforeSend.listeners[0]({ id: 42 }, details);
  return { native, calls, send };
}

// Objekte aus dem VM-Kontext haben andere Prototypen; für Vergleiche in normale Objekte umwandeln
const plain = (value) => JSON.parse(JSON.stringify(value));
const tick = () => new Promise((r) => setImmediate(r));

const DETAILS = {
  subject: "Kuchen",
  plainTextBody: "Ich bringe morgen Kuchen mit",
  body: "<p>Ich bringe morgen Kuchen mit</p>",
  isPlainText: false,
  to: ["Team <team@firma.example>", { id: "abc", type: "mailingList" }],
  cc: "anna@firma.example",
  bcc: [],
};

test("sends draft to host and lets normal mail through", async () => {
  const { native, send } = setup((m) => (m.type === "ping" ? { ok: true } : { action: "send" }));
  assert.deepEqual(plain(await send(DETAILS)), { cancel: false });
  const request = native.sent.find((m) => m.type === "before_send");
  assert.equal(request.client, "thunderbird");
  assert.equal(request.html, DETAILS.body);
  assert.deepEqual(plain(request.recipients), ["team@firma.example", "list:abc", "anna@firma.example"]);
});

test("plain text mail sends no html", async () => {
  const { native, send } = setup(() => ({ action: "send" }));
  await send({ ...DETAILS, isPlainText: true });
  assert.equal(native.sent.find((m) => m.type === "before_send").html, null);
});

test("cancel keeps the draft open", async () => {
  const { calls, send } = setup(() => ({ action: "cancel" }));
  assert.deepEqual(plain(await send(DETAILS)), { cancel: true });
  await tick();
  assert.deepEqual(calls.removed, []);
});

test("discard cancels, empties and closes the draft", async () => {
  const { calls, send } = setup(() => ({ action: "discard" }));
  assert.deepEqual(plain(await send(DETAILS)), { cancel: true });
  await tick();
  await tick();
  assert.equal(calls.setDetails[0][1].body, "");
  assert.deepEqual(calls.removed, [42]);
});

test("fails closed when the host is missing", async () => {
  const { calls, send } = setup(() => {
    throw new Error("No such native application kuchenmail_guard");
  });
  assert.deepEqual(plain(await send(DETAILS)), { cancel: true });
  assert.match(calls.notifications.at(-1).title, /nicht erreichbar/);
});
