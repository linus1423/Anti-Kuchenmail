// Lädt Hintergrundskripte einer Erweiterung in einen VM-Kontext mit gefälschter browser-API.
import { readFileSync } from "node:fs";
import vm from "node:vm";

export function event() {
  const listeners = [];
  return {
    listeners,
    addListener: (fn) => listeners.push(fn),
    removeListener: (fn) => listeners.splice(listeners.indexOf(fn), 1),
  };
}

// Falscher Native-Port: answer(message) liefert die Antwort des "Hosts" oder wirft.
export function fakeNative(answer) {
  const sent = [];
  return {
    sent,
    connectNative() {
      const onMessage = event();
      const onDisconnect = event();
      const port = {
        onMessage,
        onDisconnect,
        error: null,
        postMessage(message) {
          sent.push(message);
          Promise.resolve().then(() => {
            let response;
            try {
              response = answer(message);
            } catch (error) {
              port.error = { message: error.message };
              onDisconnect.listeners.forEach((fn) => fn(port));
              return;
            }
            if (response !== undefined) onMessage.listeners.forEach((fn) => fn({ ...response, id: message.id }));
          });
        },
      };
      return port;
    },
  };
}

export function loadScripts(files, browser, extra = {}) {
  const timers = [];
  const context = vm.createContext({
    browser,
    console: { log() {}, error() {}, warn() {} },
    setTimeout: (fn, ms) => { if (ms === 0) Promise.resolve().then(fn); return 1; },
    clearTimeout: () => {},
    setInterval: (fn) => { timers.push(fn); return 1; },
    Promise,
    ...extra,
  });
  for (const file of files) vm.runInContext(readFileSync(file, "utf8"), context, { filename: file });
  return { context, timers };
}
