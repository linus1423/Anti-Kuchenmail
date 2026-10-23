// Adapter für Roundcube (selbst gehostet, Adressen in den Einstellungen der Erweiterung).
// Statt Klicks abzufangen wird rcmail.command('send') umhüllt: darüber läuft jeder Versand,
// egal ob Button, Menü oder Tastenkürzel, und unabhängig vom Skin.
"use strict";

(() => {
  const page = window.wrappedJSObject;
  const rcmail = page && page.rcmail;
  if (!rcmail || typeof rcmail.command !== "function") return;

  const { emailsIn } = KuchenmailDom;
  const original = rcmail.command;
  let released = false;

  // Objekte, die an Seitenfunktionen gehen, müssen in den Seitenkontext geklont werden
  const forPage = (value) => (typeof cloneInto === "function" ? cloneInto(value, page) : value);

  function field(name) {
    const el = document.querySelector(`[name="${name}"]`);
    return el ? el.value || "" : "";
  }

  function readDraft() {
    const isCompose = rcmail.env && rcmail.env.action === "compose";
    if (!isCompose) return null;
    let plain = null;
    let html = null;
    const editor = rcmail.editor;
    try {
      if (editor && typeof editor.get_content === "function") {
        plain = String(editor.get_content(forPage({ nosig: true, format: "text" })) ?? "");
        if (typeof editor.is_html === "function" && editor.is_html()) {
          html = String(editor.get_content(forPage({ nosig: true })) ?? "");
        }
      }
    } catch (error) {
      console.error("Kuchenmail-Guard: Roundcube-Editor nicht lesbar", error);
    }
    if (plain === null) {
      const textarea = document.querySelector("textarea[name=_message]");
      if (!textarea) return null;
      plain = textarea.value;
    }
    return {
      subject: field("_subject"),
      plain_text: plain,
      html,
      recipients: ["_to", "_cc", "_bcc"].flatMap((name) => emailsIn(field(name))),
    };
  }

  function callOriginal(args) {
    released = true;
    try {
      return Reflect.apply(original, rcmail, args);
    } finally {
      released = false;
    }
  }

  function discard() {
    try {
      if (rcmail.editor && typeof rcmail.editor.set_content === "function") rcmail.editor.set_content("");
    } catch (error) {
      console.error("Kuchenmail-Guard: Roundcube-Editor nicht leerbar", error);
    }
    const textarea = document.querySelector("textarea[name=_message]");
    if (textarea) textarea.value = "";
    const subject = document.querySelector("[name=_subject]");
    if (subject) subject.value = "";
    callOriginal(["list"]);
  }

  const ctx = { key: document, readDraft, discard, resend: null };

  const adapter = {
    client: "roundcube",
    install(onSendAttempt) {
      rcmail.command = exportFunction(function (command, ...rest) {
        if (command === "send" && !released) {
          const args = [command, ...rest];
          onSendAttempt({ ...ctx, resend: () => callOriginal(args) });
          return false;
        }
        return Reflect.apply(original, this, [command, ...rest]);
      }, page);
    },
    openDrafts() {
      return rcmail.env && rcmail.env.action === "compose" ? [{ ...ctx, resend() {} }] : [];
    },
    _readDraft: readDraft,
  };

  globalThis.KuchenmailAdapter = adapter;
  KuchenmailGuard.start(adapter);
})();
