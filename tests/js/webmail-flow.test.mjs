import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const FLOW = new URL("../../extensions/webmail/shared/flow.js", import.meta.url).pathname;

function setup(respond) {
  const sent = [];
  const context = vm.createContext({
    browser: {
      runtime: {
        sendMessage: async (m) => {
          sent.push(m);
          if (m.type === "notify") return { ok: true };
          return respond(m);
        },
      },
    },
    console: { error() {} },
    location: { hostname: "mail.example" },
    setInterval: () => 0,
  });
  vm.runInContext(readFileSync(FLOW, "utf8") + ";globalThis.KuchenmailGuard = KuchenmailGuard;", context);
  return { guard: context.KuchenmailGuard, sent };
}

function ctx(draft = { subject: "s", plain_text: "t", html: null, recipients: [] }) {
  const calls = [];
  return {
    calls,
    key: {},
    readDraft: () => draft,
    resend: () => calls.push("resend"),
    discard: () => calls.push("discard"),
  };
}

const adapter = { client: "gmail" };

test("send resends", async () => {
  const { guard, sent } = setup(() => ({ action: "send" }));
  const c = ctx();
  assert.equal(await guard.guardSend(adapter, c), "send");
  assert.deepEqual(c.calls, ["resend"]);
  assert.equal(sent[0].client, "gmail");
  assert.match(sent[0].draft_id, /^mail\.example-\d+$/);
});

test("cancel does nothing", async () => {
  const { guard } = setup(() => ({ action: "cancel" }));
  const c = ctx();
  assert.equal(await guard.guardSend(adapter, c), "cancel");
  assert.deepEqual(c.calls, []);
});

test("discard discards", async () => {
  const { guard } = setup(() => ({ action: "discard" }));
  const c = ctx();
  await guard.guardSend(adapter, c);
  assert.deepEqual(c.calls, ["discard"]);
});

test("host error blocks and notifies", async () => {
  const { guard, sent } = setup(() => ({ error: "No such native application" }));
  const c = ctx();
  assert.equal(await guard.guardSend(adapter, c), "error");
  assert.deepEqual(c.calls, []);
  assert.ok(sent.some((m) => m.type === "notify"));
});

test("unreadable draft blocks without asking the host", async () => {
  const { guard, sent } = setup(() => ({ action: "send" }));
  const c = ctx(null);
  assert.equal(await guard.guardSend(adapter, c), "unreadable");
  assert.equal(sent.filter((m) => m.type === "before_send").length, 0);
  assert.deepEqual(c.calls, []);
});

test("second attempt while the dialog is open is ignored", async () => {
  let release;
  const { guard } = setup(() => new Promise((resolve) => { release = resolve; }));
  const c = ctx();
  const first = guard.guardSend(adapter, c);
  assert.equal(await guard.guardSend(adapter, c), "busy");
  release({ action: "send" });
  assert.equal(await first, "send");
  assert.deepEqual(c.calls, ["resend"]);
});
