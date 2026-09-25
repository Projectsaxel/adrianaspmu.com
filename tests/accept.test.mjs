import { readFileSync } from "fs";
const src = readFileSync("/Users/rachelbrum/Downloads/CLIENTES -MAC RACHEL/Adrianas PMU/site-repo/src/index.js","utf8");
// extrai as tres funcoes puras, sem precisar do runtime do Worker
const body = src.slice(src.indexOf("function parseAccept"), src.indexOf("function mdPathFor"));
const mdp  = src.slice(src.indexOf("function mdPathFor"), src.indexOf("function withVary"));
const { chooseFormat, mdPathFor } = await import(
  "data:text/javascript," + encodeURIComponent(body + mdp + "\nexport { chooseFormat, mdPathFor };")
);

const cases = [
  // [header, esperado, por que]
  [null,                                          "html",     "sem Accept, padrao HTML"],
  ["*/*",                                         "html",     "curinga total nao pede markdown"],
  ["text/html",                                   "html",     "navegador comum"],
  ["text/markdown",                               "markdown", "agente pedindo markdown"],
  ["text/markdown, text/html;q=0.9",              "markdown", "markdown com q maior"],
  ["text/html;q=1.0, text/markdown;q=0.9",        "html",     "HTML com q maior VENCE"],
  ["text/markdown;q=0.9, text/html;q=1.0",        "html",     "ordem nao importa, q importa"],
  ["text/markdown;q=0.5, text/html;q=0.5",        "html",     "empate resolve para HTML"],
  ["text/*",                                      "html",     "curinga de grupo cobre os dois, empate -> HTML"],
  ["text/markdown;q=0, text/html",                "html",     "q=0 descarta markdown"],
  ["application/json",                            "none",     "nenhum dos dois -> 406"],
  ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "html", "Accept real do Chrome"],
  ["text/markdown;q=1.0, text/html;q=0.1",        "markdown", "agente priorizando markdown"],
];
let fail = 0;
for (const [h, want, why] of cases) {
  const got = chooseFormat(h);
  const ok = got === want;
  if (!ok) fail++;
  console.log(`${ok ? "ok  " : "FALHA"} ${String(h).slice(0,52).padEnd(54)} -> ${got.padEnd(9)} ${why}`);
}
console.log();
const paths = [["/", "/content/index.md"], ["/aftercare/", "/content/aftercare/index.md"],
  ["/services/eyebrows/microblading/wilmington-ma/", "/content/services/eyebrows/microblading/wilmington-ma/index.md"],
  ["/404.html", "/content/404.md"], ["/sitemap.xml", null], ["/css/styles.css", null]];
for (const [p, want] of paths) {
  const got = mdPathFor(p);
  const ok = got === want;
  if (!ok) fail++;
  console.log(`${ok ? "ok  " : "FALHA"} ${p.padEnd(48)} -> ${got}`);
}
console.log(`\n${fail === 0 ? "TODOS OS TESTES PASSARAM" : fail + " FALHAS"}`);
process.exit(fail ? 1 : 0);
