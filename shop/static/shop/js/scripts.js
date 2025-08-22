document.addEventListener('DOMContentLoaded', function () {
  const navbar   = document.querySelector('.navbar');
  const hasHero  = document.querySelector('.hero-section');
  const isHome   = document.querySelector('.homepage-hero');

  // ---- Sticky offset (used by CSS var and scrolling) ----
  const updateStickTop = () => {
    const h = (navbar?.offsetHeight || 56);
    document.documentElement.style.setProperty('--stick-top', `${h}px`);
    return h;
  };
  let NAV_H = updateStickTop();
  window.addEventListener('resize', () => { NAV_H = updateStickTop(); });

  // ---- Navbar background on scroll ----
  function handleNavbarScroll() {
    if (window.scrollY > 50) navbar.classList.add('scrolled');
    else navbar.classList.remove('scrolled');
  }
  if (hasHero) {
    window.addEventListener('scroll', handleNavbarScroll);
    handleNavbarScroll();
  } else {
    navbar?.classList.add('scrolled');
  }

  // ---- Smooth scroll for generic anchors (skip category chips) ----
  document.querySelectorAll('a[href^="#"]:not(.category-link)').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      const y = target.getBoundingClientRect().top + window.pageYOffset - (NAV_H + 8);
      window.scrollTo({ top: y, behavior: 'smooth' });
    });
  });

  // ---- Homepage entrance animation ----
  if (!isHome) return;
  document.body.classList.add('lock-scroll');
  const heroHeading = document.querySelector('.hero-heading');
  const heroContent = document.querySelector('.hero-content');
  const revealNext  = document.querySelector('.reveal-next');

  setTimeout(() => { heroHeading?.classList.add('animate-to-position'); }, 100);
  setTimeout(() => { navbar?.classList.add('show-nav'); heroContent?.classList.add('show'); }, 1300);
  setTimeout(() => { revealNext?.classList.add('show'); document.body.classList.remove('lock-scroll'); }, 1800);
});

// Scroll to top button
function scrollToTop(){ window.scrollTo({ top: 0, behavior: 'smooth' }); }

/* ============================
   Category chips: active state,
   sticky offset, mobile centering
============================ */
(function () {
  const links = [...document.querySelectorAll('.category-link')];
  const rail  = document.querySelector('.category-rail');
  const navbar= document.querySelector('.navbar');
  if (!links.length || !rail) return;

  const getOffset = () => (navbar?.offsetHeight || 56) + 8;
  let OFFSET = getOffset();
  window.addEventListener('resize', () => { OFFSET = getOffset(); });

  // map anchors -> sections
  const map = new Map();
  links.forEach(a => {
    const id = a.dataset.anchor || a.getAttribute('href').slice(1);
    const section = document.getElementById(id);
    if (section) map.set(section, a);
  });

  const setActive = (link) => {
    links.forEach(l => l.classList.remove('active'));
    if (!link) return;
    link.classList.add('active');

    // Auto-scroll the rail so the active chip stays in view (near center)
    const r = rail.getBoundingClientRect();
    const b = link.getBoundingClientRect();
    const delta = (b.left + b.right) / 2 - (r.left + r.right) / 2;
    rail.scrollBy({ left: delta, behavior: 'smooth' });
  };

  // Click -> activate + smooth scroll to section with proper offset
  links.forEach(a => {
    a.addEventListener('click', e => {
      const id = a.dataset.anchor || a.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      setActive(a);
      const y = target.getBoundingClientRect().top + window.scrollY - OFFSET;
      window.scrollTo({ top: y, behavior: 'smooth' });
      history.replaceState(null, '', `#${id}`);
    });
  });

  // Keep the correct chip active while scrolling
  const io = new IntersectionObserver(entries => {
    const vis = entries
      .filter(e => e.isIntersecting)
      .sort((a,b)=> b.intersectionRatio - a.intersectionRatio)[0];
    if (vis) setActive(map.get(vis.target));
  }, { rootMargin: `-${Math.max(OFFSET-10,0)}px 0px -50% 0px`, threshold: [0, .25, .5, .75, 1] });

  map.forEach((_, section) => io.observe(section));

  // Initialize from hash or default to first
  const initId   = (location.hash || '').slice(1);
  const initLink = links.find(l => (l.dataset.anchor || l.getAttribute('href').slice(1)) === initId) || links[0];
  if (initLink) setActive(initLink);
})();
