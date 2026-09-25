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
        <a href="${resolvePath("/payment-plan/")}">Split your service into 4 interest-free payments with Cherry. See your options</a>
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
            <a class="btn btn-primary" href="https://www.fresha.com/book-now/adrianas-permanent-makeup-zeaseit5/all-offer?pId=727586" rel="noopener">Book Now</a>
          </div>
        </div>
      </header>`;

    const toggle = el.querySelector(".nav-toggle");
    const nav = el.querySelector(".main-nav");
    toggle?.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open);
    });

    // Esc fecha o menu e devolve o foco ao botao que o abriu.
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !nav?.classList.contains("is-open")) return;
      nav.classList.remove("is-open");
      toggle?.setAttribute("aria-expanded", "false");
      toggle?.focus();
    });

    el.querySelectorAll(".submenu-toggle").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Mesmo corte do CSS do hamburguer. Era innerWidth > 900: entre 901
        // e 1099px o menu ja e hamburguer, mas o acordeao nao abria.
        if (!window.matchMedia("(max-width: 1099.98px)").matches) return;
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
              <h3>${SITE.name}</h3>
              <p>Master Permanent Makeup Artist with ${SITE.stats.years} experience and ${SITE.stats.procedures} procedures performed.</p>
              <p>Women-owned · LGBTQ+ friendly · Wheelchair accessible (Wilmington)</p>
            </div>
            <div>
              <h3>Services</h3>
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
              <h3>Locations</h3>
              <ul>
                <li><a href="${resolvePath("/locations/")}">All Locations</a></li>
                <li><a href="${resolvePath("/locations/wilmington-ma/")}">Wilmington, MA</a></li>
                <li><a href="${resolvePath("/locations/salem-nh/")}">Salem, NH</a></li>
                <li><a href="${resolvePath("/contact/")}">Contact</a></li>
                <li><a href="${resolvePath("/faq/")}">FAQ</a></li>
              </ul>
            </div>
            <div class="footer-nap">
              <h3>Wilmington, MA</h3>
              <p>${w.street}, ${w.city}, ${w.region} ${w.zip}<br>
              <a href="tel:+17818538063">${w.phone}</a></p>
              <h3>Salem, NH</h3>
              <p>${s.street}, ${s.city}, ${s.region} ${s.zip}<br>
              <a href="tel:+19782237496">${s.phone}</a></p>
              <h3>Academy — Peabody, MA</h3>
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

  // O Worker descarta envio feito em menos de 3s (filtro de bot). Com
  // autofill, uma pessoa de verdade envia o modal em menos que isso: antes
  // ela via "Thank you!", o GA4 contava um lead e nenhum e-mail saia.
  // Agora o cliente espera o que falta antes de enviar. O filtro continua
  // valendo para quem posta direto no endpoint.
  const MIN_FILL_MS = 3000;
  function waitMinFill(start) {
    const left = MIN_FILL_MS + 250 - (Date.now() - start);
    return left > 0 ? new Promise((r) => setTimeout(r, left)) : Promise.resolve();
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
      await waitMinFill(loadedAt);
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
    btn.setAttribute("aria-label", "Message us about permanent makeup");
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
      "</svg><span class=\"float-cta-label\">Message Us</span>";

    // Unidade da pagina (window.PMU_PAGE, gravado no build). Em pagina de
    // Salem o modal mandava ligar para Wilmington e o lead chegava sem unidade.
    const pageCity = (window.PMU_PAGE && window.PMU_PAGE.city) || "";
    const callLine =
      pageCity === "salem"
        ? 'Or call <a href="tel:+19782237496">(978) 223-7496</a> &middot; Salem, NH'
        : pageCity === "wilmington"
          ? 'Or call <a href="tel:+17818538063">(781) 853-8063</a> &middot; Wilmington, MA'
          : 'Or call Wilmington <a href="tel:+17818538063">(781) 853-8063</a> or Salem <a href="tel:+19782237496">(978) 223-7496</a>';
    const leadLocation =
      pageCity === "salem" ? "Salem, NH" : pageCity === "wilmington" ? "Wilmington, MA" : "Not specified";

    const modal = document.createElement("div");
    modal.className = "float-modal";
    modal.hidden = true;
    modal.innerHTML = `
      <div class="float-modal-panel" role="dialog" aria-modal="true" aria-labelledby="float-modal-title">
        <button type="button" class="float-modal-close" aria-label="Close">&times;</button>
        <h2 class="float-modal-title" id="float-modal-title">Message Us</h2>
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
          <p class="float-modal-fine">${callLine}</p>
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

      await waitMinFill(openedAt);
      payload.elapsed = Date.now() - openedAt;
      payload.page = window.location.pathname;
      payload.source = "floating-button";
      // A origem ja vai em payload.source; aqui vai a unidade da pagina.
      payload.location = leadLocation;

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

  /* Barra de reserva que persegue o scroll (23/09/2026).

     O .float-cta ("Message Us") resolve duvida; esta resolve reserva
     e carrega o preco junto, que e o que a pessoa quer confirmar
     antes de clicar. So aparece quando o CTA do hero sai da tela:
     enquanto o botao original esta visivel, dois CTAs identicos na
     mesma tela so dividem a atencao. */
  function initBookRail() {
    const rail = document.querySelector("[data-book-rail]");
    if (!rail) return;
    // .svc-hero e o hero das 45 paginas que tem a barra: sem ele no
    // seletor, a ancora nunca era encontrada e a barra nunca aparecia.
    const anchor = document.querySelector(".svc-hero .btn-primary, .page-hero .btn, .hero .btn");
    if (!anchor) return;

    rail.hidden = false;
    // Altura real da barra para os botoes flutuantes subirem o suficiente
    // (ela tem uma ou duas linhas conforme a tela e o numero de botoes).
    const medir = () => document.documentElement.style.setProperty("--rail-h", rail.offsetHeight + "px");
    medir();
    window.addEventListener("resize", medir, { passive: true });
    const io = new IntersectionObserver(
      ([entry]) => rail.classList.toggle("is-visible", !entry.isIntersecting),
      { rootMargin: "-8px 0px 0px 0px" }
    );
    io.observe(anchor);
  }

  /* Galeria coverflow (24/09/2026).

     Reescrita em vanilla do efeito da referencia, que era React +
     Swiper. A posicao de cada slide e funcao da distancia ate o ativo:
     desloca no X, gira no Y e afunda no Z. Nada de biblioteca.

     Altura fixa e largura livre: as 37 fotos tem proporcoes de 0,46 a
     1,58 e qualquer largura fixa cortaria rosto em metade delas. */
  function initCoverflow() {
    document.querySelectorAll("[data-coverflow]").forEach(function (cf) {
      const track = cf.querySelector(".cf-track");
      const slides = Array.from(cf.querySelectorAll(".cf-slide"));
      if (slides.length < 2) return;

      const stage = cf.querySelector(".cf-stage");
      const saida = cf.querySelector("[data-cf-current]");
      const VISIVEIS = 3;            // quantos de cada lado ficam na cena
      let ativo = 0;

      function posicionar() {
        const total = slides.length;
        slides.forEach(function (s, i) {
          /* distancia CIRCULAR: sem isto, no slide 1 todos os outros
             ficavam a direita e o carrossel parecia ter comeco e fim.
             Com o laco, sempre ha foto dos dois lados. */
          let d = i - ativo;
          if (d > total / 2) d -= total;
          if (d < -total / 2) d += total;
          const ad = Math.abs(d);
          if (ad > VISIVEIS) { s.hidden = true; return; }
          s.hidden = false;
          /* Passo em PIXELS, medido na largura real do slide: em
             porcentagem ele variava com cada foto e o espacamento
             ficava irregular. */
          const passo = s.offsetWidth * 0.82;
          const giro = d === 0 ? 0 : (d > 0 ? -38 : 38);
          const z = ad === 0 ? 0 : -110 - (ad - 1) * 70;
          const escala = ad === 0 ? 1 : 0.9 - (ad - 1) * 0.06;
          s.style.transform =
            "translateX(calc(-50% + " + (d * passo) + "px)) translateZ(" + z +
            "px) rotateY(" + giro + "deg) scale(" + escala + ")";
          s.style.opacity = ad === 0 ? "1" : String(Math.max(0.25, 0.7 - (ad - 1) * 0.2));
          s.style.zIndex = String(100 - ad);
          s.setAttribute("aria-hidden", ad === 0 ? "false" : "true");
        });
        if (saida) saida.textContent = String(ativo + 1);
      }

      /* As fotos sao loading="lazy" e as que estao fora da cena ficam
         display:none: o navegador so comecava a baixar quando a foto
         entrava na borda, e com a troca a cada 1s ela passava em branco.
         Aqui as proximas ADIANTE fotos de cada lado sao aquecidas antes
         de entrar em cena. A pagina continua carregando so o necessario. */
      const ADIANTE = 3;
      const aquecidas = new Set();
      function aquecer() {
        for (let k = -(VISIVEIS + ADIANTE); k <= VISIVEIS + ADIANTE; k++) {
          const i = (ativo + k + slides.length * 2) % slides.length;
          if (aquecidas.has(i)) continue;
          const img = slides[i].querySelector("img");
          if (!img) continue;
          aquecidas.add(i);
          img.loading = "eager";
        }
      }

      function ir(delta) {
        ativo = (ativo + delta + slides.length) % slides.length;
        posicionar();
        aquecer();
      }

      cf.querySelector("[data-cf-prev]")?.addEventListener("click", function () { pararDeVez(); ir(-1); });
      cf.querySelector("[data-cf-next]")?.addEventListener("click", function () { pararDeVez(); ir(1); });

      /* clicar num slide lateral traz ele para o centro */
      slides.forEach(function (s, i) {
        s.addEventListener("click", function () { if (i !== ativo) { pararDeVez(); ativo = i; posicionar(); } });
      });

      /* teclado: a cena inteira e focavel e responde as setas */
      stage.tabIndex = 0;
      stage.setAttribute("role", "region");
      // O rotulo era "Nano Brows gallery" fixo, ate em pagina de labio.
      const titulo = cf.closest("section")?.querySelector("h2")?.textContent.trim() || "Photo gallery";
      stage.setAttribute("aria-label", titulo + ", use arrow keys");
      stage.addEventListener("keydown", function (e) {
        if (e.key === "ArrowLeft") { e.preventDefault(); pararDeVez(); ir(-1); }
        if (e.key === "ArrowRight") { e.preventDefault(); pararDeVez(); ir(1); }
      });

      /* arrastar com o dedo ou com o mouse */
      let x0 = null;
      stage.addEventListener("pointerdown", function (e) { x0 = e.clientX; });
      stage.addEventListener("pointerup", function (e) {
        if (x0 === null) return;
        const dx = e.clientX - x0;
        if (Math.abs(dx) > 40) { pararDeVez(); ir(dx < 0 ? 1 : -1); }
        x0 = null;
      });
      stage.addEventListener("pointercancel", function () { x0 = null; });

      /* --- passagem automatica ---------------------------------
         Pedido da Rachel (25/09/2026): troca a cada 1s, para a visitante
         perceber que ha muitas fotos. Movimento chama atencao. As setas,
         o arrasto e o teclado continuam funcionando.

         Freios que ficam (acessibilidade, WCAG 2.2.2):
         1. botao de pausar/retomar ao lado das setas; quem pausa por
            ele fica pausado
         2. seta, arrasto, clique ou tecla trocam a foto e o automatico
            volta sozinho RETOMA ms depois (antes desligava de vez)
         3. foco pelo TECLADO pausa (clique de mouse nao)
         4. so roda com a galeria na tela
         5. nao liga se o sistema pede menos movimento
         O hover NAO pausa mais: no desktop o cursor quase sempre esta
         em cima da galeria e ela parecia parada. */
      const INTERVALO = 1000;
      const RETOMA = 4000;
      const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");
      let timer = null;
      let retomar = null;
      let naTela = !("IntersectionObserver" in window);
      let pausadoPeloBotao = false;
      let focoTeclado = false;

      const controles = cf.querySelector(".cf-controls");
      const btnPlay = document.createElement("button");
      btnPlay.type = "button";
      btnPlay.className = "cf-nav cf-play";
      function pintarBotao() {
        const rodando = !pausadoPeloBotao;
        btnPlay.setAttribute("aria-label", rodando ? "Pause slideshow" : "Play slideshow");
        btnPlay.setAttribute("aria-pressed", rodando ? "false" : "true");
        btnPlay.innerHTML = rodando
          ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6v12M15 6v12"/></svg>'
          : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5l11 7-11 7z"/></svg>';
      }
      if (controles && !semMovimento.matches) {
        pintarBotao();
        controles.appendChild(btnPlay);
      }

      function podeTocar() {
        return naTela && !pausadoPeloBotao && !focoTeclado && !semMovimento.matches;
      }
      function tocar() {
        if (timer || !podeTocar()) return;
        timer = setInterval(function () { ir(1); }, INTERVALO);
      }
      function pausar() {
        if (timer) { clearInterval(timer); timer = null; }
      }
      function pararDeVez() {      // interacao manual: pausa e volta sozinho
        pausar();
        clearTimeout(retomar);
        retomar = setTimeout(tocar, RETOMA);
      }

      btnPlay.addEventListener("click", function () {
        pausadoPeloBotao = !pausadoPeloBotao;
        clearTimeout(retomar);
        pintarBotao();
        pausadoPeloBotao ? pausar() : (ir(1), tocar());
      });

      cf.addEventListener("focusin", function (e) {
        if (e.target.matches && e.target.matches(":focus-visible")) { focoTeclado = true; pausar(); }
      });
      cf.addEventListener("focusout", function (e) {
        if (!cf.contains(e.relatedTarget)) { focoTeclado = false; tocar(); }
      });

      /* so roda enquanto a galeria esta na tela */
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entradas) {
          naTela = entradas[0].isIntersecting;
          naTela ? tocar() : pausar();
        }, { threshold: 0.25 }).observe(cf);
      } else {
        tocar();
      }

      /* total real de fotos: o HTML trazia "37" fixo, e a galeria de
         Nano Brows tem 33 desde a retirada das fotos de antes */
      const totalEl = cf.querySelector(".cf-total");
      if (totalEl) totalEl.textContent = String(slides.length);

      cf.setAttribute("data-cf-ready", "");
      posicionar();
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entradas, obs) {
          if (entradas[0].isIntersecting) { aquecer(); obs.disconnect(); }
        }, { rootMargin: "600px 0px" }).observe(cf);
      } else {
        aquecer();
      }
    });
  }

  /* Galeria animada (24/09/2026).

     Vanilla, no lugar de React + motion/react. Duas transformacoes na
     grade (rotateX e scale) e um translateY por coluna, todas em
     funcao do progresso da rolagem dentro da secao.

     A secao inteira e conteudo real sem o script: 12 fotos, cada uma
     linkando para o proprio servico. O JS so adiciona o movimento. */
  function initGaleria() {
    const sec = document.querySelector("[data-ag]");
    if (!sec) return;

    const grade = sec.querySelector("[data-ag-grid]");
    const colunas = Array.from(sec.querySelectorAll("[data-ag-col]"));
    if (!grade || !colunas.length) return;

    const desktop = window.matchMedia("(min-width: 900px)");
    const calma = window.matchMedia("(prefers-reduced-motion: reduce)");
    /* cada coluna anda num ritmo diferente: e o parallax da referencia */
    const FAIXAS = [[-8, 2], [14, 4], [-8, 2]];

    let ligado = false, pedido = null;

    const entre = (p, a, b) => Math.min(1, Math.max(0, (p - a) / (b - a)));

    function desenhar() {
      pedido = null;
      const r = sec.getBoundingClientRect();
      const percorrivel = r.height - window.innerHeight;
      if (percorrivel <= 0) return;
      const p = Math.min(1, Math.max(0, -r.top / percorrivel));

      const giroX = 75 - 75 * entre(p, 0, 0.5);        // deitada -> de pe
      const escala = 1.2 - 0.2 * entre(p, 0.5, 0.9);   // aproxima e assenta
      grade.style.transform = "rotateX(" + giroX + "deg) scale(" + escala + ")";

      const t = entre(p, 0.5, 1);
      colunas.forEach(function (col, i) {
        const [de, ate] = FAIXAS[i % FAIXAS.length];
        col.style.transform = "translateY(" + (de + (ate - de) * t) + "%)";
      });
    }

    function aoRolar() {
      if (pedido === null) pedido = requestAnimationFrame(desenhar);
    }

    function ligar() {
      if (ligado) return;
      ligado = true;
      sec.setAttribute("data-ag-ready", "");
      sec.style.minHeight = "320vh";
      window.addEventListener("scroll", aoRolar, { passive: true });
      window.addEventListener("resize", aoRolar);
      desenhar();
    }

    function desligar() {
      if (!ligado) return;
      ligado = false;
      sec.removeAttribute("data-ag-ready");
      sec.style.minHeight = "";
      window.removeEventListener("scroll", aoRolar);
      window.removeEventListener("resize", aoRolar);
      grade.style.transform = "";
      colunas.forEach(function (c) { c.style.transform = ""; });
    }

    function avaliar() {
      desktop.matches && !calma.matches ? ligar() : desligar();
    }

    desktop.addEventListener("change", avaliar);
    calma.addEventListener("change", avaliar);
    avaliar();
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderHeader();
    renderFooter();
    initFaq();
    initReviewsNav();
    initContactForm();
    initFloatingCta();
    initBookRail();
    initCoverflow();
    initGaleria();
    initPortfolioFilters();
    initPortfolioLightbox();
    initVideo();
  });
})();

/* ===================================================================
   Hero editorial — "The Artist and Her Work" (21/09/2026)

   O markup ja garante, e este script nao pode quebrar:
   - os seis itens do indice sao <a> com href real: sem JS eles navegam
     normalmente e seguem rastreaveis. Com JS, o clique troca o slide, e
     quem navega e o link "Explore the service" do bloco de texto.
   - existe um unico <h1>, estatico. O titulo que muda e um <h2>.
   =================================================================== */
function initEditorialHero() {
  var hero = document.querySelector("[data-hero]");
  if (!hero) return;

  var shots = Array.prototype.slice.call(hero.querySelectorAll(".hero-shot"));
  var links = Array.prototype.slice.call(hero.querySelectorAll(".hero-index a"));
  var feature = hero.querySelector(".hero-feature");
  var kicker = hero.querySelector("[data-hero-kicker]");
  var name = hero.querySelector("[data-hero-name]");
  var note = hero.querySelector("[data-hero-note]");
  var cta = hero.querySelector("[data-hero-link]");
  if (!shots.length || !links.length || !feature || !cta) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var current = 0;
  var timer = null;
  var userTook = false;
  var AUTO_MS = 7000;

  function paint(i) {
    if (i === current) return;
    var link = links[i];
    if (!link) return;
    current = i;

    shots.forEach(function (s, k) { s.classList.toggle("is-active", k === i); });
    links.forEach(function (a, k) {
      a.classList.toggle("is-current", k === i);
      if (k === i) { a.setAttribute("aria-current", "true"); }
      else { a.removeAttribute("aria-current"); }
    });

    feature.setAttribute("data-swap", "");
    window.setTimeout(function () {
      kicker.textContent = link.getAttribute("data-kicker") || "";
      name.textContent = link.getAttribute("data-name") || "";
      note.innerHTML = link.getAttribute("data-note") || "";
      cta.setAttribute("href", link.getAttribute("href"));
      cta.childNodes[0].nodeValue = (link.getAttribute("data-cta") || "Explore") + " ";
      feature.removeAttribute("data-swap");
    }, reduced.matches ? 0 : 280);

    var nxt = shots[(i + 1) % shots.length];
    if (nxt) {
      var img = nxt.querySelector("img");
      if (img && img.getAttribute("loading") === "lazy") { img.setAttribute("loading", "eager"); }
    }
  }

  function stopAuto() { if (timer) { window.clearInterval(timer); timer = null; } }

  function startAuto() {
    if (reduced.matches || userTook) return;
    stopAuto();
    timer = window.setInterval(function () { paint((current + 1) % shots.length); }, AUTO_MS);
  }

  function take() { userTook = true; stopAuto(); }

  links.forEach(function (a, i) {
    a.addEventListener("mouseenter", function () { take(); paint(i); });
    a.addEventListener("focus", function () { take(); paint(i); });
    a.addEventListener("click", function (ev) {
      ev.preventDefault();
      take();
      paint(i);
      cta.focus({ preventScroll: true });
    });
  });

  var index = hero.querySelector(".hero-index");
  if (index) {
    index.addEventListener("keydown", function (ev) {
      var d = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
      if (!d) return;
      ev.preventDefault();
      take();
      var next = (current + d + shots.length) % shots.length;
      paint(next);
      links[next].focus();
    });
  }

  var x0 = null;
  hero.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
  hero.addEventListener("touchend", function (e) {
    if (x0 === null) return;
    var dx = e.changedTouches[0].clientX - x0;
    x0 = null;
    if (Math.abs(dx) < 45) return;
    take();
    paint((current + (dx < 0 ? 1 : -1) + shots.length) % shots.length);
  }, { passive: true });

  links[0].classList.add("is-current");
  links[0].setAttribute("aria-current", "true");
  startAuto();
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) { stopAuto(); } else { startAuto(); }
  });
}

// o restante deste arquivo espera o DOMContentLoaded; o hero tambem
// precisa esperar, senao o script roda antes de a secao existir.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initEditorialHero);
} else {
  initEditorialHero();
}

/* ------------------------------------------------------------------
   VIDEO — fachada que vira player de verdade no clique.

   O embed do YouTube custa ~1,3 MB e roda dezenas de requisicoes antes
   de alguem apertar play. Numa pagina que vai receber anuncio isso e
   caro em LCP. Entao o que vai no HTML e o cartaz; o iframe so nasce
   quando a pessoa clica — e ai ja com autoplay, para o clique valer
   como play e nao como "carregou, clique de novo".

   Sem JS o <noscript> da pagina mostra o link para o YouTube.
   ------------------------------------------------------------------ */
function initVideo() {
  document.querySelectorAll("[data-video]").forEach(function (caixa) {
    const botao = caixa.querySelector(".video-play");
    if (!botao) return;
    botao.addEventListener("click", function () {
      const id = caixa.getAttribute("data-video");
      if (!id) return;
      const frame = document.createElement("iframe");
      frame.className = "video-frame";
      frame.src = "https://www.youtube-nocookie.com/embed/" + id +
                  "?autoplay=1&rel=0&modestbranding=1&playsinline=1";
      frame.title = botao.getAttribute("aria-label") || "Video";
      frame.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      frame.setAttribute("allowfullscreen", "");
      frame.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
      caixa.replaceChild(frame, botao);
      caixa.setAttribute("data-video-ativo", "");
    });
  });
}
