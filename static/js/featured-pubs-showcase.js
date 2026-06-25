(function () {
  var SHOW_COUNT = 8;
  var list = document.getElementById("featured-pub-showcase");
  if (!list) return;

  var items = Array.from(list.querySelectorAll("[data-showcase-item]"));
  if (!items.length) return;

  var lightbox = document.getElementById("pub-figure-lightbox");
  var lightboxImg = document.getElementById("pub-figure-lightbox-img");
  var lightboxCaption = document.getElementById("pub-figure-lightbox-caption");
  var lightboxClose = document.getElementById("pub-figure-lightbox-close");
  var lightboxBackdrop = document.getElementById("pub-figure-lightbox-backdrop");

  function sortByYearDesc(els) {
    return els.slice().sort(function (a, b) {
      var ya = parseInt(a.getAttribute("data-year") || "0", 10);
      var yb = parseInt(b.getAttribute("data-year") || "0", 10);
      return yb - ya;
    });
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

  function hasFigure(el) {
    return el.getAttribute("data-has-figure") === "true";
  }

  function pickShowcaseItems(allItems) {
    if (allItems.length <= SHOW_COUNT) {
      return sortByYearDesc(allItems);
    }

    var withFigure = allItems.filter(hasFigure);
    if (!withFigure.length) {
      shuffle(allItems);
      return sortByYearDesc(allItems.slice(0, SHOW_COUNT));
    }

    var picked = [];
    var guaranteed = withFigure[Math.floor(Math.random() * withFigure.length)];
    picked.push(guaranteed);

    var pool = allItems.filter(function (el) {
      return el !== guaranteed;
    });
    shuffle(pool);
    for (var i = 0; i < pool.length && picked.length < SHOW_COUNT; i++) {
      picked.push(pool[i]);
    }

    return sortByYearDesc(picked);
  }

  function setFigureOpen(item, open) {
    var btn = item.querySelector("[data-pub-figure-toggle]");
    var panel = item.querySelector("[data-pub-figure-panel]");
    if (!btn || !panel) return;
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.textContent = open ? "Hide figure" : "Show figure";
  }

  function openLightboxFromTrigger(trigger) {
    if (!lightbox || !lightboxImg) return;
    var img = trigger.querySelector("img");
    lightboxImg.src = trigger.getAttribute("data-full-src") || (img ? img.src : "");
    lightboxImg.alt = trigger.getAttribute("data-full-alt") || (img ? img.alt : "");
    if (lightboxCaption) {
      lightboxCaption.textContent = trigger.getAttribute("data-caption") || "";
    }
    lightbox.hidden = false;
    document.body.classList.add("gallery-lightbox-open");
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.hidden = true;
    document.body.classList.remove("gallery-lightbox-open");
  }

  function applyShowcase() {
    closeLightbox();

    items.forEach(function (el) {
      setFigureOpen(el, false);
      el.hidden = true;
    });

    var picked = pickShowcaseItems(items);

    picked.forEach(function (el) {
      el.hidden = false;
      list.appendChild(el);
    });

    var visibleWithFigure = picked.filter(hasFigure);
    if (visibleWithFigure.length) {
      var autoItem = visibleWithFigure[Math.floor(Math.random() * visibleWithFigure.length)];
      setFigureOpen(autoItem, true);
    }
  }

  applyShowcase();

  var refreshBtn = document.getElementById("featured-pub-refresh");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", applyShowcase);
  }

  list.addEventListener("click", function (e) {
    var toggle = e.target.closest("[data-pub-figure-toggle]");
    if (toggle) {
      var item = toggle.closest("[data-showcase-item]");
      var panel = item && item.querySelector("[data-pub-figure-panel]");
      if (item && panel) {
        setFigureOpen(item, panel.hidden);
      }
      return;
    }

    var imgTrigger = e.target.closest("[data-pub-figure-img]");
    if (imgTrigger) {
      openLightboxFromTrigger(imgTrigger);
    }
  });

  if (lightboxClose) {
    lightboxClose.addEventListener("click", closeLightbox);
  }
  if (lightboxBackdrop) {
    lightboxBackdrop.addEventListener("click", closeLightbox);
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && lightbox && !lightbox.hidden) {
      closeLightbox();
    }
  });
})();
