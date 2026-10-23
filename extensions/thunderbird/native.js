// Verbindung zum lokalen Guard-Host über Native Messaging.
// Jede Anfrage bekommt eine id, die Antwort wird darüber zugeordnet.
"use strict";

const GUARD_HOST = "kuchenmail_guard";

class GuardConnection {
  constructor() {
    this.port = null;
    this.nextId = 1;
    this.pending = new Map();
  }

  connect() {
    const port = browser.runtime.connectNative(GUARD_HOST);
    port.onMessage.addListener((message) => {
      const entry = this.pending.get(message.id);
      if (entry) {
        this.pending.delete(message.id);
        entry.resolve(message);
      }
    });
    port.onDisconnect.addListener((p) => {
      const reason = (p && p.error && p.error.message) || "Verbindung zum Guard-Host getrennt";
      console.error("Kuchenmail-Guard:", reason);
      if (this.port === port) this.port = null;
      for (const entry of this.pending.values()) entry.reject(new Error(reason));
      this.pending.clear();
    });
    this.port = port;
  }

  ask(message, timeoutMs) {
    return new Promise((resolve, reject) => {
      if (!this.port) this.connect();
      const id = this.nextId++;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error("Guard-Host antwortet nicht"));
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (value) => { clearTimeout(timer); resolve(value); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      });
      try {
        this.port.postMessage({ ...message, id });
      } catch (error) {
        this.pending.get(id)?.reject(error);
        this.pending.delete(id);
      }
    });
  }
}
