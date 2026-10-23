// Adapter für Gmail (mail.google.com). Selektoren gesammelt in SELECTORS,
// damit Änderungen an Gmail nur hier nachgezogen werden müssen.
"use strict";

(() => {
  const SELECTORS = {
    body: "div[contenteditable=true][role=textbox]",
    subject: "input[name=subjectbox]",
    recipientChips: "[email], [data-hovercard-id]",
    recipientInputs: "input[type=text], input:not([type])",
    discard: "[role=button][data-tooltip^='Entwurf verwerfen'], [role=button][aria-label^='Entwurf verwerfen'], " +
      "[role=button][data-tooltip^='Discard draft'], [role=button][aria-label^='Discard draft']",
  };
  const SEND_LABEL = /^(senden|send)\b/i;
  const NOT_SEND = /(planen|schedule|weitere|more|später|later)/i;

  const { labelOf, emailsIn, interceptSends } = KuchenmailDom;

  function isSendButton(el) {
    const label = labelOf(el);
    return SEND_LABEL.test(label) && !NOT_SEND.test(label);
  }

  function findSendButton(root) {
    return [...root.querySelectorAll("[role=button], button")].find(isSendButton) || null;
  }

  function readDraft(root) {
    const body = root.querySelector(SELECTORS.body);
    if (!body) return null;
    const addresses = new Set();
    for (const chip of root.querySelectorAll(SELECTORS.recipientChips)) {
      for (const value of [chip.getAttribute("email"), chip.getAttribute("data-hovercard-id")]) {
        emailsIn(value).forEach((e) => addresses.add(e));
      }
    }
    for (const input of root.querySelectorAll(SELECTORS.recipientInputs)) {
      if (input.matches(SELECTORS.subject)) continue;
      emailsIn(input.value).forEach((e) => addresses.add(e));
    }
    const subject = root.querySelector(SELECTORS.subject);
    return {
      subject: subject ? subject.value : "",
      plain_text: body.innerText ?? body.textContent ?? "",
      html: body.innerHTML,
      recipients: [...addresses],
    };
  }

  function discard(root) {
    const button = root.querySelector(SELECTORS.discard);
    if (button) {
      button.click();
      return;
    }
    const body = root.querySelector(SELECTORS.body);
    if (body) body.innerHTML = "";
  }

  function context(root, button, interceptor) {
    return {
      key: root,
      readDraft: () => readDraft(root),
      resend: () => {
        const target = button || findSendButton(root);
        if (target) interceptor.click(target);
      },
      discard: () => discard(root),
    };
  }

  const adapter = {
    client: "gmail",
    interceptor: null,
    install(onSendAttempt) {
      this.interceptor = interceptSends({
        isSendButton,
        bodySelector: SELECTORS.body,
        onAttempt: ({ root, button }) => {
          if (!root) {
            onSendAttempt({ key: button, readDraft: () => null, resend() {}, discard() {} });
            return;
          }
          onSendAttempt(context(root, button, this.interceptor));
        },
      });
    },
    openDrafts() {
      const roots = [...document.querySelectorAll(SELECTORS.body)]
        .map((body) => KuchenmailDom.composeRoot(body, SELECTORS.body, isSendButton))
        .filter(Boolean);
      return [...new Set(roots)].map((root) => context(root, null, this.interceptor));
    },
    // für Tests
    _readDraft: readDraft,
    _isSendButton: isSendButton,
  };

  globalThis.KuchenmailAdapter = adapter;
  KuchenmailGuard.start(adapter);
})();
