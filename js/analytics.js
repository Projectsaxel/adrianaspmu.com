/**
 * Camada de medicao do adrianaspmu.com (GA4 G-ZSD89WRHYZ). Versao 2.
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
 * ---------------------------------------------------------------
 * O QUE MUDOU NA V2 (20/08/2026): ATRIBUICAO ATE O FRESHA
 * ---------------------------------------------------------------
 * A venda acontece dentro do fresha.com, outro dominio. O Fresha
 * envia para o GA4 um evento de compra COM VALOR, desde que o dono
 * do negocio cole o Measurement ID nas configuracoes dele.
 *
 * Problema: o suporte do Fresha declara que a plataforma NAO suporta
 * cross-domain tracking. Sem cross-domain, o visitante que sai daqui
 * e chega la vira sessao nova, e o Fresha atribuiria toda venda a
 * "adrianaspmu.com / referral". Ou seja: saberiamos que a venda veio
 * do site, mas nunca de qual canal (Google organico, Ads, Instagram,
 * GBP...). Isso destroi a decisao de investimento.
 *
 * Solucao implementada aqui: gravamos a origem real da visitante em
 * cookie proprio e REESCREVEMOS todo link para o fresha.com carregando
 * essa origem em utm_source / utm_medium / utm_campaign. O GA4 que roda
 * dentro do Fresha le esses utm da URL e abre a sessao dele ja com o
 * canal certo. A venda entra na property atribuida a google/organic,
 * google/cpc, instagram/social, etc., em vez de referral.
 *
 * Os click ids (gclid, wbraid, fbclid...) tambem viajam, para o Google
 * Ads reconciliar a conversao com o clique pago.
 *
 * ---------------------------------------------------------------
 * NAO existe evento "purchase" disparado por este arquivo, de
 * proposito. Disparar purchase no clique de agendamento seria contar
 * intencao como receita e corromper todo o ROI. O purchase real vem do
 * Fresha, pelo Measurement ID configurado la dentro.
 */
(function () {
  "use strict";

  var PAGE = window.PMU_PAGE || {};

  var ATTR_COOKIE = "pmu_attr";
  var ATTR_MAX_AGE = 60 * 60 * 24 * 90; // 90 dias, mesma janela do GA4
  var FRESHA_HOST = /(^|\.)fresha\.com$/i;

  // Click ids de midia paga. Viajam junto para o Fresha para que o
  // Google Ads consiga casar a conversao com o clique que a gerou.
  var CLICK_IDS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "ttclid"];

  var SEARCH_HOSTS = /(^|\.)(google|bing|yahoo|duckduckgo|ecosia|search\.brave|baidu|yandex|aol|ask)\./i;
  var SOCIAL_HOSTS = /(^|\.)(facebook|instagram|tiktok|pinterest|linkedin|twitter|threads|youtube|snapchat|reddit)\./i;
  var AI_HOSTS = /(^|\.)(chatgpt|openai|perplexity|claude|anthropic|copilot|gemini)\./i;

  // ---------------------------------------------------------------
  // cookie
  // ---------------------------------------------------------------

  function readCookie(name) {
    var parts = String(document.cookie || "").split("; ");
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].indexOf(name + "=") === 0) {
        try {
          return decodeURIComponent(parts[i].slice(name.length + 1));
        } catch (e) {
          return "";
        }
      }
    }
    return "";
  }

  function writeCookie(name, value) {
    var secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie =
      name + "=" + encodeURIComponent(value) +
      "; path=/; max-age=" + ATTR_MAX_AGE + "; SameSite=Lax" + secure;
  }

  // ---------------------------------------------------------------
  // atribuicao
  // ---------------------------------------------------------------

  /** Host raiz legivel: "www.google.com" vira "google". */
  function rootName(host) {
    var h = String(host || "").replace(/^www\./i, "").toLowerCase();
    var parts = h.split(".");
    if (parts.length >= 2) return parts[parts.length - 2];
    return h || "(unknown)";
  }

  /**
   * Origem DESTE carregamento de pagina, na mesma logica do GA4:
   * utm explicito > click id de midia paga > referrer > nada (direto).
   * Retorna null quando e trafego direto ou navegacao interna.
   */
  function currentTouch() {
    var q;
    try {
      q = new URLSearchParams(location.search);
    } catch (e) {
      return null;
    }

    var touch = { ts: Date.now() };
    var i, id, val;

    // Click ids sempre viajam, mesmo quando ha utm por cima.
    for (i = 0; i < CLICK_IDS.length; i++) {
      id = CLICK_IDS[i];
      val = q.get(id);
      if (val) {
        touch.k = id;
        touch.v = val.slice(0, 200);
        break;
      }
    }

    if (q.get("utm_source")) {
      touch.s = q.get("utm_source").slice(0, 100);
      touch.m = (q.get("utm_medium") || "(not set)").slice(0, 100);
      touch.c = (q.get("utm_campaign") || "(not set)").slice(0, 150);
      if (q.get("utm_content")) touch.ct = q.get("utm_content").slice(0, 150);
      if (q.get("utm_term")) touch.t = q.get("utm_term").slice(0, 150);
      return touch;
    }

    if (touch.k) {
      if (touch.k === "gclid" || touch.k === "gbraid" || touch.k === "wbraid") {
        touch.s = "google";
        touch.m = "cpc";
      } else if (touch.k === "msclkid") {
        touch.s = "bing";
        touch.m = "cpc";
      } else if (touch.k === "ttclid") {
        touch.s = "tiktok";
        touch.m = "cpc";
      } else {
        touch.s = "facebook";
        touch.m = "social";
      }
      touch.c = "(not set)";
      return touch;
    }

    var ref = document.referrer || "";
    if (!ref) return null;

    var refHost;
    try {
      refHost = new URL(ref).hostname;
    } catch (e) {
      return null;
    }
    // Navegacao interna, e o Fresha voltando, nao sao origem nova.
    if (refHost === location.hostname || FRESHA_HOST.test(refHost)) return null;

    touch.s = rootName(refHost);
    if (SEARCH_HOSTS.test(refHost)) touch.m = "organic";
    else if (SOCIAL_HOSTS.test(refHost)) touch.m = "social";
    else if (AI_HOSTS.test(refHost)) touch.m = "ai_referral";
    else touch.m = "referral";
    touch.c = "(not set)";
    return touch;
  }

  /**
   * Guarda dois toques: f = primeiro da vida do cookie, l = ultimo
   * nao-direto. O "l" e o que vai para o Fresha, porque e o mesmo
   * modelo que o GA4 usa nos relatorios (last non-direct click).
   * Assim o canal que o GA4 credita pela sessao no site e o mesmo que
   * o Fresha vai creditar pela venda, e os dois numeros batem.
   */
  function attribution() {
    var stored = {};
    try {
      stored = JSON.parse(readCookie(ATTR_COOKIE) || "{}") || {};
    } catch (e) {
      stored = {};
    }

    var touch = currentTouch();
    if (touch) {
      if (!stored.f) stored.f = touch;
      stored.l = touch;
      writeCookie(ATTR_COOKIE, JSON.stringify(stored));
    } else if (!stored.f) {
      stored.f = stored.l = { s: "(direct)", m: "(none)", c: "(not set)", ts: Date.now() };
      writeCookie(ATTR_COOKIE, JSON.stringify(stored));
    }
    return stored;
  }

  var ATTR = attribution();
  var LAST = ATTR.l || {};

  // ---------------------------------------------------------------
  // eventos
  // ---------------------------------------------------------------

  function gtagSafe(name, params) {
    if (typeof window.gtag !== "function") return;
    var p = {
      page_type: PAGE.page_type || "unknown",
      service: PAGE.service || "(none)",
      city: PAGE.city || "(none)",
      attr_source: LAST.s || "(direct)",
      attr_medium: LAST.m || "(none)",
      attr_campaign: LAST.c || "(not set)",
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

  // ---------------------------------------------------------------
  // decoracao dos links do Fresha
  // ---------------------------------------------------------------

  function isFresha(href) {
    if (!href || href.indexOf("fresha.com") === -1) return false;
    try {
      return FRESHA_HOST.test(new URL(href, location.href).hostname);
    } catch (e) {
      return false;
    }
  }

  /**
   * Os utm que a visitante leva para o Fresha. Quando a origem e
   * direta ou interna, marcamos explicitamente adrianaspmu.com/website:
   * assim a venda aparece como "veio do site" em vez de "(direct)",
   * que no Fresha se confundiria com quem digitou o link do Fresha.
   */
  function freshaParams() {
    var src = LAST.s;
    var med = LAST.m;
    if (!src || src === "(direct)") {
      src = "adrianaspmu.com";
      med = "website";
    }
    var params = {
      utm_source: src,
      utm_medium: med || "referral",
      utm_campaign: LAST.c && LAST.c !== "(not set)" ? LAST.c : "website_booking",
      utm_content: LAST.ct || (PAGE.page_type || "page") + ":" + location.pathname,
    };
    if (LAST.t) params.utm_term = LAST.t;
    if (LAST.k && LAST.v) params[LAST.k] = LAST.v;
    return params;
  }

  function decorate(a) {
    var href = a.getAttribute("href");
    if (!isFresha(href)) return;
    var url;
    try {
      url = new URL(href, location.href);
    } catch (e) {
      return;
    }
    if (url.searchParams.get("utm_source")) return; // ja decorado
    var params = freshaParams();
    for (var k in params) {
      if (Object.prototype.hasOwnProperty.call(params, k) && params[k]) {
        url.searchParams.set(k, params[k]);
      }
    }
    a.setAttribute("href", url.toString());
  }

  function decorateAll(root) {
    var nodes = (root || document).querySelectorAll('a[href*="fresha.com"]');
    for (var i = 0; i < nodes.length; i++) decorate(nodes[i]);
  }

  // O header, o footer e varios CTAs sao injetados pelo main.js depois
  // do DOMContentLoaded. Sem observer, esses links sairiam sem utm.
  function watchDom() {
    if (typeof MutationObserver !== "function") return;
    var obs = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var added = muts[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var n = added[j];
          if (n.nodeType !== 1) continue;
          if (n.matches && n.matches('a[href*="fresha.com"]')) decorate(n);
          if (n.querySelectorAll) decorateAll(n);
        }
      }
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
  }

  // Decora o que ja existe e passa a vigiar o que vier. O arquivo e
  // carregado com defer, entao o DOM ja esta pronto aqui; o listener
  // extra e so para o caso de alguem trocar o defer por async.
  decorateAll(document);
  watchDom();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      decorateAll(document);
    });
  }

  // ---------------------------------------------------------------
  // cliques
  // ---------------------------------------------------------------

  document.addEventListener(
    "click",
    function (ev) {
      var a = ev.target && ev.target.closest ? ev.target.closest("a[href]") : null;
      if (!a) return;
      var href = a.getAttribute("href") || "";

      if (isFresha(href)) {
        // Rede de seguranca: se o link nasceu depois do observer, ou
        // se algum script trocou o href, decoramos aqui, no ultimo
        // instante antes da navegacao.
        decorate(a);
        href = a.getAttribute("href") || href;

        // O link de avaliacoes vai para o mesmo dominio mas nao e
        // agendamento. Contar como booking_start inflaria a intencao.
        if (href.indexOf("modal-reviews") > -1) {
          gtagSafe("reviews_click", { destination: "fresha", location: unitFromHref(href) });
          return;
        }
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
        return;
      }
      if (href.indexOf("maps.app.goo.gl") > -1 || href.indexOf("google.com/maps") > -1) {
        gtagSafe("map_click", { location: unitFromHref(href) });
        return;
      }
      if (href.indexOf("instagram.com") > -1 || href.indexOf("facebook.com") > -1) {
        gtagSafe("social_click", {
          network: href.indexOf("instagram") > -1 ? "instagram" : "facebook",
        });
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
      gtagSafe("form_submit_contact", {
        location: location || PAGE.city || "(not set)",
        form_source: "contact-page",
      });
    },
    academyLead: function (course) {
      gtagSafe("academy_lead", { course: course || PAGE.service || "(not set)" });
    },
    /** Abriu a janela do botao flutuante. Intencao, nao lead. */
    floatCtaOpen: function () {
      gtagSafe("float_cta_open", { form_source: "floating-button" });
    },
    /**
     * Lead do botao flutuante, so depois de ok:true do Worker.
     * Evento separado do form_submit_contact de proposito: os dois
     * chegam nos mesmos tres e-mails, mas vem de contextos diferentes
     * e precisam ser comparaveis no relatorio.
     */
    formSubmitFloating: function () {
      gtagSafe("form_submit_floating", {
        form_source: "floating-button",
        location: PAGE.city || "(not set)",
      });
    },
  };

  // Exposto para depuracao no console: PMU_attr().
  window.PMU_attr = function () {
    return { first: ATTR.f, last: ATTR.l, freshaParams: freshaParams() };
  };
})();
