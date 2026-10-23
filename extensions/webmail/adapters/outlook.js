// Adapter für Outlook im Web (Microsoft 365 und Outlook.com), deutsche und englische Oberfläche.
// Selektoren gesammelt in SELECTORS.
"use strict";

(() => {
  const SELECTORS = {
    editable: "div[contenteditable=true][role=textbox]",
    subject: "input[aria-label*='Betreff' i], input[aria-label*='subject' i], " +
      "input[placeholder*='Betreff' i], input[placeholder*='subject' i]",
  };
  const BODY_LABEL = /(nachricht|message)/i;
  const RECIPIENT_LABEL = /^(an|to|cc|bcc)\b/i;
  const SEND_LABEL = /^(senden|send)\b/i;
  const NOT_SEND = /(später|later|weitere|more|planen|schedule)/i;
  const DISCARD_LABEL = /^(verwerfen|discard)\b/i;

  const { labelOf, emailsIn, interceptSends } = KuchenmailDom;

  function isSendButton(el) {
    const label = labelOf(el);
    return SEND_LABEL.test(label) && !NOT_SEND.test(label);
  }

  function isRecipientField(el) {
    return RECIPIENT_LABEL.test(el.getAttribute("aria-label") || "");
  }

  // Der Mailtext ist das editierbare Feld, das kein Empfängerfeld ist
  function findBody(root) {
    const editables = [...root.querySelectorAll(SELECTORS.editable)].filter((el) => !isRecipientField(el));
    return editables.find((el) => BODY_LABEL.test(el.getAttribute("aria-label") || "")) || editables[0] || null;
  }

  function recipientsOf(root) {
    const addresses = new Set();
    const fields = [...root.querySelectorAll("[aria-label]")].filter(isRecipientField);
    for (const field of fields) {
      const nodes = [field, ...field.querySelectorAll("*")];
      for (const node of nodes) {
        for (const value of [node.getAttribute("title"), node.getAttribute("aria-label")]) {
          emailsIn(value).forEach((e) => addresses.add(e));
        }
      }
      emailsIn(field.textContent).forEach((e) => addresses.add(e));
    }
    return [...addresses];
  }

  function readDraft(root) {
    const body = findBody(root);
    if (!body) return null;
    const subject = root.querySelector(SELECTORS.subject);
    return {
      subject: subject ? subject.value : "",
      plain_text: body.innerText ?? body.textContent ?? "",
      html: body.innerHTML,
      recipients: recipientsOf(root),
    };
  }

  function findButton(root, test) {
    return [...root.querySelectorAll("button, [role=button]")].find((el) => test(labelOf(el))) || null;
  }

  function discard(root) {
    const button = findButton(root, (label) => DISCARD_LABEL.test(label));
    if (button) {
      button.click();
      return;
    }
    const body = findBody(root);
    if (body) body.innerHTML = "";
  }

  function composeRoot(el) {
    // Ein Outlook-Entwurf enthält Text- und Empfängerfelder; der Mailtext allein reicht als Wurzel nicht
    for (let node = el; node && node !== document.documentElement; node = node.parentElement) {
      if (node.querySelector && findBody(node) && node.querySelector("button, [role=button]")) return node;
    }
    return null;
  }

  function context(root, button, interceptor) {
    return {
      key: root,
      readDraft: () => readDraft(root),
      resend: () => {
        const target = button || findButton(root, (label) => SEND_LABEL.test(label) && !NOT_SEND.test(label));
        if (target) interceptor.click(target);
      },
      discard: () => discard(root),
    };
  }

  const adapter = {
    client: "outlook",
    interceptor: null,
    install(onSendAttempt) {
      this.interceptor = interceptSends({
        isSendButton,
        bodySelector: SELECTORS.editable,
        onAttempt: ({ button }) => {
          const root = composeRoot(button || document.activeElement);
          if (!root) {
            onSendAttempt({ key: button || document, readDraft: () => null, resend() {}, discard() {} });
            return;
          }
          onSendAttempt(context(root, button, this.interceptor));
        },
      });
    },
    openDrafts() {
      const roots = new Set();
      for (const editable of document.querySelectorAll(SELECTORS.editable)) {
        if (isRecipientField(editable)) continue;
        const root = composeRoot(editable);
        if (root) roots.add(root);
      }
      return [...roots].map((root) => context(root, null, this.interceptor));
    },
    _readDraft: readDraft,
    _isSendButton: isSendButton,
    _composeRoot: composeRoot,
  };

  globalThis.KuchenmailAdapter = adapter;
  KuchenmailGuard.start(adapter);
})();
