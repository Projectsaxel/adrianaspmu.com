#!/usr/bin/env node
/**
 * Injeta header e footer como HTML ESTATICO em todas as paginas, no build.
 *
 * Problema que resolve (auditoria 12/08, itens T1, T2 e T3):
 * o header e o footer so existiam via innerHTML no main.js. No HTML bruto
 * nao havia um unico link de navegacao, entao 9 paginas ficavam orfas e os
 * crawlers de IA (GPTBot, ClaudeBot, PerplexityBot), que nao executam JS,
 * enxergavam o site sem navegacao nenhuma.
 *
 * Como funciona, sem duplicar codigo e sem dependencia externa:
 * carrega js/site-config.js e js/main.js de verdade, dentro de um shim de
 * DOM minimo, e captura o innerHTML que o proprio main.js produziria no
 * navegador. Se o markup do menu mudar no main.js, isto acompanha sozinho.
 *
 * O main.js em producao detecta que o elemento ja tem conteudo e nao
 * reescreve: apenas liga os listeners. Zero mudanca de comportamento.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.dirname(__dirname);

function readAll(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    if ([".git", "node_modules", "scripts", "src", "docs", ".github"].includes(name)) continue;
    const fp = path.join(dir, name);
    const st = fs.statSync(fp);
    if (st.isDirectory()) readAll(fp, out);
    else if (name === "index.html") out.push(fp);
  }
  return out;
}

/** Shim de DOM: o minimo que renderHeader/renderFooter tocam. */
function makeSandbox(base) {
  const captured = {};
  const noopEl = {
    innerHTML: "",
    addEventListener() {},
    setAttribute() {},
    removeAttribute() {},
    classList: { toggle: () => false, add() {}, remove() {}, contains: () => false },
    querySelector: () => null,
    querySelectorAll: () => [],
    closest: () => null,
    textContent: "",
  };
  const makeSlot = (id) => ({
    ...noopEl,
    set innerHTML(v) { captured[id] = v; },
    get innerHTML() { return captured[id] || ""; },
    querySelector: () => null,
    querySelectorAll: () => [],
  });
  const slots = { "site-header": makeSlot("site-header"), "site-footer": makeSlot("site-footer") };

  const document = {
    documentElement: { dataset: { base } },
    getElementById: (id) => slots[id] || null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: (ev, fn) => { if (ev === "DOMContentLoaded") fn(); },
    readyState: "loading",
    createElement: () => ({ ...noopEl, style: {} }),
    body: { ...noopEl, appendChild() {} },
  };
  const window = {
    innerWidth: 1440,
    scrollY: 0,
    addEventListener() {},
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    location: { pathname: "/", href: "https://adrianaspmu.com/" },
  };
  return { sandbox: { document, window, console, navigator: { userAgent: "build" }, fetch: () => Promise.resolve() }, captured };
}

function renderFor(base) {
  const { sandbox, captured } = makeSandbox(base);
  const ctx = vm.createContext(sandbox);
  for (const f of ["js/site-config.js", "js/main.js"]) {
    vm.runInContext(fs.readFileSync(path.join(ROOT, f), "utf8"), ctx, { filename: f });
  }
  return captured;
}

function main() {
  const files = readAll(ROOT);
  const cache = new Map();
  let changed = 0;

  for (const fp of files) {
    let html = fs.readFileSync(fp, "utf8");
    const rel = path.relative(ROOT, fp).replace(/\\/g, "/");
    const depth = rel.split("/").length - 1;
    const base = depth === 0 ? "./" : "../".repeat(depth);

    if (!cache.has(base)) cache.set(base, renderFor(base));
    const { "site-header": header, "site-footer": footer } = cache.get(base);
    if (!header || !footer) {
      console.error(`static_nav: render vazio para base=${base}`);
      process.exit(1);
    }

    const before = html;
    // idempotente: so injeta quando a div esta vazia
    html = html.replace(
      /<div id="site-header"><\/div>/,
      `<div id="site-header">${header}</div>`
    );
    html = html.replace(
      /<div id="site-footer"><\/div>/,
      `<div id="site-footer">${footer}</div>`
    );
    if (html !== before) {
      fs.writeFileSync(fp, html);
      changed++;
    }
  }
  console.log(`static_nav: ${changed} paginas com header/footer estaticos`);
}

main();
