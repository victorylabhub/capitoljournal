(function () {
  "use strict";
  var DAY = 86400000;

  // Today's date in the utility bar (Eastern Time)
  var todayEl = document.querySelector("[data-today]");
  if (todayEl) {
    try {
      todayEl.textContent = new Intl.DateTimeFormat("en-US", {
        weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "America/New_York"
      }).format(new Date());
    } catch (e) { /* leave empty */ }
  }

  // Days until Election Day, counted in Eastern Time
  function etMidnight(d) {
    var p = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", year: "numeric", month: "numeric", day: "numeric" })
      .formatToParts(d).reduce(function (o, x) { o[x.type] = x.value; return o; }, {});
    return Date.UTC(+p.year, +p.month - 1, +p.day);
  }
  function daysTo(iso) {
    var p = iso.split("-");
    return Math.round((Date.UTC(+p[0], +p[1] - 1, +p[2]) - etMidnight(new Date())) / DAY);
  }
  document.querySelectorAll("[data-countdown]").forEach(function (el) {
    var d = daysTo(el.dataset.countdown);
    el.textContent = d > 1 ? d + " days until Election Day, Tuesday, Nov. 3"
      : d === 1 ? "Election Day is tomorrow, Tuesday, Nov. 3"
      : d === 0 ? "Today is Election Day" : "Election Day was Tuesday, Nov. 3";
  });
  document.querySelectorAll("[data-countdown-num]").forEach(function (el) {
    var d = daysTo(el.dataset.countdownNum), lab = el.parentNode.querySelector("[data-countdown-label]");
    if (d > 0) { el.textContent = d + (d === 1 ? " day" : " days"); if (lab) lab.textContent = "Until Election Day"; }
    else if (d === 0) { el.textContent = "Today"; if (lab) lab.textContent = "Election Day"; }
  });
  document.querySelectorAll("[data-elex-status]").forEach(function (el) {
    var d = daysTo(el.dataset.elexStatus);
    if (d <= 0) {
      el.closest(".status").classList.add("live");
      el.innerHTML = "<strong>Status:</strong> " + (d === 0
        ? "Polls are open or closing across the country. Results appear on each state’s official site after its polls close; they are unofficial until certified."
        : "Counting and certification are under way. Results posted by states are unofficial until each state certifies them.");
    }
  });

  // Mobile menu
  var btn = document.querySelector("[data-menu]"), nav = document.getElementById("site-nav");
  if (btn && nav) btn.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // Share buttons (plain links, no third-party scripts)
  document.querySelectorAll("[data-share]").forEach(function (box) {
    var u = encodeURIComponent(location.href), t = encodeURIComponent(document.title);
    box.querySelectorAll("[data-net]").forEach(function (a) {
      var n = a.dataset.net;
      if (n === "x") a.href = "https://twitter.com/intent/tweet?url=" + u + "&text=" + t;
      if (n === "fb") a.href = "https://www.facebook.com/sharer/sharer.php?u=" + u;
      if (n === "mail") a.href = "mailto:?subject=" + t + "&body=" + u;
      if (n === "copy") a.addEventListener("click", function () {
        var done = function () { var o = a.textContent; a.textContent = "Link copied"; setTimeout(function () { a.textContent = o; }, 1800); };
        if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done, done); else done();
      });
    });
  });

  // State filter on the results table
  document.querySelectorAll("[data-filter]").forEach(function (inp) {
    var rows = document.querySelectorAll(inp.dataset.filter);
    inp.addEventListener("input", function () {
      var q = inp.value.trim().toLowerCase();
      rows.forEach(function (r) { r.hidden = q && r.dataset.name.indexOf(q) === -1; });
    });
  });
})();
