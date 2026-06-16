(function () {
  "use strict";

  var ORDER_KEY = "galleryPhotoOrder";
  var INDEX_KEY = "galleryPhotoIndex";
  var INTERVAL_MS = 5000;
  var TICK_MS = 50;

  function readGalleryItems(rootId) {
    var root = document.getElementById(rootId);
    if (!root) return [];
    return Array.prototype.map.call(root.querySelectorAll(".gallery-meta-item"), function (el) {
      return {
        file: text(el, ".gallery-meta-file"),
        caption: text(el, ".gallery-meta-caption"),
        year: text(el, ".gallery-meta-year"),
        location: text(el, ".gallery-meta-location"),
        credit: text(el, ".gallery-meta-credit"),
        link: text(el, ".gallery-meta-link"),
      };
    });
  }

  function text(el, selector) {
    var node = el.querySelector(selector);
    return node ? (node.textContent || "").trim() : "";
  }

  function shuffle(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return arr;
  }

  function buildOrder(length) {
    var order = [];
    for (var i = 0; i < length; i++) order.push(i);
    return shuffle(order);
  }

  function loadSession(length) {
    var rawOrder = sessionStorage.getItem(ORDER_KEY);
    var index = parseInt(sessionStorage.getItem(INDEX_KEY) || "0", 10);
    var order;
    if (!rawOrder) {
      order = buildOrder(length);
      index = 0;
    } else {
      try {
        order = JSON.parse(rawOrder);
      } catch (e) {
        order = buildOrder(length);
        index = 0;
      }
      if (!Array.isArray(order) || order.length !== length) {
        order = buildOrder(length);
        index = 0;
      }
    }
    if (index < 0 || index >= length) index = 0;
    sessionStorage.setItem(ORDER_KEY, JSON.stringify(order));
    sessionStorage.setItem(INDEX_KEY, String(index));
    return { order: order, index: index };
  }

  function saveSession(order, index) {
    sessionStorage.setItem(ORDER_KEY, JSON.stringify(order));
    sessionStorage.setItem(INDEX_KEY, String(index));
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderChips(chipsEl, data) {
    if (!chipsEl) return;
    var chips = [];
    if (data.year) chips.push('<span class="gallery-chip">' + escapeHtml(data.year) + "</span>");
    if (data.location) chips.push('<span class="gallery-chip">' + escapeHtml(data.location) + "</span>");
    if (chips.length) {
      chipsEl.innerHTML = chips.join("");
      chipsEl.hidden = false;
    } else {
      chipsEl.innerHTML = "";
      chipsEl.hidden = true;
    }
  }

  function renderCaption(caption, data) {
    if (!caption) return;
    var text = data.caption || "";
    var hasCaption = Boolean(text || data.credit);
    caption.classList.toggle("gallery-caption--empty", !hasCaption);
    caption.innerHTML = "";
    if (!hasCaption) return;

    if (data.link && text) {
      caption.innerHTML =
        '<a class="gallery-caption-link" href="' +
        escapeHtml(data.link) +
        '" target="_blank" rel="noopener noreferrer">' +
        escapeHtml(text).replace(/\n/g, "<br>") +
        "</a>";
      if (data.credit) {
        caption.innerHTML += '<span class="gallery-credit"> — ' + escapeHtml(data.credit) + "</span>";
      }
    } else if (text) {
      caption.textContent = text;
      if (data.credit) {
        var credit = document.createElement("span");
        credit.className = "gallery-credit";
        credit.textContent = " — " + data.credit;
        caption.appendChild(credit);
      }
    } else if (data.credit) {
      caption.textContent = data.credit;
    }
  }

  function initGallery() {
    var items = readGalleryItems("gallery-photo-data");
    if (!items.length) return;

    var tile = document.getElementById("gallery-tile");
    var img = document.getElementById("random-photo");
    var caption = document.getElementById("random-photo-caption");
    var chips = document.getElementById("random-photo-chips");
    var nextBtn = document.getElementById("next-photo");
    var trigger = document.getElementById("gallery-photo-trigger");
    var timerEl = document.getElementById("gallery-timer");
    var timerBar = document.getElementById("gallery-timer-bar");
    var lightbox = document.getElementById("gallery-lightbox");
    var lightboxImg = document.getElementById("gallery-lightbox-img");
    var lightboxCaption = document.getElementById("gallery-lightbox-caption");
    var lightboxClose = document.getElementById("gallery-lightbox-close");
    var lightboxBackdrop = document.getElementById("gallery-lightbox-backdrop");

    if (!img) return;

    if (tile && tile.getAttribute("data-interval-ms")) {
      var parsed = parseInt(tile.getAttribute("data-interval-ms"), 10);
      if (parsed > 0) INTERVAL_MS = parsed;
    }

    var session = loadSession(items.length);
    var paused = false;
    var progress = 0;
    var tickId = null;

    function currentItem() {
      return items[session.order[session.index]];
    }

    function showItem(data) {
      if (!data || !data.file) return;
      img.src = data.file;
      img.alt = data.caption ? data.caption.split("\n")[0] : "Gallery photo";
      renderChips(chips, data);
      renderCaption(caption, data);
      if (lightbox && !lightbox.hidden && lightboxImg) {
        lightboxImg.src = data.file;
        lightboxImg.alt = img.alt;
        if (lightboxCaption) {
          lightboxCaption.textContent = data.caption || "";
        }
      }
    }

    function advance() {
      if (items.length <= 1) return;
      var nextIndex = session.index + 1;
      var order = session.order;
      if (nextIndex >= items.length) {
        order = buildOrder(items.length);
        nextIndex = 0;
      }
      session.order = order;
      session.index = nextIndex;
      saveSession(session.order, session.index);
      showItem(currentItem());
      resetTimer();
    }

    function resetTimer() {
      progress = 0;
      if (timerBar) timerBar.style.width = "0%";
    }

    function stopTimer() {
      if (tickId) {
        clearInterval(tickId);
        tickId = null;
      }
    }

    function startTimer() {
      stopTimer();
      if (items.length <= 1 || paused) return;
      tickId = setInterval(function () {
        if (paused) return;
        progress += TICK_MS;
        var pct = Math.min(100, (progress / INTERVAL_MS) * 100);
        if (timerBar) timerBar.style.width = pct + "%";
        if (progress >= INTERVAL_MS) advance();
      }, TICK_MS);
    }

    function openLightbox() {
      if (!lightbox || !lightboxImg) return;
      var data = currentItem();
      lightboxImg.src = data.file;
      lightboxImg.alt = img.alt;
      if (lightboxCaption) lightboxCaption.textContent = data.caption || "";
      lightbox.hidden = false;
      document.body.classList.add("gallery-lightbox-open");
      paused = true;
    }

    function closeLightbox() {
      if (!lightbox) return;
      lightbox.hidden = true;
      document.body.classList.remove("gallery-lightbox-open");
      paused = false;
      resetTimer();
      startTimer();
    }

    showItem(currentItem());
    resetTimer();
    startTimer();

    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        advance();
      });
    }

    if (trigger) {
      trigger.addEventListener("click", openLightbox);
    }

    if (lightboxClose) lightboxClose.addEventListener("click", closeLightbox);
    if (lightboxBackdrop) lightboxBackdrop.addEventListener("click", closeLightbox);

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && lightbox && !lightbox.hidden) closeLightbox();
    });

    if (timerEl && items.length > 1) timerEl.hidden = false;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGallery);
  } else {
    initGallery();
  }
})();
