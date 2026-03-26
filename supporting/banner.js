/**
 * Licensed under the GNU General Public License v3.0
 * SPDX-License-Identifier: GPL-3.0-only
 *
 * Based on https://keepandroidopen.org/banner.js
 */

(function () {
  "use strict";

  // ── Localized banner strings ──────────────────────────────────────────
  var messages = {
    fa:      "به تأیید سن آنلاین نه بگویید",
    ar:      "قل لا للتحقق من العمر عبر الإنترنت",
    he:      "אמור לא לאימות גיל מקוון",
    en:      "Say No to Online Age Verification",
    ca:      "Digues no a la verificació d'edat en línia",
    cs:      "Řekněte ne online ověřování věku",
    de:      "Sagen Sie Nein zur Online-Altersverifikation",
    da:      "Sig nej til online aldersverifikation",
    nl:      "Zeg nee tegen online leeftijdsverificatie",
    el:      "Πείτε όχι στην επαλήθευση ηλικίας στο διαδίκτυο",
    es:      "Di no a la verificación de edad en línea",
    fr:      "Dites non à la vérification d’âge en ligne",
    id:      "Katakan tidak pada verifikasi usia online",
    it:      "Dì no alla verifica dell’età online",
    ko:      "온라인 연령 확인에 반대하세요",
    pl:      "Powiedz nie weryfikacji wieku online",
    "pt-BR": "Diga não à verificação de idade online",
    ru:      "Скажите нет онлайн-проверке возраста",
    sk:      "Povedzte nie overovaniu veku online",
    th:      "ปฏิเสธการยืนยันอายุออนไลน์",
    tr:      "Çevrimiçi yaş doğrulamasına hayır deyin",
    uk:      "Скажіть ні онлайн-перевірці віку",
    "zh-CN": "对在线年龄验证说不",
    "zh-TW": "對線上年齡驗證說不",
    ja:      "オンライン年齢確認に反対しよう",
    fi:      "Sano ei verkkoiän varmistukselle",
    hu:      "Mondj nemet az online életkor-ellenőrzésre",
    vi:      "Nói không với xác minh độ tuổi trực tuyến",
  };

  // ── Parse query parameters ────────────────────────────────────────────
  function getScriptParams() {
    var params = {};
    try {
      var src = document.currentScript && document.currentScript.src;
      if (!src) return params;
      var q = src.indexOf("?");
      if (q === -1) return params;
      var pairs = src.substring(q + 1).split("&");
      for (var i = 0; i < pairs.length; i++) {
        var kv = pairs[i].split("=");
        params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
      }
    } catch (e) {}
    return params;
  }

  var params = getScriptParams();

  // ── Determine locale ──────────────────────────────────────────────────
  function resolveLocale(tag) {
    if (!tag) return "en";
    if (messages[tag]) return tag;

    var lower = tag.toLowerCase();

    for (var key in messages) {
      if (key.toLowerCase() === lower) return key;
    }

    var base = lower.split("-")[0];

    for (var key2 in messages) {
      if (key2.toLowerCase() === base) return key2;
    }

    for (var key3 in messages) {
      if (key3.toLowerCase().split("-")[0] === base) return key3;
    }

    return "en";
  }

  var locale = resolveLocale(
    params.lang ||
    document.documentElement.lang ||
    navigator.language ||
    navigator.userLanguage
  );

  // ── Size variant ──────────────────────────────────────────────────────
  var size = params.size === "mini" ? "mini"
      : params.size === "minimal"
        ? "minimal"
        : "normal";

  // ── Link ───────────────────────────────────────────────────
  var linkParam = params.link;
  var defaultLink = "https://reclaimthenet.org/age-verification";
  var linkUrl = linkParam === "none" ? null : (linkParam || defaultLink);

  // ── Close button ─────────────────────────────────────────────────────
  var showClose = params.hidebutton !== "off";
  var storageKey = "kao-banner-hidden";
  var dismissDays = 30;

  // ── CSS ──────────────────────────────────────────────────
  var cssNormal =
    ".kao-banner{" +
      "position:relative;" +
      "background:linear-gradient(180deg,#d32f2f 0%,#b71c1c 100%);" +
      "border-bottom:4px solid #801313;" +
      "color:#fff;" +
      "font-family:'Arial Black',sans-serif;" +
      "font-weight:900;" +
      "text-transform:uppercase;" +
      "letter-spacing:2px;" +
      "font-size:1.5rem;" +
      "text-align:center;" +
      "padding:0.5rem 2.5rem;" +
    "}";

  var cssMini =
    ".kao-banner{" +
      "font-size:0.75rem;padding:0.25rem 1.5rem;" +
    "}";

  var cssMinimal = cssMini;

  var cssCommon =
    ".kao-banner a{color:#fff;text-decoration:none;}" +
    ".kao-banner-close{position:absolute;right:0.5rem;top:50%;transform:translateY(-50%);}";

  var style = document.createElement("style");
  style.textContent =
    (size === "mini" ? cssMini : size === "minimal" ? cssMinimal : cssNormal)
    + cssCommon;
  document.head.appendChild(style);

  // ── Dismiss check ─────────────────────────────────────────────────────
  if (showClose) {
    try {
      var dismissed = localStorage.getItem(storageKey);
      if (dismissed) {
        var elapsed = Date.now() - Number(dismissed);
        if (elapsed < dismissDays * 86400000) return;
        localStorage.removeItem(storageKey);
      }
    } catch (e) {}
  }

  // ── Create banner ─────────────────────────────────────────────────────
  var banner = document.createElement("div");
  banner.className = "kao-banner";

  var messageText = messages[locale] || messages.en;

  if (linkUrl) {
    var link = document.createElement("a");
    link.href = linkUrl;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = messageText;
    banner.appendChild(link);
  } else {
    banner.appendChild(document.createTextNode(messageText));
  }

  // Close button
  if (showClose) {
    var closeBtn = document.createElement("button");
    closeBtn.className = "kao-banner-close";
    closeBtn.textContent = "✕";
    closeBtn.onclick = function () {
      banner.style.display = "none";
      try { localStorage.setItem(storageKey, Date.now()); } catch (e) {}
    };
    banner.appendChild(closeBtn);
  }

  // Insert banner
  var targetId = params.id;
  if (targetId) {
    var target = document.getElementById(targetId);
    if (target) target.appendChild(banner);
    else document.body.prepend(banner);
  } else {
    document.body.prepend(banner);
  }

})();