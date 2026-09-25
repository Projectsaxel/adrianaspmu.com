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

const LIMITS = { name: 120, email: 200, phone: 40, location: 80, interest: 60, message: 4000, source: 40 };

// De onde o lead veio. Allowlist e nao texto livre: "source" entra no
// assunto do e-mail, e assunto montado com string do cliente e injecao
// de cabecalho esperando acontecer.
const SOURCES = {
  "contact-page": "Contact page",
  "floating-button": "Floating button",
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

  const to = String(env.CONTACT_TO)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const cf = request.cf || {};
  const meta = [
    ["Came from", sourceLabel],
    ["Preferred location", location],
    ["Interested in", interest],
    ["Submitted from", page || "/contact/"],
    ["Visitor city", [cf.city, cf.region, cf.country].filter(Boolean).join(", ")],
    ["Received (UTC)", new Date().toISOString().replace("T", " ").slice(0, 19)],
  ].filter(([, v]) => v);

  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#222">
<h2 style="margin:0 0 4px">New contact form submission</h2>
<p style="margin:0 0 16px;color:#666">adrianaspmu.com &mdash; ${esc(sourceLabel)}</p>
<table cellpadding="6" style="border-collapse:collapse;font-size:15px">
<tr><td><strong>Name</strong></td><td>${esc(name)}</td></tr>
<tr><td><strong>Email</strong></td><td><a href="mailto:${esc(email)}">${esc(email)}</a></td></tr>
<tr><td><strong>Phone</strong></td><td><a href="tel:${esc(phone.replace(/[^\d+]/g, ""))}">${esc(phone)}</a></td></tr>
${meta.map(([k, v]) => `<tr><td><strong>${esc(k)}</strong></td><td>${esc(v)}</td></tr>`).join("")}
</table>
<h3 style="margin:20px 0 6px">Message</h3>
<div style="white-space:pre-wrap;border-left:3px solid #ddd;padding-left:12px">${esc(message) || "<em style='color:#888'>No message</em>"}</div>
<p style="margin-top:24px;color:#888;font-size:12px">Reply directly to this email to answer ${esc(name)}.</p>
</body></html>`;

  const text = [
    `New contact form submission - adrianaspmu.com [${sourceLabel}]`,
    "",
    `Name:  ${name}`,
    `Email: ${email}`,
    `Phone: ${phone}`,
    ...meta.map(([k, v]) => `${k}: ${v}`),
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
        subject: `[${sourceLabel}] New website inquiry: ${name}`,
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

  console.log(JSON.stringify({ event: "contact_sent", delivered, of: to.length, location }));
  return json({ ok: true });
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
