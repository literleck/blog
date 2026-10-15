// Lord Literleck: the shared header and the phone footer.
// The strings below are content and may change after the freeze; the markup is frozen.
(function () {
  "use strict";

  var NAME = "Lord Literleck";
  var TAGLINE = "// learning to make games from scratch";
  // Path from the site root to the sigil image. Empty hides the slot until the sigil exists.
  var SIGIL = "";
  var MENU = [["Devlog", "index.html"], ["Games", "games.html"], ["About", "about.html"]];
  // A link appears once its account exists. Add more lines as accounts are created.
  var LINKS = [
    ["github", "https://github.com/kganitis"],
    ["rss", "feed.xml"]
  ];

  var root = document.body.getAttribute("data-root") || "";
  var current = document.body.getAttribute("data-page") || "";

  function href(url) { return /^[a-z]+:/i.test(url) ? url : root + url; }

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs).forEach(function (k) { if (attrs[k] !== null) e.setAttribute(k, attrs[k]); });
    if (text) e.textContent = text;
    return e;
  }

  function links() {
    var box = el("span", { "class": "links" });
    LINKS.forEach(function (l) {
      box.appendChild(el("a", { href: href(l[1]), rel: /^https?:/.test(l[1]) ? "me" : null }, l[0]));
    });
    return box;
  }

  var head = document.getElementById("site");
  if (head) {
    head.textContent = "";
    var top = el("div", { "class": "top" });
    if (SIGIL) top.appendChild(el("img", { "class": "sigil", src: href(SIGIL), alt: "" }));
    var who = el("div", {});
    who.appendChild(el("a", { "class": "name", href: href("index.html") }, NAME));
    who.appendChild(el("div", { "class": "tagline" }, TAGLINE));
    top.appendChild(who);
    head.appendChild(top);
    var bar = el("nav", { "class": "bar", "aria-label": "Site" });
    var menu = el("span", { "class": "menu" });
    MENU.forEach(function (m) {
      menu.appendChild(el("a", { href: href(m[1]), "aria-current": m[0].toLowerCase() === current ? "page" : null }, m[0]));
    });
    bar.appendChild(menu);
    bar.appendChild(links());
    head.appendChild(bar);
  }

  var foot = document.getElementById("foot");
  if (foot) {
    foot.textContent = "";
    var nav = el("nav", { "aria-label": "Elsewhere" });
    nav.appendChild(links());
    foot.appendChild(nav);
  }
})();
