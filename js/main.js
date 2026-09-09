(function () {
  "use strict";

  const root = document.documentElement;
  const base = root.dataset.base || "/";

  function resolvePath(href) {
    if (href.startsWith("http") || href.startsWith("#")) return href;
    if (href.startsWith("/")) return base.replace(/\/?$/, "/") + href.slice(1);
    return href;
  }

  function renderNavItem(item) {
    if (item.children) {
      const sub = item.children
        .map((c) => {
          if (c.children) {
            const nested = c.children
              .map((n) => `<li><a href="${resolvePath(n.href)}">${n.label}</a></li>`)
              .join("");
            return `<li><a href="${resolvePath(c.href)}"><strong>${c.label}</strong></a><ul>${nested}</ul></li>`;
          }
          return `<li><a href="${resolvePath(c.href)}">${c.label}</a></li>`;
        })
        .join("");
      const parent = item.href
        ? `<a href="${resolvePath(item.href)}" class="nav-parent">${item.label}</a>`
        : `<span class="nav-parent nav-parent--static">${item.label}</span>`;
      return `<li class="has-submenu">
        <div class="nav-item-row">
          ${parent}
          <button type="button" class="submenu-toggle" aria-expanded="false" aria-label="Show ${item.label} submenu">
            <span class="submenu-chevron" aria-hidden="true"></span>
          </button>
        </div>
        <ul class="submenu">${sub}</ul>
      </li>`;
    }
    return `<li><a href="${resolvePath(item.href)}">${item.label}</a></li>`;
  }

  function renderHeader() {
    const el = document.getElementById("site-header");
    if (!el || typeof NAV === "undefined") return;

    const navItems = NAV.map(renderNavItem).join("");
    const home = resolvePath("/");
    const logoSrc = resolvePath((typeof SITE !== "undefined" && SITE.logo) || "/assets/images/logo.svg");

    // Se o build ja injetou o header como HTML estatico (scripts/static_nav.js),
    // nao reescreve: so liga os listeners abaixo. Isso mantem a navegacao
    // visivel para crawlers e para GPTBot/ClaudeBot, que nao executam JS.
    if (!el.innerHTML.trim()) el.innerHTML = `
      <div class="promo-banner">
        <a href="${resolvePath("/payment-plan/")}">Split your service into 4 interest-free payments with Cherry &mdash; see your options</a>
      </div>
      <header class="site-header">
        <div class="container header-inner">
          <a class="logo" href="${home}" aria-label="Adriana's PMU Home">
            <img class="logo-img" src="${logoSrc}" alt="Adriana's Permanent Makeup" width="254" height="66" decoding="async">
          </a>
          <button class="nav-toggle" type="button" aria-label="Open menu" aria-expanded="false">☰</button>
          <nav class="main-nav" aria-label="Main navigation">
            <ul>${navItems}</ul>
          </nav>
          <div class="header-cta">
            <a class="btn btn-ghost header-call" href="tel:+17818538063" aria-label="Call the studio">Call</a>
            <a class="btn btn-primary" href="${resolvePath("/contact/")}">Book Consultation</a>
          </div>
        </div>
      </header>`;

    const toggle = el.querySelector(".nav-toggle");
    const nav = el.querySelector(".main-nav");
    toggle?.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open);
    });

    el.querySelectorAll(".submenu-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (window.innerWidth > 900) return;
        const li = btn.closest(".has-submenu");
        if (!li) return;
        const expanded = !li.classList.contains("is-expanded");
        el.querySelectorAll(".has-submenu.is-expanded").forEach((other) => {
          other.classList.remove("is-expanded");
          other.querySelector(".submenu-toggle")?.setAttribute("aria-expanded", "false");
        });
        if (expanded) {
          li.classList.add("is-expanded");
          btn.setAttribute("aria-expanded", "true");
        } else {
          li.classList.remove("is-expanded");
          btn.setAttribute("aria-expanded", "false");
        }
      });
    });

    // O header e o mesmo HTML em todas as paginas (injetado no build).
    // Em pagina de Salem, o botao Call precisa tocar em Salem, senao a
    // visitante liga para a unidade errada.
    if (String(window.location.pathname).indexOf("salem") > -1) {
      const call = el.querySelector(".header-call");
      if (call) call.setAttribute("href", "tel:+19782237496");
    }

    const header = el.querySelector(".site-header");
    if (header) {
      const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 12);
      onScroll();
      window.addEventListener("scroll", onScroll, { passive: true });
    }
  }

  function renderFooter() {
    const el = document.getElementById("site-footer");
    if (!el || typeof SITE === "undefined") return;

    const w = SITE.locations.wilmington;
    const s = SITE.locations.salem;
    const p = SITE.locations.peabody;

    if (el.innerHTML.trim()) return;   // ja injetado no build
    el.innerHTML = `
      <footer class="site-footer">
        <div class="container">
          <div class="footer-grid">
            <div>
              <h4>${SITE.name}</h4>
              <p>Master Permanent Makeup Artist with ${SITE.stats.years} experience and ${SITE.stats.procedures} procedures performed.</p>
              <p>Women-owned · LGBTQ+ friendly · Wheelchair accessible (Wilmington)</p>
            </div>
            <div>
              <h4>Services</h4>
              <ul>
                <li><a href="${resolvePath("/services/eyebrows/")}">Eyebrow PMU</a></li>
                <li><a href="${resolvePath("/services/lips/")}">Lip PMU</a></li>
                <li><a href="${resolvePath("/services/eyeliner/")}">Eyeliner PMU</a></li>
                <li><a href="${resolvePath("/services/combos/")}">Combo Packages</a></li>
                <li><a href="${resolvePath("/academy/")}">PMU Academy</a></li>
                <li><a href="${resolvePath("/payment-plan/")}">Payment Plans</a></li>
              </ul>
            </div>
            <div>
              <h4>Locations</h4>
              <ul>
                <li><a href="${resolvePath("/locations/")}">All Locations</a></li>
                <li><a href="${resolvePath("/locations/wilmington-ma/")}">Wilmington, MA</a></li>
                <li><a href="${resolvePath("/locations/salem-nh/")}">Salem, NH</a></li>
                <li><a href="${resolvePath("/contact/")}">Contact</a></li>
                <li><a href="${resolvePath("/faq/")}">FAQ</a></li>
              </ul>
            </div>
            <div class="footer-nap">
              <h4>Wilmington, MA</h4>
              <p>${w.street}, ${w.city}, ${w.region} ${w.zip}<br>
              <a href="tel:+17818538063">${w.phone}</a></p>
              <h4>Salem, NH</h4>
              <p>${s.street}, ${s.city}, ${s.region} ${s.zip}<br>
              <a href="tel:+19782237496">${s.phone}</a></p>
              <h4>Academy — Peabody, MA</h4>
              <p>${p.street}, ${p.city}, ${p.region} ${p.zip}<br>
              <a href="tel:+17818538063">${p.phone}</a></p>
            </div>
          </div>
          <div class="footer-bottom">
            <p>© ${new Date().getFullYear()} ${SITE.legalName}. All rights reserved.</p>
            <p>
              <a href="${resolvePath("/privacy-policy/")}">Privacy</a> ·
              <a href="${resolvePath("/terms-of-use/")}">Terms</a> ·
              <a href="${SITE.instagram}" rel="noopener">Instagram</a> ·
              <a href="${SITE.facebook}" rel="noopener">Facebook</a>
            </p>
          </div>
        </div>
      </footer>`;
  }

  function initFaq() {
    document.querySelectorAll(".faq-item button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const item = btn.closest(".faq-item");
        const open = item.classList.toggle("is-open");
        btn.setAttribute("aria-expanded", open);
      });
    });
  }

  function initReviewsNav() {
    const prev = document.querySelector("[data-reviews-prev]");
    const next = document.querySelector("[data-reviews-next]");
    const track = document.querySelector(".reviews-track");
    if (!track) return;
    const scroll = (dir) => track.scrollBy({ left: dir * 340, behavior: "smooth" });
    prev?.addEventListener("click", () => scroll(-1));
    next?.addEventListener("click", () => scroll(1));
  }

  function initContactForm() {
    const form = document.getElementById("contact-form");
    if (!form) return;

    const msg = form.querySelector(".form-message");
    const button = form.querySelector('button[type="submit"]');
    const buttonLabel = button ? button.textContent : "";
    const loadedAt = Date.now();

    const PHONES =
      "Please call Wilmington (781) 853-8063 or Salem (978) 223-7496.";

    function show(text, ok) {
      if (!msg) return;
      msg.textContent = text;
      msg.hidden = false;
      msg.classList.toggle("form-message--ok", !!ok);
      msg.classList.toggle("form-message--error", !ok);
    }

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      if (button) {
        button.disabled = true;
        button.textContent = "Sending...";
      }
      show("Sending your message...", true);

      const payload = Object.fromEntries(new FormData(form).entries());
      payload.elapsed = Date.now() - loadedAt;
      payload.page = window.location.pathname;

      let ok = false;
      let text = "We could not send your message. " + PHONES;

      try {
        const res = await fetch("/api/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const body = await res.json().catch(() => ({}));

        if (res.ok && body.ok) {
          ok = true;
          text =
            "Thank you! We received your message and will contact you shortly. For faster booking, use Fresha or call our studios.";
        } else if (body.error) {
          text = body.error;
        }
      } catch (err) {
        text = "Network error. " + PHONES;
      }

      show(text, ok);
      if (ok) {
        // Lead so conta depois que o Worker confirmou o envio. Contar no
        // submit inflaria o numero com tentativas que nunca chegaram.
        window.PMU_track?.formSubmitContact?.(payload.location);
        form.reset();
      }

      if (button) {
        button.disabled = false;
        button.textContent = buttonLabel;
      }
    });
  }

  /**
   * Contato flutuante: botao fixo no canto inferior direito de TODAS as
   * paginas, abrindo uma janela com formulario curto.
   *
   * Por que em JS e nao em HTML: sao 63 paginas. Injetar aqui garante 100%
   * de cobertura sem rebuild, do mesmo jeito que header e footer.
   *
   * O envio usa o MESMO endpoint /api/contact e portanto os MESMOS tres
   * destinatarios do secret CONTACT_TO. O campo "source" viaja para que o
   * assunto do e-mail diga que o lead veio do botao flutuante, e nao da
   * pagina de contato.
   */
  function initFloatingCta() {
    if (document.querySelector(".float-cta")) return;

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "float-cta";
    btn.setAttribute("aria-haspopup", "dialog");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", "Ask about your brows, lips or eyeliner");
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
      "</svg><span class=\"float-cta-label\">Ask about your brows</span>";

    const modal = document.createElement("div");
    modal.className = "float-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="float-modal-panel" role="dialog" aria-modal="true" aria-labelledby="float-modal-title">
        <button type="button" class="float-modal-close" aria-label="Close">&times;</button>
        <h2 class="float-modal-title" id="float-modal-title">Ask about your brows</h2>
        <p class="float-modal-sub">Tell us what you are considering and Adriana's team answers with the honest options for your features, healing time and price.</p>
        <p class="float-modal-langs">We answer in English &middot; Atendemos em portugu&ecirc;s</p>
        <form novalidate>
          <div class="float-hp" aria-hidden="true">
            <label>Do not fill this<input type="text" name="website" tabindex="-1" autocomplete="off"></label>
          </div>
          <div class="form-group">
            <label for="float-name">Name <span aria-hidden="true">*</span></label>
            <input id="float-name" name="name" type="text" required autocomplete="name">
          </div>
          <div class="form-group">
            <label for="float-phone">Phone <span aria-hidden="true">*</span></label>
            <input id="float-phone" name="phone" type="tel" required autocomplete="tel">
          </div>
          <div class="form-group">
            <label for="float-email">Email <span aria-hidden="true">*</span></label>
            <input id="float-email" name="email" type="email" required autocomplete="email">
          </div>
          <div class="form-group">
            <label for="float-message">What are you looking for? <span aria-hidden="true">*</span></label>
            <textarea id="float-message" name="message" rows="3" required></textarea>
          </div>
          <p class="form-message" hidden role="status" aria-live="polite"></p>
          <button type="submit" class="btn btn-primary">Send my question</button>
          <p class="float-modal-fine">Or call <a href="tel:+17818538063">(781) 853-8063</a> &middot; Wilmington MA &amp; Salem NH</p>
        </form>
      </div>`;

    document.body.append(btn, modal);

    const panel = modal.querySelector(".float-modal-panel");
    const form = modal.querySelector("form");
    const msg = modal.querySelector(".form-message");
    const submit = modal.querySelector('button[type="submit"]');
    const submitLabel = submit.textContent;
    let openedAt = 0;
    let lastFocus = null;

    const PHONES = "Please call Wilmington (781) 853-8063 or Salem (978) 223-7496.";

    function show(text, ok) {
      msg.textContent = text;
      msg.hidden = false;
      msg.classList.toggle("form-message--ok", !!ok);
      msg.classList.toggle("form-message--error", !ok);
    }

    function open() {
      lastFocus = document.activeElement;
      modal.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      openedAt = Date.now();
      document.body.style.overflow = "hidden";
      modal.querySelector("#float-name").focus();
      window.PMU_track?.floatCtaOpen?.();
    }

    function close() {
      modal.hidden = true;
      btn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }

    btn.addEventListener("click", open);
    modal.querySelector(".float-modal-close").addEventListener("click", close);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) close();
    });
    document.addEventListener("keydown", (e) => {
      if (modal.hidden) return;
      if (e.key === "Escape") {
        close();
        return;
      }
      // Prende o foco na janela: sem isso o teclado sai para o site atras.
      if (e.key === "Tab") {
        const focaveis = panel.querySelectorAll(
          'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])',
        );
        const lista = [...focaveis].filter((el) => el.offsetParent !== null);
        if (!lista.length) return;
        const primeiro = lista[0];
        const ultimo = lista[lista.length - 1];
        if (e.shiftKey && document.activeElement === primeiro) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && document.activeElement === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      // Os quatro campos sao obrigatorios. Validamos aqui tambem porque o
      // form e novalidate (para controlarmos a mensagem em vez do balao
      // nativo do navegador).
      const payload = Object.fromEntries(new FormData(form).entries());
      const faltando = ["name", "phone", "email", "message"].filter(
        (k) => !String(payload[k] || "").trim(),
      );
      if (faltando.length) {
        show("Please fill in your name, phone, email and message.", false);
        form.querySelector(`[name="${faltando[0]}"]`)?.focus();
        return;
      }

      submit.disabled = true;
      submit.textContent = "Sending...";
      show("Sending your message...", true);

      payload.elapsed = Date.now() - openedAt;
      payload.page = window.location.pathname;
      payload.source = "floating-button";
      payload.location = "From floating button";

      let ok = false;
      let text = "We could not send your message. " + PHONES;

      try {
        const res = await fetch("/api/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const body = await res.json().catch(() => ({}));
        if (res.ok && body.ok) {
          ok = true;
          text = "Thank you! We received your question and will get back to you shortly.";
        } else if (body.error) {
          text = body.error;
        }
      } catch (err) {
        text = "Network error. " + PHONES;
      }

      show(text, ok);
      if (ok) {
        // Só conta como lead depois que o Worker confirmou o envio.
        window.PMU_track?.formSubmitFloating?.();
        form.reset();
      }
      submit.disabled = false;
      submit.textContent = submitLabel;
    });
  }

  function initPortfolioFilters() {
    document.querySelectorAll(".portfolio-filters").forEach((bar) => {
      const grid = bar.nextElementSibling;
      if (!grid?.classList.contains("portfolio-grid")) return;

      const buttons = bar.querySelectorAll(".portfolio-filter");
      const items = grid.querySelectorAll(".portfolio-item");

      bar.addEventListener("click", (e) => {
        const btn = e.target.closest(".portfolio-filter");
        if (!btn) return;
        const filter = btn.dataset.filter;

        buttons.forEach((b) => {
          const active = b === btn;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-pressed", active);
        });

        items.forEach((item) => {
          item.hidden = filter !== "all" && item.dataset.category !== filter;
        });
      });
    });
  }

  function initPortfolioLightbox() {
    const triggers = document.querySelectorAll(".portfolio-item");
    if (!triggers.length) return;

    let overlay = document.getElementById("portfolio-lightbox");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "portfolio-lightbox";
      overlay.className = "portfolio-lightbox";
      overlay.hidden = true;
      overlay.innerHTML = `
        <div class="portfolio-lightbox-backdrop" data-lightbox-close></div>
        <div class="portfolio-lightbox-dialog" role="dialog" aria-modal="true" aria-label="Portfolio image preview">
          <button type="button" class="portfolio-lightbox-close" aria-label="Close">&times;</button>
          <button type="button" class="portfolio-lightbox-nav portfolio-lightbox-prev" aria-label="Previous image">&#8249;</button>
          <figure class="portfolio-lightbox-figure">
            <img class="portfolio-lightbox-img" src="" alt="">
            <figcaption class="portfolio-lightbox-caption"></figcaption>
          </figure>
          <button type="button" class="portfolio-lightbox-nav portfolio-lightbox-next" aria-label="Next image">&#8250;</button>
        </div>`;
      document.body.appendChild(overlay);
    }

    const lightboxImg = overlay.querySelector(".portfolio-lightbox-img");
    const caption = overlay.querySelector(".portfolio-lightbox-caption");
    const items = [];

    triggers.forEach((item) => {
      const thumb = item.querySelector("img");
      if (!thumb) return;
      const idx = items.length;
      items.push({ src: thumb.src, alt: thumb.alt, el: item });
      item.addEventListener("click", () => openAt(idx));
    });

    if (!items.length) return;

    let index = 0;
    let lastFocus = null;

    function openAt(i) {
      index = i;
      lastFocus = document.activeElement;
      show();
    }

    function show() {
      const current = items[index];
      lightboxImg.src = current.src;
      lightboxImg.alt = current.alt;
      caption.textContent = current.alt;
      overlay.hidden = false;
      document.body.classList.add("portfolio-lightbox-open");
      overlay.querySelector(".portfolio-lightbox-close")?.focus();
    }

    function close() {
      overlay.hidden = true;
      document.body.classList.remove("portfolio-lightbox-open");
      lightboxImg.removeAttribute("src");
      lastFocus?.focus();
    }

    function step(delta) {
      const visible = items.map((it, i) => (it.el.hidden ? -1 : i)).filter((i) => i >= 0);
      if (!visible.length) return;
      const pos = visible.indexOf(index);
      index = visible[pos === -1 ? 0 : (pos + delta + visible.length) % visible.length];
      show();
    }

    overlay.querySelector("[data-lightbox-close]")?.addEventListener("click", close);
    overlay.querySelector(".portfolio-lightbox-close")?.addEventListener("click", close);
    overlay.querySelector(".portfolio-lightbox-prev")?.addEventListener("click", () => step(-1));
    overlay.querySelector(".portfolio-lightbox-next")?.addEventListener("click", () => step(1));

    document.addEventListener("keydown", (e) => {
      if (overlay.hidden) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderHeader();
    renderFooter();
    initFaq();
    initReviewsNav();
    initContactForm();
    initFloatingCta();
    initPortfolioFilters();
    initPortfolioLightbox();
  });
})();
