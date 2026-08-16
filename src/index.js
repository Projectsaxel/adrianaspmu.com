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

const LIMITS = { name: 120, email: 200, phone: 40, location: 80, message: 4000 };

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
        subject: `New website inquiry: ${name} (${location})`,
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
