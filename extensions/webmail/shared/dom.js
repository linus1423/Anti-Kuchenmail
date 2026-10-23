// DOM-Hilfen für Gmail und Outlook: Senden-Buttons erkennen, Ereignisse abfangen
// und nach der Freigabe erneut auslösen.
"use strict";

// eslint-disable-next-line no-var
var KuchenmailDom = (() => {
  const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
  const RELEASE_MS = 1_500;

  function labelOf(el) {
    return [el.getAttribute("aria-label"), el.getAttribute("data-tooltip"), el.getAttribute("title")]
      .filter(Boolean)
      .join(" ")
      .trim();
  }

  function emailsIn(text) {
    return [...new Set((text || "").match(EMAIL) || [])].map((e) => e.toLowerCase());
  }

  // Erste Vorfahr-Ebene, die Mailtext UND Senden-Button enthält = der Entwurf
  function composeRoot(el, bodySelector, isSendButton) {
    for (let node = el; node && node !== document.documentElement; node = node.parentElement) {
      if (!node.querySelector || !node.querySelector(bodySelector)) continue;
      if ([...node.querySelectorAll("button, [role=button]")].some(isSendButton)) return node;
    }
    return null;
  }

  // Fängt Klick (inkl. mousedown/mouseup), Tastatur auf dem Button und Strg+Enter im Entwurf ab.
  function interceptSends({ isSendButton, bodySelector, onAttempt }) {
    let releasedUntil = 0;
    const released = () => Date.now() < releasedUntil;

    function stop(event) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }

    function buttonFrom(target) {
      const el = target instanceof Element ? target.closest("button, [role=button]") : null;
      return el && isSendButton(el) ? el : null;
    }

    for (const type of ["mousedown", "mouseup", "click", "pointerdown", "pointerup"]) {
      document.addEventListener(type, (event) => {
        if (released()) return;
        const button = buttonFrom(event.target);
        if (!button) return;
        stop(event);
        if (type === "click") {
          const root = composeRoot(button, bodySelector, isSendButton);
          onAttempt({ root, button });
        }
      }, true);
    }

    document.addEventListener("keydown", (event) => {
      if (released()) return;
      const button = buttonFrom(event.target);
      const onButton = button && (event.key === "Enter" || event.key === " ");
      const shortcut = event.key === "Enter" && (event.ctrlKey || event.metaKey);
      if (!onButton && !shortcut) return;
      const root = composeRoot(button || event.target, bodySelector, isSendButton);
      const inEditor = event.target instanceof Element &&
        (event.target.closest(bodySelector) || event.target.isContentEditable);
      if (!root && !button && !inEditor) return;
      // Ohne erkannten Entwurf trotzdem abfangen: der Ablauf blockiert dann (fail-closed)
      stop(event);
      onAttempt({ root, button });
    }, true);

    return {
      // Senden erneut auslösen; für kurze Zeit wird nichts abgefangen
      click(button) {
        releasedUntil = Date.now() + RELEASE_MS;
        for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup"]) {
          button.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
        }
        button.click();
      },
    };
  }

  return { labelOf, emailsIn, composeRoot, interceptSends };
})();
