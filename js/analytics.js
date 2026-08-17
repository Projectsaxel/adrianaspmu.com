/**
 * Camada de medicao do adrianaspmu.com (GA4 G-ZSD89WRHYZ).
 *
 * Por que um arquivo separado e nao script inline em 63 paginas:
 * um arquivo e baixado uma vez e fica em cache. Inline seria o mesmo
 * codigo repetido 63 vezes, sem cache, e qualquer correcao exigiria
 * rebuild de tudo.
 *
 * A classificacao da pagina (page_type, service, city) e injetada no
 * build por scripts/enrich_pages.py em window.PMU_PAGE. Aqui so lemos.
 *
 * Os eventos usam delegacao no document: funcionam para qualquer link,
 * inclusive os que o main.js injeta depois (header, footer, CTAs).
 *
 * NAO existe evento "purchase" aqui de proposito. A venda acontece
 * dentro do Fresha, fora do dominio. Disparar "purchase" no clique de
 * agendamento seria contar intencao como receita e corromper todo o
 * ROI. O purchase real depende do conector do Fresha ou de import
 * offline, que ainda nao temos.
 */
(function () {
  "use strict";

  var PAGE = window.PMU_PAGE || {};

  function gtagSafe(name, params) {
    if (typeof window.gtag !== "function") return;
    var p = {
      page_type: PAGE.page_type || "unknown",
      service: PAGE.service || "(none)",
      city: PAGE.city || "(none)",
    };
    for (var k in params) if (Object.prototype.hasOwnProperty.call(params, k)) p[k] = params[k];
    window.gtag("event", name, p);
  }

  /** De qual unidade e este link do Fresha / telefone. */
  function unitFromHref(href) {
    var h = String(href || "").toLowerCase();
    if (h.indexOf("wilmington") > -1 || h.indexOf("7818538063") > -1) return "wilmington";
    if (h.indexOf("salem") > -1 || h.indexOf("9782237496") > -1) return "salem";
    return PAGE.city || "(not set)";
  }

  document.addEventListener(
    "click",
    function (ev) {
      var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
      if (!a) return;
      var href = a.getAttribute("href") || "";

      if (href.indexOf("fresha.com") > -1) {
        gtagSafe("booking_start", {
          location: unitFromHref(href),
          link_text: (a.textContent || "").trim().slice(0, 60),
          destination: href.slice(0, 200),
        });
        return;
      }
      if (href.indexOf("tel:") === 0) {
        gtagSafe("phone_click", {
          location: unitFromHref(href),
          phone: href.replace("tel:", ""),
        });
        return;
      }
      if (href.indexOf("wa.me") > -1 || href.indexOf("api.whatsapp.com") > -1) {
        gtagSafe("whatsapp_click", { location: unitFromHref(href) });
      }
    },
    true,
  );

  /**
   * Disparados pelo main.js quando o formulario responde ok:true.
   * Nao ouvimos "submit" porque submit inclui envio que falhou; o que
   * vale como lead e o que o Worker confirmou que saiu.
   */
  window.PMU_track = {
    formSubmitContact: function (location) {
      gtagSafe("form_submit_contact", { location: location || PAGE.city || "(not set)" });
    },
    academyLead: function (course) {
      gtagSafe("academy_lead", { course: course || PAGE.service || "(not set)" });
    },
  };
})();
