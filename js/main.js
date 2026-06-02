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
      return `<li class="has-submenu">
        <button type="button" aria-expanded="false">${item.label}</button>
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

    el.innerHTML = `
      <div class="promo-banner">
        <span>Limited-time offer: Initial session + perfection touch-up included on select services.</span>
        <a href="${resolvePath("/contact.html")}">Book consultation ($50)</a>
      </div>
      <header class="site-header">
        <div class="container header-inner">
          <a class="logo" href="${home}" aria-label="Adriana's PMU Home">Adriana's <span>PMU</span></a>
          <button class="nav-toggle" type="button" aria-label="Open menu" aria-expanded="false">☰</button>
          <nav class="main-nav" aria-label="Main navigation">
            <ul>${navItems}</ul>
          </nav>
          <div class="header-cta">
            <a class="btn btn-primary" href="${resolvePath("/contact.html")}">Book Consultation</a>
          </div>
        </div>
      </header>`;

    const toggle = el.querySelector(".nav-toggle");
    const nav = el.querySelector(".main-nav");
    toggle?.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open);
    });

    el.querySelectorAll(".has-submenu > button").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (window.innerWidth > 900) return;
        const li = btn.parentElement;
        li.classList.toggle("is-expanded");
        btn.setAttribute("aria-expanded", li.classList.contains("is-expanded"));
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
              </ul>
            </div>
            <div>
              <h4>Locations</h4>
              <ul>
                <li><a href="${resolvePath("/locations/wilmington-ma.html")}">Wilmington, MA</a></li>
                <li><a href="${resolvePath("/locations/salem-nh.html")}">Salem, NH</a></li>
                <li><a href="${resolvePath("/contact.html")}">Contact</a></li>
                <li><a href="${resolvePath("/faq.html")}">FAQ</a></li>
              </ul>
            </div>
            <div class="footer-nap">
              <h4>Wilmington, MA</h4>
              <p>${w.street}, ${w.city}, ${w.region} ${w.zip}<br>
              <a href="tel:+17818538063">${w.phone}</a></p>
              <h4>Salem, NH</h4>
              <p>${s.street}, ${s.city}, ${s.region} ${s.zip}<br>
              <a href="tel:+19782237496">${s.phone}</a></p>
            </div>
          </div>
          <div class="footer-bottom">
            <p>© ${new Date().getFullYear()} ${SITE.legalName}. All rights reserved.</p>
            <p>
              <a href="${resolvePath("/privacy-policy.html")}">Privacy</a> ·
              <a href="${resolvePath("/terms-of-use.html")}">Terms</a> ·
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

  document.addEventListener("DOMContentLoaded", () => {
    renderHeader();
    renderFooter();
    initFaq();
    initReviewsNav();
    initContactForm();
  });
})();
