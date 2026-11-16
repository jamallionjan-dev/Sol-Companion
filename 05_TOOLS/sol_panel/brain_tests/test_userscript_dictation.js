// ChatGPT dictation through the userscript: mic button -> "submit dictation" -> text lands in the composer.
const { JSDOM } = require("jsdom");
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const dom = new JSDOM(`<body><main><div id="prompt-textarea" contenteditable="true"></div>
  <button aria-label="Dictate button" id="mic">mic</button></main></body>`, { url: "https://chatgpt.com/c/sol-1", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.localStorage.setItem("sollink_chat", "/c/sol-1");
Object.defineProperty(w.HTMLElement.prototype, "innerText", { get() { return this.textContent; } });
const cmds = ["dictate_start", null, null, "dictate_stop"]; let heard = null;
w.GM_xmlhttpRequest = (o) => setTimeout(() => {
  if (o.url.endsWith("/next")) { const c = cmds.length ? cmds.shift() : null; o.onload({ status: 200, responseText: JSON.stringify(c ? { id: 0, cmd: c } : { id: 0 }) }); }
  else if (o.url.endsWith("/heard")) { heard = JSON.parse(o.data); o.onload({ status: 200, responseText: "{}" }); }
}, 5);
let recording = false;
w.document.getElementById("mic").addEventListener("click", () => {
  recording = true;
  const sub = w.document.createElement("button"); sub.setAttribute("aria-label", "Submit dictation");
  sub.addEventListener("click", () => { recording = false; setTimeout(() => { w.document.getElementById("prompt-textarea").textContent = "ادخلي للداخل يا سول"; }, 800); });
  w.document.querySelector("main").appendChild(sub);
});
w.eval(src);
const t0 = Date.now();
const iv = setInterval(() => {
  if (heard || Date.now() - t0 > 25000) {
    clearInterval(iv);
    const ok = heard && heard.text === "ادخلي للداخل يا سول" && w.document.getElementById("prompt-textarea").textContent.trim() === "";
    console.log(ok ? "PASS dictation: mic clicked, submitted, text taken from the composer and the composer cleared" : "FAIL " + JSON.stringify(heard));
    process.exit(ok ? 0 : 1);
  }
}, 200);
