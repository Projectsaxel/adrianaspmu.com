/**
 * Worker do formulario de contato do adrianaspmu.com
 *
 * Roda APENAS em /api/* (ver "run_worker_first" no wrangler.jsonc).
 * Todo o resto do site continua sendo servido direto pelos assets
 * estaticos, sem invocar codigo, exatamente como antes.
 *
 * Envio por Resend, em conta propria da Adriana's PMU, com o dominio
 * adrianaspmu.com verificado. O Resend usa APENAS o subdominio send. e o
 * seletor resend._domainkey. O MX e o SPF do APEX nao sao usados nem
 * alterados: o e-mail da cliente continua inteiro na Nucleo.
 *
 * Variaveis (Worker > Settings > Variables and Secrets):
 *   RESEND_API_KEY   secret   chave da API do Resend
 *   CONTACT_TO       secret   destinatarios, separados por virgula
 *   CONTACT_FROM     secret   ex: Adriana's PMU Website <website@adrianaspmu.com>
 *   ALLOWED_ORIGINS  var      origens aceitas, separadas por virgula
 *   AUTOREPLY        var      "on" liga a confirmacao para a visitante
 *
 * CONTACT_TO e CONTACT_FROM sao secrets de proposito: o repositorio e
 * publico e e-mail em repositorio publico vira alvo de scraping de spam.
 */

const LIMITS = { name: 120, email: 200, phone: 40, location: 80, message: 4000 };

// Tempo minimo, em ms, entre a pagina carregar e o envio.
// Humano nao preenche nome, e-mail e telefone em menos de 3 segundos. Bot preenche.
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

  // Sem Origin: cai para o Referer. Navegador manda Origin em POST,
  // entao chegar aqui ja e sinal de cliente nao convencional.
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

  // Rate limit por IP. Binding nativo da Cloudflare, sem KV e sem estado proprio.
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

  // Honeypot. Campo escondido no HTML, invisivel para humano, preenchido por bot.
  // Responde 200 de proposito: bot que recebe erro tenta de novo, bot que recebe
  // sucesso vai embora satisfeito e a mensagem nao e enviada.
  if (clean(data.website, 200) !== "") {
    console.log(JSON.stringify({ event: "contact_spam", reason: "honeypot" }));
    return json({ ok: true });
  }

  const elapsed = Number(data.elapsed);
  if (!Number.isFinite(elapsed) || elapsed < MIN_FILL_MS) {
    console.log(JSON.stringify({ event: "contact_spam", reason: "too_fast", elapsed }));
    return json({ ok: true });
  }

  const name = clean(data.name, LIMITS.name);
  const email = clean(data.email, LIMITS.email);
  const phone = clean(data.phone, LIMITS.phone);
  const location = clean(data.location, LIMITS.location) || "Not specified";
  const message = clean(data.message, LIMITS.message);
  const page = clean(data.page, 200);

  const errors = [];
  if (name.length < 2) errors.push("Please enter your name.");
  if (!EMAIL_RE.test(email)) errors.push("Please enter a valid email address.");
  if (phone.replace(/\D/g, "").length < 10) errors.push("Please enter a valid phone number.");
  if (errors.length) {
    return json({ ok: false, error: errors.join(" ") }, 422);
  }

  // Falta de configuracao tem que falhar alto. O bug que este Worker corrige
  // era exatamente o oposto: dizer "obrigado" sem ter enviado nada.
  const missing = ["RESEND_API_KEY", "CONTACT_TO", "CONTACT_FROM"].filter((k) => !env[k]);
  if (missing.length) {
    console.error(JSON.stringify({ event: "contact_misconfigured", missing }));
    return json({ ok: false, error: FALLBACK }, 503);
  }

  const to = String(env.CONTACT_TO)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const cf = request.cf || {};
  const meta = [
    ["Preferred location", location],
    ["Submitted from", page || "/contact/"],
    ["Visitor city", [cf.city, cf.region, cf.country].filter(Boolean).join(", ")],
    ["Received (UTC)", new Date().toISOString().replace("T", " ").slice(0, 19)],
  ].filter(([, v]) => v);

  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#222">
<h2 style="margin:0 0 4px">New contact form submission</h2>
<p style="margin:0 0 16px;color:#666">adrianaspmu.com</p>
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
    "New contact form submission - adrianaspmu.com",
    "",
    `Name:  ${name}`,
    `Email: ${email}`,
    `Phone: ${phone}`,
    ...meta.map(([k, v]) => `${k}: ${v}`),
    "",
    "Message:",
    message || "(no message)",
  ].join("\n");

  let res;
  try {
    res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: env.CONTACT_FROM,
        to,
        reply_to: email,
        subject: `New website inquiry: ${name} (${location})`,
        html,
        text,
      }),
    });
  } catch (err) {
    console.error(JSON.stringify({ event: "contact_send_network_error", error: String(err) }));
    return json({ ok: false, error: FALLBACK }, 502);
  }

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    console.error(
      JSON.stringify({ event: "contact_send_failed", status: res.status, detail: detail.slice(0, 500) }),
    );
    return json({ ok: false, error: FALLBACK }, 502);
  }

  const sent = await res.json().catch(() => ({}));
  console.log(JSON.stringify({ event: "contact_sent", id: sent.id || null, location }));

  // Auto-reply para a visitante. DESLIGADO por padrao: ligue trocando a var
  // AUTOREPLY para "on" no wrangler.jsonc, depois de validar o fluxo basico.
  //
  // Roda DEPOIS da notificacao e nunca altera a resposta ao navegador. O lead
  // ja chegou nas tres caixas; se a confirmacao falhar, isso e um problema de
  // cortesia, nao de captacao, e nao pode virar erro na tela da visitante.
  if (String(env.AUTOREPLY || "").toLowerCase() === "on") {
    const task = sendAutoReply(env, { name, email, location, to });
    if (ctx && typeof ctx.waitUntil === "function") ctx.waitUntil(task);
    else await task;
  }

  return json({ ok: true });
}

async function sendAutoReply(env, { name, email, location, to }) {
  const WILMINGTON = "(781) 853-8063";
  const SALEM = "(978) 223-7496";
  const FRESHA =
    "https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/all-offer?share=true&pId=727586";

  const first = esc(String(name).split(/\s+/)[0] || "there");

  const html = `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;color:#222;line-height:1.6">
<p>Hi ${first},</p>
<p>Thank you for reaching out to Adriana's Permanent Makeup. We received your message and one of us will get back to you shortly.</p>
<p>If you would rather not wait, you can book your appointment online or call the studio directly:</p>
<p>
  <a href="${FRESHA}" style="display:inline-block;background:#222;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">Book online</a>
</p>
<table cellpadding="0" cellspacing="0" style="font-size:15px;margin-top:8px">
  <tr><td style="padding:6px 24px 6px 0"><strong>Wilmington, MA</strong><br>211 Lowell Street, Suite F<br><a href="tel:+17818538063">${WILMINGTON}</a></td>
      <td style="padding:6px 0"><strong>Salem, NH</strong><br>117A Main Street<br><a href="tel:+19782237496">${SALEM}</a></td></tr>
</table>
<p style="color:#666;font-size:14px">Mon to Sat, 10:00 AM to 6:00 PM. Closed Sunday.</p>
<p style="color:#888;font-size:12px;margin-top:24px">This is an automatic confirmation. Replying to it reaches our team directly.</p>
</body></html>`;

  const text = [
    `Hi ${String(name).split(/\s+/)[0] || "there"},`,
    "",
    "Thank you for reaching out to Adriana's Permanent Makeup. We received your",
    "message and one of us will get back to you shortly.",
    "",
    `Book online: ${FRESHA}`,
    "",
    `Wilmington, MA - 211 Lowell Street, Suite F - ${WILMINGTON}`,
    `Salem, NH - 117A Main Street - ${SALEM}`,
    "Mon to Sat, 10:00 AM to 6:00 PM. Closed Sunday.",
    "",
    "This is an automatic confirmation. Replying to it reaches our team directly.",
  ].join("\n");

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.RESEND_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        from: env.CONTACT_FROM,
        to: [email],
        // Resposta da visitante cai numa caixa lida de verdade, nao no remetente.
        reply_to: to[0],
        subject: "We received your message - Adriana's Permanent Makeup",
        html,
        text,
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      console.error(
        JSON.stringify({
          event: "autoreply_failed",
          status: res.status,
          detail: detail.slice(0, 300),
        }),
      );
      return;
    }
    const body = await res.json().catch(() => ({}));
    console.log(JSON.stringify({ event: "autoreply_sent", id: body.id || null, location }));
  } catch (err) {
    console.error(JSON.stringify({ event: "autoreply_error", error: String(err) }));
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname !== "/api/contact") {
      return json({ ok: false, error: "Not found" }, 404);
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
