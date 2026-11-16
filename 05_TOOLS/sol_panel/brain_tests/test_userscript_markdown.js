// The page as Firefox showed it (2026-10-24): no data-message-author-role, no <article>; replies inside .markdown.
const { JSDOM } = require("jsdom");
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const dom = new JSDOM(`<body><main>
  <section><div class="user-bubble">hi</div></section>
  <section><div class="markdown prose">old reply</div><button aria-label="Stop reading">x</button></section>
  <div id="prompt-textarea" contenteditable="true"></div><button data-testid="send-button">send</button></main></body>`,
  { url: "https://chatgpt.com/c/sol-1", runScripts: "outside-only", pretendToBeVisual: true });
const w = dom.window;
w.localStorage.setItem("sollink_chat", "/c/sol-1");
Object.defineProperty(w.HTMLElement.prototype, "innerText", { get() { return this.textContent; } });
let served = false, posted = null;
w.GM_xmlhttpRequest = (o) => setTimeout(() => {
  if (o.url.endsWith("/next")) { const d = served ? { id: 0 } : { id: 9, text: "مرحبا", speak: false }; served = true; o.onload({ status: 200, responseText: JSON.stringify(d) }); }
  else if (o.url.endsWith("/reply")) { posted = JSON.parse(o.data); o.onload({ status: 200, responseText: "{}" }); }
}, 5);
w.document.querySelector('[data-testid="send-button"]').addEventListener("click", () => {
  const sec = w.document.createElement("section"); const md = w.document.createElement("div"); md.className = "markdown prose"; sec.appendChild(md);
  w.document.querySelector("main").appendChild(sec);
  const parts = ["مرحبا جمال،", " أنا هنا معك."]; let i = 0;
  const iv = w.setInterval(() => { md.textContent += parts[i++]; if (i >= parts.length) w.clearInterval(iv); }, 500);
});
w.eval(src);
const t0 = Date.now();
const iv = setInterval(() => {
  if (posted || Date.now() - t0 > 20000) {
    clearInterval(iv);
    const ok = posted && posted.id === 9 && posted.text === "مرحبا جمال، أنا هنا معك.";
    console.log(ok ? "PASS reply found inside .markdown on a page without role attributes or articles" : "FAIL " + JSON.stringify(posted));
    process.exit(ok ? 0 : 1);
  }
}, 200);
