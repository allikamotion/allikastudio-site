// Allika Studio — live legal text for the Benzina app pages.
//
// Every /benzina/*/index.html page ships with a full, static copy of the legal
// text baked into the HTML, so it is readable with JavaScript switched off, with
// no network, and by anything that does not run scripts. This file then fetches
// the source of truth — the JSON document on GitHub — and re-renders the page
// from it, so editing that document updates the site without a redeploy.
//
// If the fetch fails for any reason the baked-in copy simply stays on screen.
// The renderer below must stay in step with render() in build_legal.py.
(function () {
  var host = document.querySelector('[data-legal]');
  if (!host || !window.fetch) return;

  var key = host.getAttribute('data-legal');          // privacyPolicy | termsOfService
  var src = host.getAttribute('data-legal-src');
  if (!key || !src) return;

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  // turns bare URLs and email addresses in the source text into real links
  function linkify(s) {
    return s.replace(/(https?:\/\/[^\s<>()\[\]]+[^\s<>()\[\].,;:!?])|([\w.+-]+@[\w-]+(?:\.[\w-]+)+)/g,
      function (m, url, mail) {
        if (url) return '<a href="' + url + '" target="_blank" rel="noopener">' + url + '</a>';
        return '<a href="mailto:' + mail + '">' + mail + '</a>';
      });
  }

  function render(text) {
    var out = [];
    var blocks = text.replace(/\r\n/g, '\n').trim().split(/\n\s*\n/);
    for (var bi = 0; bi < blocks.length; bi++) {
      var lines = blocks[bi].split('\n')
        .map(function (l) { return l.trim(); })
        .filter(function (l) { return l.length; });
      if (!lines.length) continue;

      // drop the document's own title — the page already has an <h1>
      if (bi === 0 && lines.length === 1 && lines[0].length < 60 && !/[.:!?]$/.test(lines[0])) continue;

      var i = 0;
      if (lines.length > 1 && lines[0].length < 70 && !/[.:!?]$/.test(lines[0])) {
        out.push('<h2>' + esc(lines[0]) + '</h2>');
        i = 1;
      }
      var buf = [];
      var flush = function () {
        if (!buf.length) return;
        out.push('<ul>' + buf.map(function (x) {
          return '<li>' + linkify(esc(x)) + '</li>';
        }).join('') + '</ul>');
        buf = [];
      };
      for (; i < lines.length; i++) {
        if (lines[i].indexOf('- ') === 0) {
          buf.push(lines[i].slice(2).trim());
        } else {
          flush();
          out.push('<p>' + linkify(esc(lines[i])) + '</p>');
        }
      }
      flush();
    }
    return out.join('\n');
  }

  fetch(src, { cache: 'no-cache' })
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (data) {
      var text = data && data.legal && data.legal[key];
      if (typeof text !== 'string' || text.trim().length < 200) return;  // never blank the page
      var html = render(text);
      if (html.length < 200) return;
      host.innerHTML = html;
    })
    .catch(function () {
      // keep the baked-in copy; nothing to do
    });
})();
