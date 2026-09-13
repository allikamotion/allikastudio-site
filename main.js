// Allika Studio — shared site behavior
// Recreates the original Framer template's interactions in plain JS:
// menu overlay, scroll-reveal, services accordion, live Tallinn clock,
// draggable horizontal gallery, back-to-top.

document.addEventListener('DOMContentLoaded', () => {

  /* ---- mobile/full nav overlay ---- */
  const menuBtn = document.querySelector('[data-menu-open]');
  const closeBtn = document.querySelector('[data-menu-close]');
  const overlay = document.querySelector('.site-nav-overlay');
  if (menuBtn && overlay) {
    menuBtn.addEventListener('click', () => overlay.classList.add('open'));
  }
  if (closeBtn && overlay) {
    closeBtn.addEventListener('click', () => overlay.classList.remove('open'));
  }
  overlay?.querySelectorAll('a').forEach(a =>
    a.addEventListener('click', () => overlay.classList.remove('open'))
  );

  /* ---- scroll reveal ----
     Elements fade + rise into place as they enter the viewport.
     Siblings inside the same section get a small stagger so a
     row of cards/list-items arrives one after another, not all
     at once — much closer to how the original Framer motion felt. */
  const revealEls = document.querySelectorAll('[data-reveal]');
  if ('IntersectionObserver' in window && revealEls.length) {
    // group elements by their nearest section/parent to compute stagger index
    const groups = new Map();
    revealEls.forEach(el => {
      const group = el.closest('section, header, footer, nav, .project-media-secondary') || document.body;
      if (!groups.has(group)) groups.set(group, []);
      groups.get(group).push(el);
    });
    groups.forEach(list => {
      list.forEach((el, i) => {
        el.style.setProperty('--reveal-delay', `${Math.min(i, 14) * 0.09}s`);
      });
    });

    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -10% 0px' });
    revealEls.forEach(el => io.observe(el));

    // Elements already in view on first paint (e.g. the hero) would
    // otherwise reveal instantly with no visible motion — hold them
    // back one animation frame + a beat so the very first thing you
    // see is still an intentional fade/rise-in, not a jump-cut.
    requestAnimationFrame(() => {
      revealEls.forEach(el => {
        const r = el.getBoundingClientRect();
        const inView = r.top < window.innerHeight && r.bottom > 0;
        if (inView) el.style.transitionDelay = `calc(${getComputedStyle(el).getPropertyValue('--reveal-delay') || '0s'} + .1s)`;
      });
    });
  } else {
    revealEls.forEach(el => el.classList.add('is-visible'));
  }

  /* ---- services rows: hover expand (CSS), tap fallback for touch ---- */
  document.querySelectorAll('.service-row').forEach(row => {
    row.addEventListener('touchstart', () => {
      document.querySelectorAll('.service-row.is-open').forEach(other => {
        if (other !== row) other.classList.remove('is-open');
      });
      row.classList.toggle('is-open');
    }, { passive: true });
  });

  /* ---- live Tallinn clock ---- */
  const clockEls = document.querySelectorAll('[data-clock]');
  if (clockEls.length) {
    const tick = () => {
      const now = new Date().toLocaleTimeString('en-US', {
        timeZone: 'Europe/Tallinn', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true
      });
      clockEls.forEach(el => { el.textContent = `TALLINN ${now} [GMT +3:00]`; });
    };
    tick();
    setInterval(tick, 1000);
  }

  /* ---- back to top ---- */
  document.querySelectorAll('[data-to-top]').forEach(btn => {
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  });

  /* ---- draggable horizontal gallery (explorations page) ---- */
  document.querySelectorAll('.drag-gallery').forEach(gallery => {
    let isDown = false, startX, scrollLeft;
    const start = (x) => { isDown = true; gallery.classList.add('dragging'); startX = x - gallery.offsetLeft; scrollLeft = gallery.scrollLeft; };
    const end = () => { isDown = false; gallery.classList.remove('dragging'); };
    const move = (x) => { if (!isDown) return; const walk = (x - gallery.offsetLeft - startX); gallery.scrollLeft = scrollLeft - walk; };

    gallery.addEventListener('mousedown', e => start(e.pageX));
    gallery.addEventListener('mouseleave', end);
    gallery.addEventListener('mouseup', end);
    gallery.addEventListener('mousemove', e => { if (isDown) { e.preventDefault(); move(e.pageX); } });

    gallery.addEventListener('touchstart', e => start(e.touches[0].pageX), { passive: true });
    gallery.addEventListener('touchend', end);
    gallery.addEventListener('touchmove', e => move(e.touches[0].pageX), { passive: true });
  });
});

// ---------- hover-to-play video previews ----------
(function(){
  document.querySelectorAll('[data-hover-video]').forEach(function(wrap){
    var video = wrap.querySelector('video');
    if (!video) return;
    var play = function(){ var p = video.play(); if (p !== undefined) p.catch(function(){}); };
    var reset = function(){ video.pause(); try { video.currentTime = 0; } catch (e) {} };
    wrap.addEventListener('mouseenter', play);
    wrap.addEventListener('mouseleave', reset);
    wrap.addEventListener('touchstart', play, { passive: true });
    wrap.addEventListener('touchend', reset, { passive: true });
  });
})();

// ---------- double-click a video: watch full-size, with sound, in-page ----------
// No new tab/window is ever opened -- a single overlay is reused for every
// video on the page. Wrapping cards that are also links (project/work
// cards) still navigate normally on a single click; a second click inside
// the double-click window cancels that navigation and opens the lightbox
// instead.
(function(){
  var lightbox, lbVideo, lbClose;

  function buildLightbox(){
    if (lightbox) return;
    lightbox = document.createElement('div');
    lightbox.className = 'video-lightbox';
    lightbox.setAttribute('aria-hidden', 'true');
    lightbox.innerHTML =
      '<button type="button" class="video-lightbox-close" aria-label="Close">&times;</button>' +
      '<video class="video-lightbox-player" controls playsinline></video>';
    document.body.appendChild(lightbox);
    lbVideo = lightbox.querySelector('video');
    lbClose = lightbox.querySelector('.video-lightbox-close');

    function close(){
      lightbox.classList.remove('is-open');
      lbVideo.pause();
      lbVideo.removeAttribute('src');
      lbVideo.load();
      document.body.classList.remove('lightbox-open');
    }
    lbClose.addEventListener('click', close);
    lightbox.addEventListener('click', function(e){ if (e.target === lightbox) close(); });
    document.addEventListener('keydown', function(e){ if (e.key === 'Escape') close(); });
  }

  function openWithSound(video){
    buildLightbox();
    var srcEl = video.querySelector('source');
    var src = srcEl ? srcEl.src : video.currentSrc;
    if (!src) return;
    lbVideo.muted = false;
    lbVideo.src = src;
    lightbox.classList.add('is-open');
    document.body.classList.add('lightbox-open');
    var p = lbVideo.play();
    if (p !== undefined) p.catch(function(){});
  }

  document.querySelectorAll('[data-hover-video], [data-autoplay-video]').forEach(function(wrap){
    var video = wrap.querySelector('video');
    if (!video) return;
    var link = wrap.closest('a');

    if (!link) {
      // Not a link -- a plain native dblclick is all we need.
      wrap.addEventListener('dblclick', function(e){
        e.preventDefault();
        openWithSound(video);
      });
      return;
    }

    // Wrapped in a link (project/work card): tell single click from
    // double click apart so a normal click still navigates, but a
    // double click opens the video instead of following the link.
    var clickTimer = null;
    link.addEventListener('click', function(e){
      if (clickTimer) {
        clearTimeout(clickTimer);
        clickTimer = null;
        e.preventDefault();
        openWithSound(video);
        return;
      }
      e.preventDefault();
      var href = link.href;
      clickTimer = setTimeout(function(){
        clickTimer = null;
        window.location.href = href;
      }, 280);
    });
  });
})();

// ---------- hero pixel flicker ----------
(function(){
  var hero = document.querySelector('.hero');
  if (!hero) return;
  var colors = ['#4a7fe8','#f2c94c','#7fd1e0','#e06fa0','#e0503c','#7bc47f','#e0873c','#9b7fe0'];
  var count = 7;
  var pixels = [];
  for (var i = 0; i < count; i++) {
    var p = document.createElement('span');
    p.className = 'pixel-flicker';
    hero.appendChild(p);
    pixels.push(p);
  }
  function flashOne(){
    var p = pixels[Math.floor(Math.random() * pixels.length)];
    var color = colors[Math.floor(Math.random() * colors.length)];
    var x = 4 + Math.random() * 90;
    var y = 6 + Math.random() * 86;
    var size = 6 + Math.random() * 9;
    p.style.left = x + '%';
    p.style.top = y + '%';
    p.style.width = size + 'px';
    p.style.height = size + 'px';
    p.style.background = color;
    p.style.opacity = '1';
    window.setTimeout(function(){ p.style.opacity = '0'; }, 220 + Math.random() * 320);
  }
  window.setInterval(flashOne, 420);
  for (var j = 0; j < 4; j++) window.setTimeout(flashOne, j * 140);
})();

// ---------- header logo: video near top, text once scrolled ----------
(function(){
  var header = document.querySelector('.site-header');
  if (!header) return;
  var video = header.querySelector('.brand-mark');
  var threshold = 80;
  var wasScrolled = null;
  var firstCheck = true;
  function onScroll(){
    // On the very first check only, also treat "#services in the URL" as
    // scrolled: right after an anchor-driven page load the real scrollY
    // can briefly lag behind the anchor jump, and without this an early
    // onScroll() call could momentarily flip the header back to the video
    // and call .play() on it before the jump catches up. Later, genuine
    // scroll events rely on scrollY alone, so scrolling back to the top
    // still correctly restores the video even if the URL still ends in
    // #services.
    var isScrolled = window.scrollY > threshold ||
      (firstCheck && location.hash === '#services');
    firstCheck = false;
    if (isScrolled === wasScrolled) return;
    wasScrolled = isScrolled;
    header.classList.toggle('scrolled', isScrolled);
    // some browsers pause an off-screen (display:none) video; make sure it
    // resumes once it becomes visible again instead of staying frozen.
    if (!isScrolled && video) {
      var p = video.play();
      if (p !== undefined) p.catch(function(){});
    }
  }
  header.classList.add('js-ready');
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
  // Clicking a nav link to an anchor lower on the page (e.g. #services)
  // triggers a smooth-scroll that takes a few hundred ms to cross the
  // "scrolled" threshold above — during that time the animated video logo
  // would otherwise keep playing, showing as an unwanted flash of motion.
  // Switch to the text logo immediately on the hash change itself, before
  // the smooth-scroll animation even starts.
  window.addEventListener('hashchange', function(){
    if (location.hash && location.hash !== '#') {
      wasScrolled = true;
      header.classList.add('scrolled');
    }
  });
  // Clicking the "Services" nav link on this same page fires a native
  // smooth-scroll straight away, before 'hashchange' or 'scroll' events
  // reach us — that gap is exactly where the video logo still gets a
  // frame or two to play. Catch the click itself, synchronously, before
  // the browser's default action (the scroll) even starts.
  document.querySelectorAll('a[href$="#services"]').forEach(function(link){
    link.addEventListener('click', function(){
      wasScrolled = true;
      header.classList.add('scrolled');
      if (video) video.pause();
    });
  });
})();

// ---------- brand link: smooth-scroll to top instead of a full reload when already on this page ----------
(function(){
  var brand = document.querySelector('.site-header a.brand');
  if (!brand) return;
  brand.addEventListener('click', function(e){
    try {
      var linkUrl = new URL(brand.getAttribute('href'), window.location.href);
      var currentUrl = new URL(window.location.href);
      if (linkUrl.pathname === currentUrl.pathname) {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } catch (err) { /* if URL parsing fails for any reason, fall back to normal navigation */ }
  });
})();

// ---------- project pages: video plays by itself while it is on screen ----------
// Cards on the home page and the project list still play on hover; inside a
// project the videos start on their own, because that is the point of opening
// the page. Off-screen videos stay paused so a page with five clips does not
// download all of them at once.
(function(){
  var wraps = document.querySelectorAll('[data-autoplay-video]');
  if (!wraps.length) return;

  var play  = function(v){ var p = v.play(); if (p !== undefined) p.catch(function(){}); };
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Someone who asked their system to reduce motion should not get five clips
  // moving at once -- fall back to the hover behaviour for them.
  if (reduce) {
    wraps.forEach(function(wrap){
      var v = wrap.querySelector('video'); if (!v) return;
      wrap.addEventListener('mouseenter', function(){ play(v); });
      wrap.addEventListener('mouseleave', function(){ v.pause(); try { v.currentTime = 0; } catch (e) {} });
    });
    return;
  }

  if (!('IntersectionObserver' in window)) {
    wraps.forEach(function(wrap){ var v = wrap.querySelector('video'); if (v) play(v); });
    return;
  }

  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      var v = entry.target.querySelector('video');
      if (!v) return;
      if (entry.isIntersecting) play(v); else v.pause();
    });
  }, { threshold: 0.25 });
  wraps.forEach(function(wrap){ io.observe(wrap); });
})();
