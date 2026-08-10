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

    el.innerHTML = `
      <div class="promo-banner">
        <span>Limited-time offer: Initial session + perfection touch-up included on select services.</span>
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
                <li><a href="${resolvePath("/training/")}">PMU Academy</a></li>
              </ul>
            </div>
            <div>
              <h4>Locations</h4>
              <ul>
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
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const msg = form.querySelector(".form-message");
      if (msg) {
        msg.textContent =
          "Thank you! We will contact you shortly. For faster booking, use Fresha or call our studios.";
        msg.hidden = false;
      }
      form.reset();
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
    initPortfolioFilters();
    initPortfolioLightbox();
  });
})();
