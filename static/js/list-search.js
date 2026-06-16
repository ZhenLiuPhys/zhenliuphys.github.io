(function () {
  var TALKS_VIEW_STORAGE_KEY = "talksViewMode";

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

  function getActiveTalkFilter(scope) {
    if (!scope || !scope.id) return "all";
    var wrap = document.querySelector('[data-talk-filter-scope="' + scope.id + '"]');
    if (!wrap) return "all";
    var active = wrap.querySelector("[data-talk-filter-btn].is-active");
    if (!active) return "all";
    return (active.getAttribute("data-talk-filter-value") || "all").toLowerCase();
  }

  function rowMatches(row, query, talkFilter) {
    var text = row.getAttribute("data-search-text") || "";
    if (query && text.indexOf(query) === -1) return false;
    if (!row.classList.contains("talk-row")) return true;
    if (!talkFilter || talkFilter === "all") return true;
    var category = (row.getAttribute("data-talk-category") || "other").toLowerCase();
    if (talkFilter === "scheduled") {
      return row.getAttribute("data-scheduled") === "true";
    }
    return category === talkFilter;
  }

  function getTalksLayout(scope) {
    return scope.getAttribute("data-talks-layout") || "list";
  }

  function setTalksLayout(scope, mode) {
    scope.setAttribute("data-talks-layout", mode);
    scope.classList.remove("talks-view--list", "talks-view--by-year");
    scope.classList.add("talks-view--" + mode);
    try {
      sessionStorage.setItem(TALKS_VIEW_STORAGE_KEY, mode);
    } catch (e) {}
  }

  function applyListViewLayout(scope) {
    scope.querySelectorAll(".talk-year-group").forEach(function (details) {
      details.setAttribute("open", "");
    });
  }

  function applyByYearViewLayout(scope) {
    var opened = false;
    scope.querySelectorAll(".talk-year-group").forEach(function (details) {
      if (details.hidden) return;
      if (!opened) {
        details.setAttribute("open", "");
        opened = true;
      } else {
        details.removeAttribute("open");
      }
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
    scope.querySelectorAll("details.section-collapse").forEach(function (details) {
      var countEl = details.querySelector(".section-count");
      if (!countEl) return;
      var total = countEl.dataset.totalCount || countEl.textContent.trim();
      if (!filtering) {
        countEl.textContent = total;
        return;
      }
      var visible = details.querySelectorAll(".pub-row:not([hidden]), .talk-row:not([hidden])").length;
      countEl.textContent = visible + " / " + total;
    });
  }

  function updateTalkYearGroups(scope, filtering) {
    var groups = scope.querySelectorAll(".talk-year-group");
    if (!groups.length) return;

    var layout = getTalksLayout(scope);

    groups.forEach(function (details) {
      var visible = details.querySelectorAll(".talk-row:not([hidden])").length;
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
          if (layout === "by-year") {
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

    if (layout === "list") {
      applyListViewLayout(scope);
    } else {
      applyByYearViewLayout(scope);
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
    var filtering = query.length > 0 || talkFilter !== "all";
    var rows = getRows(scope);
    var visible = 0;

    rows.forEach(function (row) {
      var match = rowMatches(row, query, talkFilter);
      row.hidden = !match;
      if (match) visible += 1;
    });

    scope.classList.toggle("is-filtering", filtering);
    updateYearDividers(scope);
    updateDetailsSections(scope, filtering);
    updateTalkYearGroups(scope, filtering);
    updateSectionCounts(scope, filtering);
    setRecentVisibility(input, filtering);
    updateStatus(input, visible, rows.length, filtering);
  }

  function bindTalkViewToggle(scope, input) {
    if (!scope || !scope.id) return;
    var wrap = document.querySelector('[data-talk-view-toggle="' + scope.id + '"]');
    if (!wrap) return;

    var saved = "list";
    try {
      saved = sessionStorage.getItem(TALKS_VIEW_STORAGE_KEY) || "list";
    } catch (e) {}
    if (saved !== "list" && saved !== "by-year") saved = "list";

    setTalksLayout(scope, saved);
    wrap.querySelectorAll("[data-talk-view]").forEach(function (btn) {
      var view = btn.getAttribute("data-talk-view");
      var active = view === saved;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });

    if (saved === "by-year") {
      applyByYearViewLayout(scope);
    } else {
      applyListViewLayout(scope);
    }

    wrap.querySelectorAll("[data-talk-view]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var view = btn.getAttribute("data-talk-view");
        if (!view || view === getTalksLayout(scope)) return;

        wrap.querySelectorAll("[data-talk-view]").forEach(function (b) {
          var v = b.getAttribute("data-talk-view");
          var active = v === view;
          b.classList.toggle("is-active", active);
          b.setAttribute("aria-pressed", active ? "true" : "false");
        });

        setTalksLayout(scope, view);
        if (view === "list") {
          applyListViewLayout(scope);
        } else {
          applyByYearViewLayout(scope);
        }

        applyFilter(input);
      });
    });
  }

  function bindTalkFilters(scope, input) {
    if (!scope || !scope.id) return;
    var wrap = document.querySelector('[data-talk-filter-scope="' + scope.id + '"]');
    if (!wrap) return;
    wrap.querySelectorAll("[data-talk-filter-btn]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        wrap.querySelectorAll("[data-talk-filter-btn]").forEach(function (b) {
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
    bindTalkFilters(scope, input);
    bindTalkViewToggle(scope, input);

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
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-list-search-input]").forEach(bindSearch);
  });
})();
