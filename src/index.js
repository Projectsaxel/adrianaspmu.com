/**
 * Worker do formulario de contato do adrianaspmu.com
 *
 * Roda APENAS em /api/* (ver "run_worker_first" no wrangler.jsonc).
 * Todo o resto do site continua sendo servido direto pelos assets.
 *
 * ENVIO: binding nativo send_email do Cloudflare Email Service.
 * Zero servico de terceiro. Enviar para enderecos de destino
 * VERIFICADOS da conta e gratuito em qualquer plano e nao conta
 * em cota nenhuma (docs: email-service/platform/limits).
 * A unica exigencia: o remetente pertence ao dominio de routing.
 *
 * Por que o Resend saiu: ele so seria necessario para enviar a
 * DESTINATARIO ARBITRARIO (a confirmacao para a visitante), que
 * estava desligada de qualquer jeito. Manter era pagar em
 * complexidade (conta, chave, DNS, rotacao) por um recurso morto.
 *
 * Variaveis:
 *   EMAIL       binding  send_email (wrangler.jsonc)
 *   CONTACT_TO  secret   destinatarios, separados por virgula.
 *                        Secret e nao var: o repo e publico e
 *                        e-mail em repo publico vira alvo de spam.
 *   CONTACT_FROM var     website@adrianaspmu.com (dominio de routing)
 */

const LIMITS = { lead_path: 90, name: 120, email: 200, phone: 40, location: 80, interest: 60, message: 4000, source: 40 };

// De onde o lead veio. Allowlist e nao texto livre: "source" entra no
// assunto do e-mail, e assunto montado com string do cliente e injecao
// de cabecalho esperando acontecer.
const SOURCES = {
  "contact-page": "Contact page",
  "floating-button": "Floating button",
  "academy-class": "Home announcement (Academy enrollment)",
};
const SOURCE_DEFAULT = "contact-page";

// Humano nao preenche nome, e-mail e telefone em menos de 3s. Bot preenche.
const MIN_FILL_MS = 3000;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;

const FALLBACK =
  "We could not send your message. Please call Wilmington (781) 853-8063 or Salem (978) 223-7496.";

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex",
    },
  });
}

function esc(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

function clean(value, max) {
  return String(value ?? "")
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, "")
    .trim()
    .slice(0, max);
}

function originAllowed(request, env) {
  const allowed = String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  if (allowed.length === 0) return true;

  const origin = request.headers.get("origin");
  if (origin) return allowed.includes(origin);

  const referer = request.headers.get("referer");
  if (!referer) return false;
  try {
    return allowed.includes(new URL(referer).origin);
  } catch {
    return false;
  }
}

/* ---------------------------------------------------------------
 * Filtro de oferta/spam (10/10/2026)
 *
 * O spam que chega NAO e robo: e gente oferecendo SEO, trafego ou
 * "mais alunos", de fora dos EUA ou de servidor, digitando no formulario
 * de verdade. Honeypot, tempo minimo e captcha nao pegam isso. O que
 * separa e o conteudo: cliente pergunta de horario, preco e procedimento;
 * spam oferece servico.
 *
 * Pontuacao (3 ou mais = filtrado):
 *   +2 enviado de fora dos EUA
 *   +3 telefone que ja foi usado em spam
 *   +2 link na mensagem
 *   +1 por expressao de oferta (maximo 4)
 *
 * Filtrado NAO e descartado: vai so para a Axel (SPAM_TO_DEFAULT), com [FILTERED]
 * no assunto, e nao para a Adriana. Se aparecer cliente real ali, a
 * regra e ajustada. A visitante ve o "Thank you" normal e o GA4 nao conta
 * como lead (o main.js le "filtered").
 * --------------------------------------------------------------- */

const SPAM_PHONES = new Set(["3072076448"]);
const SPAM_TO_DEFAULT = "info@axelseo.com";

const PITCH = [
  /\bseo\b/i,
  /search engine|google search|first page|page one of google|higher on google|rank(ing|ings)?\b/i,
  /\btraffic\b/i,
  /backlink|guest post/i,
  /(website|site) audit|audit of your|improvements? (for|to) your (site|website)/i,
  /digital marketing|marketing (agency|services|plan)|social media (management|marketing)/i,
  /web ?design|redesign|app development|wordpress develop/i,
  /\bleads?\b.*\b(generat|more)|more (clients|customers|students|leads|patients)/i,
  /student base|client base|customer base|(connect|provide) you with/i,
  /expand(ing)? your|grow (your|traffic)|scale your/i,
  /competitors/i,
  /unsubscribe|reply stop|opt[- ]out/i,
  /cost[- ]effective|affordable package|free (seo|review|audit|quote|consultation for your)/i,
  /\bi (help|specialize|work with) (businesses|business|companies|brands)/i,
  /\bwe can (place|help your business|get your)/i,
  /\bpartnership\b|\bcollaborat/i,
];

function spamCheck({ message, phone, country }) {
  const reasons = [];
  let score = 0;
  if (country && country !== "US") {
    score += 2;
    reasons.push("sent from outside the US (" + country + ")");
  }
  const digits = phone.replace(/\D/g, "").replace(/^1(?=\d{10}$)/, "");
  if (SPAM_PHONES.has(digits)) {
    score += 3;
    reasons.push("phone number used in earlier spam");
  }
  if (/https?:\/\/|www\.|\b[a-z0-9-]+\.(com|net|io|co|org)\/\S*/i.test(message)) {
    score += 2;
    reasons.push("link in the message");
  }
  const hits = PITCH.filter((re) => re.test(message)).length;
  if (hits) {
    score += Math.min(hits, 4);
    reasons.push(hits + " sales-pitch expression(s)");
  }
  return { spam: score >= 3, score, reasons };
}

/* ---------------------------------------------------------------
 * Origem do lead (07/10/2026)
 *
 * O analytics.js manda o cookie pmu_attr cru (primeiro toque e ultimo
 * toque nao-direto, mesmo modelo do GA4) e as paginas vistas na visita.
 * A classificacao e feita AQUI, num lugar so, e o que vai para o assunto
 * do e-mail e sempre um rotulo fixo desta tabela, nunca texto do cliente.
 *
 * Pago x organico e o ponto: a Adriana paga Google Ads, entao o lead que
 * veio da ficha do Google, da busca organica ou do ChatGPT precisa chegar
 * marcado como ORGANICO para nao ser creditado ao anuncio.
 *
 * Ficha do Google: o Google manda a visita da ficha com referrer
 * google.com, igual a busca organica. So da para separar se o link do
 * site na ficha tiver utm_campaign comecando com "gbp" (ex.:
 * ?utm_source=google&utm_medium=organic&utm_campaign=gbp-wilmington).
 * --------------------------------------------------------------- */

const PAID_MEDIUM = /^(cpc|ppc|paid|paidsearch|paid[-_ ]?social|paid[-_ ]?search|display|cpm|ads?)$/i;
const AI_SOURCE = /(chatgpt|openai|perplexity|gemini|copilot|claude|anthropic)/i;
const SEARCH_SOURCE = /^(google|bing|yahoo|duckduckgo|ecosia|brave|baidu|yandex|aol|ask)$/i;
const SOCIAL_SOURCE = /(instagram|facebook|^ig$|^fb$|meta|tiktok|pinterest|youtube|linkedin|threads|reddit|snapchat|twitter)/i;

const AI_NAMES = [
  [/chatgpt|openai/i, "ChatGPT"],
  [/perplexity/i, "Perplexity"],
  [/gemini/i, "Google Gemini"],
  [/copilot/i, "Microsoft Copilot"],
  [/claude|anthropic/i, "Claude"],
];

function attrField(v, max) {
  return clean(v, max).replace(/[\r\n\t]+/g, " ").replace(/[<>"'`]/g, "");
}

function safePath(v) {
  const p = clean(v, 120);
  return /^\/(?!\/)[\w\-./%~]*$/.test(p) ? p : "";
}

/** Le um toque do cookie e devolve so campos conhecidos e limpos. */
function readTouch(t) {
  if (!t || typeof t !== "object") return null;
  const touch = {
    s: attrField(t.s, 100).toLowerCase(),
    m: attrField(t.m, 100).toLowerCase(),
    c: attrField(t.c, 150),
    t: attrField(t.t, 150),
    k: ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "ttclid"].includes(t.k) ? t.k : "",
    r: attrField(t.r, 80).toLowerCase(),
    lp: safePath(t.lp),
    ts: Number.isFinite(Number(t.ts)) ? Number(t.ts) : 0,
  };
  return touch.s ? touch : null;
}

/**
 * Rotulo do canal. type: PAID | ORGANIC | DIRECT | REFERRAL.
 * channel e detail sao sempre texto fixo daqui, seguros para o assunto.
 */
function classifyTouch(t) {
  if (!t || t.s === "(direct)") {
    return { type: "DIRECT", channel: "Direct", detail: "Typed the address, saved bookmark, or a link from a text/email/app" };
  }
  const { s, m, c, k } = t;
  const camp = c.toLowerCase();

  // Pago primeiro: click id do Google ou medium de anuncio.
  if (k === "gclid" || k === "gbraid" || k === "wbraid" || (s === "google" && PAID_MEDIUM.test(m))) {
    return { type: "PAID", channel: "Google Ads", detail: "Clicked a paid Google ad" };
  }
  if (k === "msclkid" || (s === "bing" && PAID_MEDIUM.test(m))) {
    return { type: "PAID", channel: "Microsoft Ads", detail: "Clicked a paid Bing ad" };
  }
  if (PAID_MEDIUM.test(m)) {
    if (SOCIAL_SOURCE.test(s)) return { type: "PAID", channel: "Meta Ads (Facebook/Instagram)", detail: "Clicked a paid social ad" };
    return { type: "PAID", channel: "Paid ad", detail: "Clicked a paid ad" };
  }

  // Ficha do Google: so reconhecivel pelo utm do link da ficha.
  if (camp.startsWith("gbp") || m === "gbp" || s === "gbp") {
    const unit = /salem/.test(camp) ? " - Salem" : /wilmington/.test(camp) ? " - Wilmington" : "";
    return { type: "ORGANIC", channel: "Google Business Profile" + unit, detail: "Clicked the website button on the Google Maps / Business listing" };
  }

  if (AI_SOURCE.test(s) || AI_SOURCE.test(t.r) || m === "ai_referral") {
    const hit = AI_NAMES.find(([re]) => re.test(s) || re.test(t.r));
    return { type: "ORGANIC", channel: "AI assistant: " + (hit ? hit[1] : "other"), detail: "An AI assistant recommended or linked the site" };
  }

  if (SEARCH_SOURCE.test(s) && (m === "organic" || m === "(not set)" || m === "referral")) {
    const name = s === "google" ? "Google Search" : s.charAt(0).toUpperCase() + s.slice(1) + " Search";
    return { type: "ORGANIC", channel: name, detail: "Found the site in the regular, unpaid search results" };
  }

  if (SOCIAL_SOURCE.test(s) || m === "social") {
    const net = /insta|^ig$/.test(s) ? "Instagram" : /face|^fb$|meta/.test(s) ? "Facebook" : /tiktok/.test(s) ? "TikTok" : "Social media";
    return { type: "ORGANIC", channel: net, detail: "Came from a post, profile or bio link, not an ad" };
  }

  if (m === "email") return { type: "ORGANIC", channel: "Email", detail: "Clicked a link in an email" };

  return { type: "REFERRAL", channel: "Another website", detail: "Followed a link from another site" };
}

const TYPE_LABEL = {
  PAID: "PAID",
  ORGANIC: "ORGANIC",
  DIRECT: "DIRECT",
  REFERRAL: "REFERRAL",
};
const TYPE_COLOR = { PAID: "#b45309", ORGANIC: "#15803d", DIRECT: "#475569", REFERRAL: "#1d4ed8" };

function fmtDate(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString().slice(0, 10);
}

/** Monta a origem do lead a partir do payload. Nunca lanca. */
function leadOrigin(raw) {
  const a = raw && typeof raw === "object" ? raw : {};
  const last = readTouch(a.last);
  const first = readTouch(a.first);
  const path = (Array.isArray(a.path) ? a.path : []).slice(-15).map(safePath).filter(Boolean);

  if (!last && !first) {
    return { known: false, type: "UNKNOWN", channel: "Not recorded", rows: [], path };
  }
  const main = last || first;
  const cls = classifyTouch(main);
  const rows = [
    ["Lead type", TYPE_LABEL[cls.type]],
    ["Channel", cls.channel],
    ["What that means", cls.detail],
    ["Arrived on page", main.lp],
  ];
  if (cls.type === "REFERRAL") rows.push(["Referring site", main.r || main.s]);
  if (cls.type === "PAID") {
    if (main.c && main.c !== "(not set)") rows.push(["Ad campaign", main.c]);
    if (main.t) rows.push(["Ad keyword", main.t]);
  }
  if (first && last && (first.s !== last.s || first.m !== last.m || first.c !== last.c)) {
    const fc = classifyTouch(first);
    rows.push([
      "First found us",
      `${fc.channel} (${TYPE_LABEL[fc.type]})` + (first.lp ? ` on ${first.lp}` : "") + (first.ts ? `, ${fmtDate(first.ts)}` : ""),
    ]);
  }
  rows.push(["Raw source / medium", `${main.s} / ${main.m || "(none)"}` + (main.c && main.c !== "(not set)" ? ` / ${main.c}` : "")]);
  return { known: true, type: cls.type, channel: cls.channel, rows: rows.filter(([, v]) => v), path };
}

async function handleContact(request, env, ctx) {
  if (!originAllowed(request, env)) {
    return json({ ok: false, error: FALLBACK }, 403);
  }

  if (env.CONTACT_LIMITER) {
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const { success } = await env.CONTACT_LIMITER.limit({ key: `contact:${ip}` });
    if (!success) {
      return json(
        { ok: false, error: "Too many submissions. Please wait a minute and try again." },
        429,
      );
    }
  }

  let data;
  try {
    data = await request.json();
  } catch {
    return json({ ok: false, error: FALLBACK }, 400);
  }

  // Honeypot. Responde 200 de proposito: bot que recebe sucesso
  // vai embora satisfeito e a mensagem nao e enviada.
  if (clean(data.website, 200) !== "") {
    console.log(JSON.stringify({ event: "contact_spam", reason: "honeypot" }));
    return json({ ok: true });
  }

  // Rapido demais: responde ERRO, nao sucesso. Era { ok: true } silencioso,
  // e uma pessoa com autofill via "Thank you!", o GA4 contava o lead e o
  // e-mail nunca saia. O main.js ja espera os 3s antes de enviar, entao
  // isto so dispara para quem posta direto no endpoint.
  const elapsed = Number(data.elapsed);
  if (!Number.isFinite(elapsed) || elapsed < MIN_FILL_MS) {
    console.log(JSON.stringify({ event: "contact_spam", reason: "too_fast", elapsed }));
    return json({ ok: false, error: "Please wait a moment and send your message again." }, 422);
  }

  const name = clean(data.name, LIMITS.name);
  const email = clean(data.email, LIMITS.email);
  const phone = clean(data.phone, LIMITS.phone);
  const location = clean(data.location, LIMITS.location) || "Not specified";
  // Interesse (servico ou curso da Academy). Allowlist: entra no e-mail.
  const INTERESTS = {
    service: "A permanent makeup service",
    "pmu-100h-fundamental": "100-Hour Fundamental course",
    "pmu-apprenticeship": "Apprenticeship",
    "vip-masterclass": "VIP Masterclass",
    "not-sure": "Not sure yet",
  };
  const interestKey = clean(data.interest, LIMITS.interest);
  const interest = Object.prototype.hasOwnProperty.call(INTERESTS, interestKey) ? INTERESTS[interestKey] : "Not specified";
  const message = clean(data.message, LIMITS.message);
  const page = clean(data.page, 200);
  // Caminho ate o lead de curso: etapas separadas por " > ", cada uma de
  // uma allowlist (entra no e-mail). Ex.: "academy-announcement >
  // course-announcement" vira "Academy page card, then Course page card".
  const LEAD_STEPS = {
    "home-announcement": "Home announcement",
    "academy-announcement": "Academy page card",
    "course-announcement": "Course page card",
    "course-page": "Course page",
    "contact-page": "Contact page",
  };
  const leadPathKey = clean(data.lead_path, LIMITS.lead_path);
  const steps = leadPathKey ? leadPathKey.split(" > ") : [];
  const leadPath =
    steps.length && steps.length <= 3 && steps.every((k) => Object.prototype.hasOwnProperty.call(LEAD_STEPS, k))
      ? steps.map((k) => LEAD_STEPS[k]).join(", then ") + (steps.length === 1 && steps[0].endsWith("-announcement") ? ", directly" : "")
      : "";

  const sourceKey = clean(data.source, LIMITS.source);
  const source = Object.prototype.hasOwnProperty.call(SOURCES, sourceKey)
    ? sourceKey
    : SOURCE_DEFAULT;
  const sourceLabel = SOURCES[source];

  const errors = [];
  if (name.length < 2) errors.push("Please enter your name.");
  if (!EMAIL_RE.test(email)) errors.push("Please enter a valid email address.");
  if (phone.replace(/\D/g, "").length < 10) errors.push("Please enter a valid phone number.");
  // No botao flutuante os quatro campos sao obrigatorios. Na pagina de
  // contato a mensagem segue opcional, para nao mudar o que ja funciona.
  if (source === "floating-button" && message.length < 2) {
    errors.push("Please tell us what you are looking for.");
  }
  if (errors.length) {
    return json({ ok: false, error: errors.join(" ") }, 422);
  }

  // Falta de configuracao falha ALTO. O bug que este Worker corrige
  // era exatamente o oposto: dizer "obrigado" sem ter enviado nada.
  if (!env.EMAIL || !env.CONTACT_TO || !env.CONTACT_FROM) {
    console.error(
      JSON.stringify({
        event: "contact_misconfigured",
        missing: [
          !env.EMAIL && "EMAIL binding",
          !env.CONTACT_TO && "CONTACT_TO",
          !env.CONTACT_FROM && "CONTACT_FROM",
        ].filter(Boolean),
      }),
    );
    return json({ ok: false, error: FALLBACK }, 503);
  }


  const origin = leadOrigin(data.attribution);
  const check = spamCheck({ message, phone, country: (request.cf || {}).country || "" });
  // Filtrado vai so para a Axel. SPAM_TO (secret) sobrepoe o padrao, que
  // e o endereco publico da agencia e ja e destino verificado do CONTACT_TO.
  const to = String(check.spam ? env.SPAM_TO || SPAM_TO_DEFAULT : env.CONTACT_TO)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const cf = request.cf || {};
  const meta = [
    ["Came from", sourceLabel],
    ["Preferred location", location],
    ["Interested in", interest],
    ["Lead path", leadPath],
    ["Submitted from", page || "/contact/"],
    ["Visitor city", [cf.city, cf.region, cf.country].filter(Boolean).join(", ")],
    ["Received (UTC)", new Date().toISOString().replace("T", " ").slice(0, 19)],
  ].filter(([, v]) => v);

  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#222">
${check.spam ? `<p style="margin:0 0 12px;padding:8px 12px;background:#fef3c7;border-left:4px solid #b45309"><strong>Filtered as a sales pitch / spam</strong> (score ${check.score}): ${esc(check.reasons.join("; "))}. Sent only to the Axel team, not to Adriana. If this is a real client, forward it and tell us.</p>` : ""}
<h2 style="margin:0 0 4px">New contact form submission</h2>
<p style="margin:0 0 16px;color:#666">adrianaspmu.com &mdash; ${esc(sourceLabel)}</p>
<table cellpadding="6" style="border-collapse:collapse;font-size:15px">
<tr><td><strong>Name</strong></td><td>${esc(name)}</td></tr>
<tr><td><strong>Email</strong></td><td><a href="mailto:${esc(email)}">${esc(email)}</a></td></tr>
<tr><td><strong>Phone</strong></td><td><a href="tel:${esc(phone.replace(/[^\d+]/g, ""))}">${esc(phone)}</a></td></tr>
${meta.map(([k, v]) => `<tr><td><strong>${esc(k)}</strong></td><td>${esc(v)}</td></tr>`).join("")}
</table>
<h3 style="margin:20px 0 6px">How this person found Adriana's</h3>
${origin.known
    ? `<p style="margin:0 0 8px"><span style="display:inline-block;padding:3px 10px;border-radius:4px;color:#fff;font-weight:700;background:${TYPE_COLOR[origin.type]}">${esc(origin.type)}</span> <strong>${esc(origin.channel)}</strong></p>
<table cellpadding="6" style="border-collapse:collapse;font-size:15px">
${origin.rows.slice(1).map(([k, v]) => `<tr><td><strong>${esc(k)}</strong></td><td>${esc(v)}</td></tr>`).join("")}
${origin.path.length ? `<tr><td><strong>Pages viewed before contacting</strong></td><td>${origin.path.map(esc).join(" &rarr; ")}</td></tr>` : ""}
</table>`
    : `<p style="margin:0;color:#888">Not recorded (cookies blocked, or the form was sent before tracking loaded).</p>`}
<h3 style="margin:20px 0 6px">Message</h3>
<div style="white-space:pre-wrap;border-left:3px solid #ddd;padding-left:12px">${esc(message) || "<em style='color:#888'>No message</em>"}</div>
<p style="margin-top:24px;color:#888;font-size:12px">Reply directly to this email to answer ${esc(name)}.</p>
</body></html>`;

  const text = [
    ...(check.spam ? [`FILTERED AS SALES PITCH / SPAM (score ${check.score}): ${check.reasons.join("; ")}`, ""] : []),
    `New contact form submission - adrianaspmu.com [${sourceLabel}]`,
    "",
    `Name:  ${name}`,
    `Email: ${email}`,
    `Phone: ${phone}`,
    ...meta.map(([k, v]) => `${k}: ${v}`),
    "",
    "HOW THIS PERSON FOUND ADRIANA'S",
    ...(origin.known
      ? [...origin.rows.map(([k, v]) => `${k}: ${v}`), ...(origin.path.length ? [`Pages viewed before contacting: ${origin.path.join(" > ")}`] : [])]
      : ["Not recorded"]),
    "",
    "Message:",
    message || "(no message)",
  ].join("\n");

  // Um envio por destinatario. O binding aceita um "to" por chamada
  // e cada envio para destino verificado e gratuito. Se UM falhar,
  // os outros dois ainda recebem, e o erro so vai para a visitante
  // se NENHUM envio sair.
  const results = await Promise.allSettled(
    to.map((rcpt) =>
      env.EMAIL.send({
        to: rcpt,
        from: env.CONTACT_FROM,
        reply_to: email,
        subject: `${check.spam ? "[FILTERED] " : ""}[${!origin.known ? sourceLabel : origin.type === "DIRECT" ? "DIRECT" : `${origin.type} - ${origin.channel}`}] New website inquiry: ${name}`,
        html,
        text,
      }),
    ),
  );

  const delivered = results.filter((r) => r.status === "fulfilled").length;
  const failed = results
    .map((r, i) => (r.status === "rejected" ? { to: to[i], error: String(r.reason) } : null))
    .filter(Boolean);

  if (failed.length) {
    console.error(JSON.stringify({ event: "contact_send_partial", delivered, failed }));
  }
  if (delivered === 0) {
    return json({ ok: false, error: FALLBACK }, 502);
  }

  console.log(JSON.stringify({ event: "contact_sent", delivered, of: to.length, location, lead_type: origin.type, channel: origin.channel, filtered: check.spam, spam_score: check.score }));
  return json(check.spam ? { ok: true, filtered: true } : { ok: true });
}

/* ---------------------------------------------------------------
 * Negociacao de conteudo: Accept: text/markdown
 *
 * Padrao: acceptmarkdown.com, que cobra tres coisas do servidor:
 *   1. servir markdown quando o cliente pede text/markdown
 *   2. mandar "Vary: Accept" em TODA variante, inclusive na HTML,
 *      senao a CDN cacheia uma e entrega para quem pediu a outra
 *   3. respeitar q-values (RFC 9110), para que
 *      "text/html;q=1.0, text/markdown;q=0.9" continue recebendo HTML
 *
 * Os gemeos .md sao gerados no build por scripts/gen_markdown.py e
 * vivem em /content/<caminho>/index.md. Nada e convertido em runtime.
 * --------------------------------------------------------------- */

const VARY = "Accept, Accept-Encoding";

/** Parseia o header Accept em pares {type, q}, ordenados por q desc. */
function parseAccept(header) {
  if (!header) return [];
  return header
    .split(",")
    .map((part) => {
      const [raw, ...params] = part.trim().split(";");
      let q = 1;
      for (const p of params) {
        const m = /^\s*q=([0-9.]+)\s*$/i.exec(p);
        if (m) {
          const v = parseFloat(m[1]);
          if (!Number.isNaN(v)) q = v;
        }
      }
      return { type: raw.trim().toLowerCase(), q };
    })
    .filter((e) => e.type && e.q > 0)
    .sort((a, b) => b.q - a.q);
}

/** Peso do Accept para um media type, considerando curingas. */
function qFor(entries, type) {
  const [group] = type.split("/");
  let best = -1;
  for (const e of entries) {
    if (e.type === type || e.type === group + "/*" || e.type === "*/*") {
      if (e.q > best) best = e.q;
    }
  }
  return best;
}

/**
 * Decide o formato: "markdown", "html" ou "none" (406).
 * Sem header Accept, ou com curinga total, o padrao e HTML.
 */
function chooseFormat(header) {
  const entries = parseAccept(header);
  if (entries.length === 0) return "html";
  const md = qFor(entries, "text/markdown");
  const html = qFor(entries, "text/html");
  if (md < 0 && html < 0) return "none";
  return md > html ? "markdown" : "html";
}

/** /servicos/ -> /content/servicos/index.md ; / -> /content/index.md */
function mdPathFor(pathname) {
  let p = pathname;
  if (p.endsWith("/")) p += "index.html";
  if (!p.endsWith(".html")) return null;
  return "/content" + p.slice(0, -".html".length) + ".md";
}

function withVary(res, extra) {
  const h = new Headers(res.headers);
  h.set("vary", VARY);
  if (extra) for (const [k, v] of Object.entries(extra)) h.set(k, v);
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}

const NOT_FOUND_MD = `# 404 — Page Not Found

This URL does not exist on adrianaspmu.com.

Where to look next:

- Sitemap: https://adrianaspmu.com/sitemap.xml
- Agent guide: https://adrianaspmu.com/llms.txt
- All services and prices: https://adrianaspmu.com/services/
- Studios: https://adrianaspmu.com/locations/
- Aftercare and contraindications: https://adrianaspmu.com/aftercare/
- Contact: https://adrianaspmu.com/contact/

Adriana's Permanent Makeup — Wilmington, MA (781) 853-8063 and Salem, NH (978) 223-7496.
`;

/**
 * Rota de pagina: termina em "/" ou ".html", ou nao tem extensao
 * (/about, que o asset server manda para /about/). So estas negociam
 * formato. Imagem, CSS, JS, sitemap, robots e llms.txt sao servidos direto:
 * antes um Accept: image/webp ou text/css recebia 406.
 */
function isPageRoute(pathname) {
  if (pathname.endsWith("/") || pathname.endsWith(".html")) return true;
  const last = pathname.split("/").pop();
  return !last.includes(".");
}

/**
 * O asset server responde 307 para URL sem barra (/about -> /about/).
 * 307 e temporario e nao consolida canonical: vira 301.
 */
function permanentSlash(res, url) {
  if (res.status !== 307) return res;
  const loc = res.headers.get("location");
  if (!loc) return res;
  const to = new URL(loc, url);
  if (to.origin === url.origin && to.pathname === url.pathname + "/") {
    const h = new Headers(res.headers);
    h.set("vary", VARY);
    return new Response(null, { status: 301, headers: h });
  }
  return res;
}

const isRedirect = (s) => s >= 300 && s < 400;

async function serveNegotiated(request, env) {
  const url = new URL(request.url);

  // Gemeos markdown acessados direto: servem, mas nao indexam e apontam o
  // canonical para a pagina HTML (para arquivo que nao e HTML o canonical
  // vai no header Link).
  if (url.pathname.startsWith("/content/") && url.pathname.endsWith(".md")) {
    const res = await env.ASSETS.fetch(request);
    if (res.status !== 200) return res;
    let page = url.pathname.slice("/content".length, -".md".length);
    page = page.endsWith("/index") ? page.slice(0, -"index".length) : page + "/";
    return withVary(res, {
      "content-type": "text/markdown; charset=utf-8",
      "x-robots-tag": "noindex",
      link: `<${url.origin}${page}>; rel="canonical"`,
    });
  }

  if (!isPageRoute(url.pathname)) {
    const res = await env.ASSETS.fetch(request);
    if (res.status === 404) {
      const page = await env.ASSETS.fetch(new URL("/404.html", url));
      return new Response(page.body, {
        status: 404,
        headers: { "content-type": "text/html; charset=utf-8", vary: VARY },
      });
    }
    return res;
  }

  const format = chooseFormat(request.headers.get("accept"));

  // Redirect vale para qualquer formato: antes, com Accept: text/markdown,
  // as 118 regras do _redirects e as URLs sem barra davam 404.
  const res = await env.ASSETS.fetch(request);
  if (isRedirect(res.status)) return withVary(permanentSlash(res, url));

  if (format === "none") {
    return new Response("Not Acceptable. This resource is available as text/html or text/markdown.\n", {
      status: 406,
      headers: { "content-type": "text/plain; charset=utf-8", vary: VARY },
    });
  }

  if (format === "markdown") {
    const md = mdPathFor(url.pathname);
    if (md) {
      const hit = await env.ASSETS.fetch(new Request(new URL(md, url), request));
      if (hit.status === 200) {
        return withVary(hit, { "content-type": "text/markdown; charset=utf-8" });
      }
    }
    // Pagina existe mas nao tem gemeo: entrega o HTML, nao um 404 falso.
    if (res.status === 200) return withVary(res);
    return new Response(NOT_FOUND_MD, {
      status: 404,
      headers: { "content-type": "text/markdown; charset=utf-8", vary: VARY },
    });
  }

  if (res.status === 404) {
    const page = await env.ASSETS.fetch(new URL("/404.html", url));
    return new Response(page.body, {
      status: 404,
      headers: { "content-type": "text/html; charset=utf-8", vary: VARY },
    });
  }
  return withVary(res);
}

/* Avaliacoes do Google (25/09/2026). O GitHub Actions grava o JSON a cada
   3 dias na branch reviews-data do repositorio (publico); o Worker so le e
   guarda 1h em cache. Sem segredo nenhum no Worker. Se a branch falhar, cai
   no data/reviews.json que foi publicado no ultimo deploy. */
const REVIEWS_URL =
  "https://raw.githubusercontent.com/Projectsaxel/adrianaspmu.com/reviews-data/reviews.json";

async function serveReviews(request, env, url) {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "public, max-age=3600",
    "x-robots-tag": "noindex",
  };
  try {
    const r = await fetch(REVIEWS_URL, { cf: { cacheTtl: 3600, cacheEverything: true } });
    if (r.ok) {
      const body = await r.text();
      JSON.parse(body); // so repassa se for JSON valido
      return new Response(body, { status: 200, headers });
    }
  } catch (e) {
    console.log(JSON.stringify({ event: "reviews_fallback", error: String(e).slice(0, 120) }));
  }
  const local = await env.ASSETS.fetch(new Request(new URL("/data/reviews.json", url), request));
  if (local.ok) return new Response(local.body, { status: 200, headers });
  return new Response('{"units":{},"reviews":{},"selection":{}}', { status: 200, headers });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/api/reviews") {
      return serveReviews(request, env, url);
    }
    if (url.pathname !== "/api/contact") {
      return serveNegotiated(request, env);
    }
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: { allow: "POST, OPTIONS" } });
    }
    if (request.method !== "POST") {
      return json({ ok: false, error: "Method not allowed" }, 405);
    }

    return handleContact(request, env, ctx);
  },
};
