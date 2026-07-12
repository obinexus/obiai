(function () {
  var searchInput = document.getElementById("site-search");
  var searchResults = document.getElementById("search-results");
  var navToggle = document.querySelector(".nav-toggle");
  var siteNav = document.getElementById("site-nav");
  var searchIndex = [];

  if (navToggle && siteNav) {
    navToggle.addEventListener("click", function () {
      var isOpen = siteNav.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  document.querySelectorAll("pre").forEach(function (block) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "Copy";
    button.addEventListener("click", function () {
      var code = block.querySelector("code");
      if (!code) return;
      navigator.clipboard.writeText(code.textContent || "").then(function () {
        button.textContent = "Copied";
        window.setTimeout(function () {
          button.textContent = "Copy";
        }, 1400);
      });
    });
    block.appendChild(button);
  });

  if (searchInput && searchResults) {
    fetch(window.OBI_SEARCH_URL || "search.json")
      .then(function (response) {
        return response.ok ? response.json() : [];
      })
      .then(function (records) {
        searchIndex = Array.isArray(records) ? records : [];
      })
      .catch(function () {
        searchIndex = [];
      });

    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim().toLowerCase();
      if (query.length < 2) {
        searchResults.innerHTML = "";
        return;
      }
      var terms = query.split(/\s+/).filter(Boolean);
      var results = searchIndex
        .map(function (record) {
          var haystack = [record.title, record.summary, record.text, record.kind]
            .join(" ")
            .toLowerCase();
          var score = terms.reduce(function (total, term) {
            return total + (haystack.includes(term) ? 1 : 0);
          }, 0);
          return Object.assign({ score: score }, record);
        })
        .filter(function (record) {
          return record.score > 0;
        })
        .sort(function (a, b) {
          return b.score - a.score || a.title.localeCompare(b.title);
        })
        .slice(0, 8);

      searchResults.innerHTML = results
        .map(function (record, index) {
          return '<a class="search-result" role="option" id="search-result-' +
            index +
            '" href="' +
            record.href +
            '"><strong>' +
            escapeHtml(record.title) +
            "</strong><span>" +
            escapeHtml(record.summary || record.kind || "") +
            "</span></a>";
        })
        .join("");
    });

    searchInput.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowDown") return;
      var first = searchResults.querySelector("a");
      if (first) {
        event.preventDefault();
        first.focus();
      }
    });
  }

  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a[href^='#']"));
  var sections = tocLinks
    .map(function (link) {
      var target = document.querySelector(link.getAttribute("href"));
      return target ? { link: link, target: target } : null;
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length > 0) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          sections.forEach(function (item) {
            item.link.classList.toggle("active", item.target === entry.target);
          });
        });
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: 0.01 },
    );
    sections.forEach(function (item) {
      observer.observe(item.target);
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }
})();