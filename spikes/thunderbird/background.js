// Spike: Hält jeden Versand 30 s an, protokolliert die Compose-Details über den
// Spike-Host und bricht ab, wenn der Betreff "SPIKE-CANCEL" enthält.
const HOLD_SECONDS = 30;

function ask(port, message) {
  return new Promise((resolve) => {
    const onMessage = (response) => {
      port.onMessage.removeListener(onMessage);
      resolve(response);
    };
    port.onMessage.addListener(onMessage);
    port.postMessage(message);
  });
}

const port = browser.runtime.connectNative("kuchenmail_spike");
port.onDisconnect.addListener(() => console.error("Spike-Host getrennt", port.error));

browser.compose.onBeforeSend.addListener(async (tab, details) => {
  const started = Date.now();
  await ask(port, {
    type: "before_send",
    client: "thunderbird",
    subject: details.subject,
    to: details.to,
    cc: details.cc,
    bcc: details.bcc,
    isPlainText: details.isPlainText,
    plainTextBody: details.plainTextBody,
    body: details.body,
  });
  await ask(port, { type: "hold", seconds: HOLD_SECONDS });
  const waited = Math.round((Date.now() - started) / 1000);
  const cancel = (details.subject || "").includes("SPIKE-CANCEL");
  await ask(port, { type: "result", waited, cancel });
  return { cancel };
});
