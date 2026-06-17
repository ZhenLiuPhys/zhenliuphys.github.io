(function () {
  var TALKS_VIEW_STORAGE_KEY = "talksViewMode";
  var PUBS_VIEW_STORAGE_KEY = "pubsViewMode";

  function debounce(fn, ms) {
    var timer;
    return function () {
      var args = arguments;
      var self = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(self, args);
      }, ms);
    };
  }

  function getScope(input) {
    var id = input.getAttribute("data-list-search-scope");
    return id ? document.getElementById(id) : null;
  }

  function getRows(scope) {
    return scope.querySelectorAll(".pub-row, .talk-row");
  }

  function getActiveFilter(scope, attr) {
    if (!scope || !scope.id) return "all";
    var wrap = document.querySelector("[" + attr + '="' + scope.id + '"]');
    if (!wrap) return "all";
    var active = wrap.querySelector(".is-active[data-" + attr.split("-").slice(1).join("-") + "-btn], .is-active");
    if (!wrap.querySelector("[class*='-filter-btn'].is-active")) {
      active = wrap.querySelector(".is-active");
    }
    active = wrap.querySelector("button.is-active");
    if (!active) return "all";
    var valueAttr = Object.keys(active.dataset)[0];
    if (active.hasAttribute("data-talk-filter-value")) {
      return (active.getAttribute("data-talk-filter-value") || "all").toLowerCase();
    }
    if (active.hasAttribute("data-pub-tag-filter-value")) {
      return active.getAttribute("data-pub-tag-filter-value") || "all";
    }
    if (active.hasAttribute("data-pub-section-filter-value")) {
      return active.getAttribute("data-pub-section-filter-value") || "all";
    }
    return "all";
  }

  function getActiveTalkFilter(scope) {
    if (!scope || !scope.id) return "all";
    var wrap = document.querySelector('[data-talk-filter-scope="' + scope.id + '"]');
    if (!wrap) return "all";
    var active = wrap.querySelector("[data-talk-filter-btn].is-active");
    if (!active) return "all";
    return (active.getAttribute("data-talk-filter-value") || "all").toLowerCase();
  }

  function getActivePubTagFilter(scope) {
    if (!scope || !scope.id) return "all";
    var wrap = document.querySelector('[data-pub-tag-filter-scope="' + scope.id + '"]');
    if (!wrap) return "all";
    var active = wrap.querySelector("[data-pub-tag-filter-btn].is-active");
    if (!active) return "all";
    return active.getAttribute("data-pub-tag-filter-value") || "all";
  }

  function getActivePubSectionFilter(scope) {
    if (!scope || !scope.id) return "all";
    var wrap = document.querySelector('[data-pub-section-filter-scope="' + scope.id + '"]');
    if (!wrap) return "all";
    var active = wrap.querySelector("[data-pub-section-filter-btn].is-active");
    if (!active) return "all";
    return active.getAttribute("data-pub-section-filter-value") || "all";
  }

  function rowMatches(row, query, talkFilter, pubTagFilter, pubSectionFilter) {
    var text = row.getAttribute("data-search-text") || "";
    if (query && text.indexOf(query) === -1) return false;

    if (row.classList.contains("talk-row")) {
      if (!talkFilter || talkFilter === "all") return true;
      var category = (row.getAttribute("data-talk-category") || "other").toLowerCase();
      if (talkFilter === "scheduled") {
        return row.getAttribute("data-scheduled") === "true";
      }
      return category === talkFilter;
    }

    if (row.classList.contains("pub-row")) {
      if (pubTagFilter && pubTagFilter !== "all") {
        var tags = (row.getAttribute("data-pub-tags") || "").split(/\s+/).filter(Boolean);
        if (tags.indexOf(pubTagFilter) === -1) return false;
      }
      if (pubSectionFilter && pubSectionFilter !== "all") {
        var section = row.getAttribute("data-pub-section") || "";
        if (section !== pubSectionFilter) return false;
      }
    }

    return true;
  }

  function getLayout(scope, attr, fallback) {
    return scope.getAttribute(attr) || fallback;
  }

  function setTalksLayout(scope, mode) {
    scope.setAttribute("data-talks-layout", mode);
    scope.classList.remove("talks-view--list", "talks-view--by-year");
    scope.classList.add("talks-view--" + mode);
    try {
      sessionStorage.setItem(TALKS_VIEW_STORAGE_KEY, mode);
    } catch (e) {}
  }

  function setPubsLayout(scope, mode) {
    scope.setAttribute("data-pubs-layout", mode);
    scope.classList.remove("pubs-view--list", "pubs-view--by-year");
    scope.classList.add("pubs-view--" + mode);
    try {
      sessionStorage.setItem(PUBS_VIEW_STORAGE_KEY, mode);
    } catch (e) {}
  }

  function applyListViewLayout(scope, groupSelector) {
    scope.querySelectorAll(groupSelector).forEach(function (details) {
      details.setAttribute("open", "");
    });
  }

  function applyPubYearViewLayout(scope) {
    scope.querySelectorAll(".pub-year-group").forEach(function (details) {
      if (details.hidden) {
        details.removeAttribute("open");
      } else {
        details.setAttribute("open", "");
      }
    });
  }

  function applyByYearViewLayout(scope, groupSelector) {
    if (groupSelector === ".pub-year-group") {
      applyPubYearViewLayout(scope);
      return;
    }

    var opened = false;
    scope.querySelectorAll(groupSelector).forEach(function (details) {
      if (details.hidden) return;
      if (!opened) {
        details.setAttribute("open", "");
        opened = true;
      } else {
        details.removeAttribute("open");
      }
    });
  }

  function bindYearGroupAccordion(scope, config) {
    if (!scope) return;

    scope.querySelectorAll(config.groupSelector).forEach(function (yearGroup) {
      if (yearGroup.dataset.yearAccordionBound) return;
      yearGroup.dataset.yearAccordionBound = "1";
      yearGroup.addEventListener("toggle", function () {
        if (getLayout(scope, config.layoutAttr, "list") !== "by-year") return;
        if (!yearGroup.open) return;
        scope.querySelectorAll(config.groupSelector).forEach(function (other) {
          if (other !== yearGroup && !other.hidden && other.open) {
            other.removeAttribute("open");
          }
        });
      });
    });
  }

  function updateYearDividers(scope) {
    scope.querySelectorAll(".year-divider").forEach(function (divider) {
      var hasVisible = false;
      var el = divider.nextElementSibling;
      while (el && !el.classList.contains("year-divider")) {
        if (el.matches(".pub-row, .talk-row") && !el.hidden) {
          hasVisible = true;
          break;
        }
        el = el.nextElementSibling;
      }
      divider.hidden = !hasVisible;
    });
  }

  function initSectionCounts(scope) {
    scope.querySelectorAll(".section-count").forEach(function (el) {
      if (!el.dataset.totalCount) {
        el.dataset.totalCount = el.textContent.trim();
      }
    });
  }

  function updateSectionCounts(scope, filtering) {
    scope.querySelectorAll("details.section-collapse, details.talk-year-group, details.pub-year-group").forEach(function (details) {
      var countEl = details.querySelector(":scope > summary .section-count, :scope > .talk-year-summary .section-count, :scope > .pub-year-summary .section-count");
      if (!countEl) {
        countEl = details.querySelector(".section-count");
      }
      if (!countEl) return;
      var total = countEl.dataset.totalCount || countEl.textContent.trim();
      if (!countEl.dataset.totalCount) {
        countEl.dataset.totalCount = total;
      }
      total = countEl.dataset.totalCount;
      if (!filtering) {
        countEl.textContent = total;
        return;
      }
      var rowSel = details.classList.contains("talk-year-group")
        ? ".talk-row:not([hidden])"
        : ".pub-row:not([hidden]), .talk-row:not([hidden])";
      var visible = details.querySelectorAll(rowSel).length;
      countEl.textContent = visible + " / " + total;
    });
  }

  function updateYearGroups(scope, groupSelector, layoutAttr, rowSelector, filtering) {
    var groups = scope.querySelectorAll(groupSelector);
    if (!groups.length) return;

    var layout = getLayout(scope, layoutAttr, "list");

    groups.forEach(function (details) {
      var visible = details.querySelectorAll(rowSelector + ":not([hidden])").length;
      var countEl = details.querySelector(".section-count");
      if (countEl) {
        var total = countEl.dataset.totalCount || countEl.textContent.trim();
        if (!countEl.dataset.totalCount) {
          countEl.dataset.totalCount = total;
        }
        total = countEl.dataset.totalCount;
        countEl.textContent = filtering ? visible + " / " + total : total;
      }

      if (filtering) {
        if (visible > 0) {
          details.hidden = false;
          details.classList.add("has-search-match");
          if (groupSelector === ".pub-year-group") {
            details.setAttribute("open", "");
          }
        } else {
          details.classList.remove("has-search-match");
          details.removeAttribute("open");
          details.hidden = true;
        }
        return;
      }

      details.hidden = false;
      details.classList.remove("has-search-match");
    });

    if (groupSelector === ".pub-year-group") {
      applyPubYearViewLayout(scope);
    } else if (layout === "list") {
      applyListViewLayout(scope, groupSelector);
    } else {
      applyByYearViewLayout(scope, groupSelector);
    }
  }

  function updateDetailsSections(scope, filtering) {
    scope.querySelectorAll("details.section-collapse").forEach(function (details) {
      var visible = details.querySelectorAll(".pub-row:not([hidden]), .talk-row:not([hidden])").length;
      if (!filtering) {
        details.classList.remove("has-search-match");
        var defOpen = details.getAttribute("data-default-open") === "true";
        if (defOpen) {
          details.setAttribute("open", "");
        } else {
          details.removeAttribute("open");
        }
        details.hidden = false;
        return;
      }
      if (visible > 0) {
        details.setAttribute("open", "");
        details.classList.add("has-search-match");
        details.hidden = false;
      } else {
        details.classList.remove("has-search-match");
        details.removeAttribute("open");
        details.hidden = true;
      }
    });
  }

  function setRecentVisibility(input, filtering) {
    var sel = input.getAttribute("data-list-search-recent-hide");
    if (!sel) return;
    var recent = document.querySelector(sel);
    if (recent) {
      recent.classList.toggle("is-search-hidden", filtering);
    }
    var scope = getScope(input);
    var details = scope ? scope.closest("details") : null;
    if (!details) return;
    if (filtering) {
      details.setAttribute("open", "");
      return;
    }
    var defOpen = details.getAttribute("data-default-open") === "true";
    if (defOpen) {
      details.setAttribute("open", "");
    } else {
      details.removeAttribute("open");
    }
  }

  function updateStatus(input, visible, total, filtering) {
    var statusId = input.getAttribute("data-list-search-status");
    var status = statusId ? document.getElementById(statusId) : null;
    if (!status) return;
    var label = input.getAttribute("data-list-search-item-label") || "items";
    if (!filtering) {
      status.textContent = "";
      return;
    }
    if (visible === 0) {
      status.textContent = "No matching " + label + ".";
      return;
    }
    status.textContent = "Showing " + visible + " of " + total + " " + label + ".";
  }

  function applyFilter(input) {
    var scope = getScope(input);
    if (!scope) return;

    var query = input.value.trim().toLowerCase();
    var talkFilter = getActiveTalkFilter(scope);
    var pubTagFilter = getActivePubTagFilter(scope);
    var pubSectionFilter = getActivePubSectionFilter(scope);
    var filtering =
      query.length > 0 ||
      talkFilter !== "all" ||
      pubTagFilter !== "all" ||
      pubSectionFilter !== "all";
    var rows = getRows(scope);
    var visible = 0;

    rows.forEach(function (row) {
      var match = rowMatches(row, query, talkFilter, pubTagFilter, pubSectionFilter);
      row.hidden = !match;
      if (match) visible += 1;
    });

    scope.classList.toggle("is-filtering", filtering);
    updateYearDividers(scope);
    updateDetailsSections(scope, filtering);
    updateYearGroups(scope, ".talk-year-group", "data-talks-layout", ".talk-row", filtering);
    updateYearGroups(scope, ".pub-year-group", "data-pubs-layout", ".pub-row", filtering);
    updateSectionCounts(scope, filtering);
    setRecentVisibility(input, filtering);
    updateStatus(input, visible, rows.length, filtering);
  }

  function bindViewToggle(scope, input, config) {
    if (!scope || !scope.id) return;
    var wrap = document.querySelector("[" + config.toggleAttr + '="' + scope.id + '"]');
    if (!wrap) return;

    var saved = "list";
    try {
      saved = sessionStorage.getItem(config.storageKey) || "list";
    } catch (e) {}
    if (saved !== "list" && saved !== "by-year") saved = "list";

    config.setLayout(scope, saved);
    wrap.querySelectorAll("[" + config.viewAttr + "]").forEach(function (btn) {
      var view = btn.getAttribute(config.viewAttr);
      var active = view === saved;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    if (saved === "by-year") {
      applyByYearViewLayout(scope, config.groupSelector);
    } else {
      applyListViewLayout(scope, config.groupSelector);
    }

    wrap.querySelectorAll("[" + config.viewAttr + "]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var view = btn.getAttribute(config.viewAttr);
        if (!view || view === getLayout(scope, config.layoutAttr, "list")) return;

        wrap.querySelectorAll("[" + config.viewAttr + "]").forEach(function (b) {
          var v = b.getAttribute(config.viewAttr);
          var active = v === view;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-pressed", active ? "true" : "false");
        });

        config.setLayout(scope, view);
        if (view === "list") {
          applyListViewLayout(scope, config.groupSelector);
        } else {
          applyByYearViewLayout(scope, config.groupSelector);
        }

        applyFilter(input);
      });
    });
  }

  function bindChipFilters(scope, input, scopeAttr, btnAttr) {
    if (!scope || !scope.id) return;
    var wrap = document.querySelector("[" + scopeAttr + '="' + scope.id + '"]');
    if (!wrap) return;
    wrap.querySelectorAll("[" + btnAttr + "]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        wrap.querySelectorAll("[" + btnAttr + "]").forEach(function (b) {
          b.classList.remove("is-active");
          b.setAttribute("aria-selected", "false");
        });
        btn.classList.add("is-active");
        btn.setAttribute("aria-selected", "true");
        applyFilter(input);
      });
    });
  }

  function bindSearch(input) {
    var scope = getScope(input);
    if (!scope) return;
    initSectionCounts(scope);

    bindChipFilters(scope, input, "data-talk-filter-scope", "data-talk-filter-btn");
    bindChipFilters(scope, input, "data-pub-tag-filter-scope", "data-pub-tag-filter-btn");
    bindChipFilters(scope, input, "data-pub-section-filter-scope", "data-pub-section-filter-btn");

    bindViewToggle(scope, input, {
      toggleAttr: "data-talk-view-toggle",
      storageKey: TALKS_VIEW_STORAGE_KEY,
      viewAttr: "data-talk-view",
      layoutAttr: "data-talks-layout",
      groupSelector: ".talk-year-group",
      setLayout: setTalksLayout,
    });

    if (scope.id === "talk-full-list-scope") {
      bindYearGroupAccordion(scope, {
        layoutAttr: "data-talks-layout",
        groupSelector: ".talk-year-group",
      });
    }

    var run = debounce(function () {
      applyFilter(input);
    }, 150);

    input.addEventListener("input", run);

    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        input.value = "";
        applyFilter(input);
        input.focus();
      }
    });

    applyFilter(input);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-list-search-input]").forEach(bindSearch);
  });
})();
