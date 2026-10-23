// Leitet Funde der Probe an den Spike-Host weiter, damit sie in ~/kuchenmail-spike.log landen.
const port = browser.runtime.connectNative("kuchenmail_spike");
port.onDisconnect.addListener(() => console.error("Spike-Host getrennt", port.error));
browser.runtime.onMessage.addListener((message, sender) => {
  port.postMessage({ ...message, url: sender.url });
});
