// The userscript against a ChatGPT-like page: a persistent "Stop" button (read aloud) that fooled v1.0,
// a reply that streams in over a few seconds, then stays.
const { JSDOM } = require("jsdom");
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const dom = new JSDOM(`<body><main>
  <article><div data-message-author-role="user">hi</div></article>
  <article><div data-message-author-role="assistant">old reply</div><button aria-label="Stop reading">x</button></article>
  <div id="prompt-textarea" contenteditable="true"></div><button data-testid="send-button">send</button></main></body>`,
  { url: "https://chatgpt.com/c/sol-1", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.localStorage.setItem("sollink_chat", "/c/sol-1");
let served = false, posted = null;
w.GM_xmlhttpRequest = (o) => {
  setTimeout(() => {
    if (o.url.endsWith("/next")) { const d = served ? { id: 0 } : { id: 7, text: "ادخلي للداخل", speak: false }; served = true; o.onload({ status: 200, responseText: JSON.stringify(d) }); }
    else if (o.url.endsWith("/reply")) { posted = JSON.parse(o.data); o.onload({ status: 200, responseText: "{}" }); }
  }, 5);
};
// clicking send makes ChatGPT "stream" a reply: new article, text grows for ~2 s, then the stop button goes away
w.document.querySelector('[data-testid="send-button"]').addEventListener("click", () => {
  const art = w.document.createElement("article");
  const msg = w.document.createElement("div"); msg.setAttribute("data-message-author-role", "assistant"); art.appendChild(msg);
  w.document.querySelector("main").appendChild(art);
  const stop = w.document.createElement("button"); stop.setAttribute("data-testid", "stop-button"); w.document.body.appendChild(stop);
  const parts = ["تمام جمال،", " دخلت", " للداخل", " باتجاه غرفة المعيشة."]; let i = 0;
  const iv = w.setInterval(() => { msg.textContent += parts[i++]; if (i >= parts.length) { w.clearInterval(iv); stop.remove(); } }, 500);
});
Object.defineProperty(w.HTMLElement.prototype, "innerText", { get() { return this.textContent; } });
w.eval(src);
const start = Date.now();
const iv = setInterval(() => {
  if (posted || Date.now() - start > 20000) {
    clearInterval(iv);
    const ok = posted && posted.id === 7 && posted.text === "تمام جمال، دخلت للداخل باتجاه غرفة المعيشة.";
    console.log(ok ? "PASS reply detected despite a persistent 'Stop' button, full text after streaming" : "FAIL " + JSON.stringify(posted));
    process.exit(ok ? 0 : 1);
  }
}, 200);
