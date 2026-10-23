"use strict";

const list = document.getElementById("origins");
const message = document.getElementById("message");

function show(text, isError = false) {
  message.textContent = text;
  message.className = isError ? "error" : "";
}

function toOrigin(value) {
  const url = new URL(value.trim());
  if (url.protocol !== "https:" && url.protocol !== "http:") throw new Error("nur http(s)-Adressen");
  return url.origin;
}

async function load() {
  const { roundcubeOrigins = [] } = await browser.storage.local.get("roundcubeOrigins");
  return roundcubeOrigins;
}

async function render() {
  list.replaceChildren();
  for (const origin of await load()) {
    const item = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = origin;
    const remove = document.createElement("button");
    remove.textContent = "Entfernen";
    remove.addEventListener("click", async () => {
      const origins = (await load()).filter((o) => o !== origin);
      await browser.storage.local.set({ roundcubeOrigins: origins });
      await browser.permissions.remove({ origins: [`${origin}/*`] }).catch(() => {});
      render();
    });
    item.append(label, remove);
    list.append(item);
  }
}

document.getElementById("add").addEventListener("submit", async (event) => {
  event.preventDefault();
  let origin;
  try {
    origin = toOrigin(document.getElementById("url").value);
  } catch (error) {
    show(`Ungültige Adresse: ${error.message}`, true);
    return;
  }
  // Muss direkt aus dem Klick heraus passieren, sonst lehnt Firefox die Anfrage ab
  const granted = await browser.permissions.request({ origins: [`${origin}/*`] });
  if (!granted) {
    show("Ohne Berechtigung kann die Erweiterung diese Seite nicht schützen.", true);
    return;
  }
  const origins = await load();
  if (!origins.includes(origin)) origins.push(origin);
  await browser.storage.local.set({ roundcubeOrigins: origins });
  document.getElementById("url").value = "";
  show(`${origin} wird geschützt. Offene Roundcube-Tabs bitte neu laden.`);
  render();
});

render();
