// ======================================================
// EARTH STORE — Frontend scripts (cleaned & organized)
// - intro / navbar
// - ajax search
// - category chips
// - cart (live totals + soft AJAX sync)
// - checkout (WhatsApp / Email from cart) + i18n-safe
// - back-to-top (global scrollToTop())
// ======================================================

document.addEventListener('DOMContentLoaded', () => {
  // Guard each init so one failure never blocks the others
  try { IntroNavbar.init(); } catch (e) { console.error('IntroNavbar.init failed:', e); }
  try { CategoryChips.init(); } catch (e) { console.error('CategoryChips.init failed:', e); }
  try { Cart.init(); } catch (e) { console.error('Cart.init failed:', e); }
  try { SmoothAnchors.init(); } catch (e) { console.error('SmoothAnchors.init failed:', e); }
  try { Checkout.init(); } catch (e) { console.error('Checkout.init failed:', e); }
  try { BackToTop.init(); } catch (e) { console.error('BackToTop.init failed:', e); }
});

/* -----------------------------------
   Helpers
----------------------------------- */
const Utils = (() => {
  const getCookie = (name) => {
    const m = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  };

  const postForm = async (form, extraHeaders = {}) => {
    const fd = new FormData(form);
    // Prefer cookie; Django also accepts body token in FormData
    const csrf = getCookie('csrftoken') || fd.get('csrfmiddlewaretoken') || '';
    const headers = { 'X-Requested-With': 'XMLHttpRequest', ...extraHeaders };
    if (csrf) headers['X-CSRFToken'] = csrf;

    const resp = await fetch(form.action, { method: 'POST', body: fd, headers });
    // Try JSON; if not JSON, return raw text
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('application/json')) return resp.json();
    return resp.text();
  };

  // robust parse/format for Euro numbers
  const euroFormatter = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' });
  const formatEuro = (n) => euroFormatter.format(Number.isFinite(n) ? n : 0);

  const parseEuro = (str) => {
    // keep digits, comma for decimal, minus sign
    const s = String(str).replace(/[^\d,.-]/g, '').replace(/\.(?=\d{3}(\D|$))/g, '');
    const withDot = s.replace(',', '.');
    const n = parseFloat(withDot);
    return Number.isFinite(n) ? n : 0;
  };

  return { getCookie, postForm, formatEuro, parseEuro };
})();

/* -----------------------------------
   Intro / Navbar / Sticky offset
----------------------------------- */
const IntroNavbar = (() => {
  let NAV_H = 56;

  const setStickTop = () => {
    const navbar = document.querySelector('.navbar');
    const h = (navbar?.offsetHeight || 56);
    document.documentElement.style.setProperty('--stick-top', `${h}px`);
    NAV_H = h;
  };

  const handleNavbarScroll = () => {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;
    if (window.scrollY > 50) navbar.classList.add('scrolled');
    else navbar.classList.remove('scrolled');
  };

  const init = () => {
    const navbar  = document.querySelector('.navbar');
    const hasHero = document.querySelector('.hero-section');
    const isHome  = document.querySelector('.homepage-hero');
    const body    = document.body;

    const SKIP_KEY = 'es_skip_intro';
    const params = new URLSearchParams(location.search);
    const hasQuery = params.has('q') && params.get('q').trim() !== '';
    let skipIntro  = body.classList.contains('skip-intro') || hasQuery || (sessionStorage.getItem(SKIP_KEY) === '1');
    if (skipIntro) { try { sessionStorage.removeItem(SKIP_KEY); } catch (_) {} }

    setStickTop();
    window.addEventListener('resize', setStickTop);

    const showNavbarNow    = () => navbar?.classList.add('show-nav');
    const solidNavbarNow   = () => navbar?.classList.add('scrolled');
    const revealContentNow = () => document.querySelector('.reveal-next')?.classList.add('show');
    const unlockScroll     = () => body.classList.remove('lock-scroll');

    if (hasHero && !skipIntro) {
      window.addEventListener('scroll', handleNavbarScroll);
      handleNavbarScroll();
    } else {
      solidNavbarNow();
    }

    if (isHome && !skipIntro) {
      body.classList.add('lock-scroll');
      const heroHeading = document.querySelector('.hero-heading');
      const heroContent = document.querySelector('.hero-content');
      const revealNext  = document.querySelector('.reveal-next');

      setTimeout(() => { heroHeading?.classList.add('animate-to-position'); }, 100);
      setTimeout(() => { showNavbarNow(); heroContent?.classList.add('show'); }, 1300);
      setTimeout(() => { revealNext?.classList.add('show'); unlockScroll(); }, 1800);
    } else {
      showNavbarNow();
      revealContentNow();
      unlockScroll();
    }
  };

  return { init, get NAV_H() { return NAV_H; } };
})();

/* -----------------------------------
   Smooth anchors (excluding category chips)
----------------------------------- */
const SmoothAnchors = (() => {
  const init = () => {
    document.querySelectorAll('a[href^="#"]:not(.category-link)').forEach(a => {
      a.addEventListener('click', (e) => {
        const target = document.querySelector(a.getAttribute('href'));
        if (!target) return;
        e.preventDefault();
        const y = target.getBoundingClientRect().top + window.pageYOffset - (IntroNavbar.NAV_H + 8);
        window.scrollTo({ top: y, behavior: 'smooth' });
      });
    });
  };
  return { init };
})();

/* -----------------------------------
   AJAX search (no reload)
----------------------------------- */
(() => {
  const form = document.getElementById('shop-search-form');
  const results = document.getElementById('shop-results');
  if (!form || !results) return;

  const ajaxUrl = form.dataset.ajaxUrl || form.action;
  const qInput  = form.querySelector('input[name="q"]');

  let controller;
  const setLoading = (on) => results.classList.toggle('is-loading', !!on);

  const render = (html) => {
    results.innerHTML = html;
    CategoryChips.init(); // re-bind after DOM swap
  };

  const doSearch = async (q) => {
    const qs = q ? ('?q=' + encodeURIComponent(q)) : '';
    history.replaceState(null, '', qs + location.hash);

    controller?.abort?.();
    controller = new AbortController();

    setLoading(true);
    try {
      const resp = await fetch(`${ajaxUrl}?q=${encodeURIComponent(q)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: controller.signal
      });
      render(await resp.text());
    } catch (e) {
      if (e.name !== 'AbortError') console.error(e);
    } finally {
      setLoading(false);
    }
  };

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    doSearch((qInput?.value || '').trim());
  });

  let t;
  qInput?.addEventListener('input', (e) => {
    clearTimeout(t);
    t = setTimeout(() => doSearch((e.target.value || '').trim()), 320);
  });
})();

/* -----------------------------------
   Category chips (callable after AJAX)
----------------------------------- */
const CategoryChips = (() => {
  const init = () => {
    const links  = [...document.querySelectorAll('.category-link')];
    const rail   = document.querySelector('.category-rail');
    const navbar = document.querySelector('.navbar');
    if (!links.length || !rail) return;

    const getOffset = () => (navbar?.offsetHeight || 56) + 8;
    let OFFSET = getOffset();
    window.addEventListener('resize', () => { OFFSET = getOffset(); });

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

      // center active chip
      const r = rail.getBoundingClientRect();
      const b = link.getBoundingClientRect();
      rail.scrollBy({ left: ((b.left + b.right) / 2 - (r.left + r.right) / 2), behavior: 'smooth' });
    };

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

    const io = new IntersectionObserver(entries => {
      const vis = entries.filter(e => e.isIntersecting)
                         .sort((a,b)=> b.intersectionRatio - a.intersectionRatio)[0];
      if (vis) setActive(map.get(vis.target));
    }, { rootMargin: `-${Math.max(OFFSET-10,0)}px 0px -50% 0px`, threshold: [0,.25,.5,.75,1] });

    map.forEach((_, section) => io.observe(section));

    const initId   = (location.hash || '').slice(1);
    const initLink = links.find(l => (l.dataset.anchor || l.getAttribute('href').slice(1)) === initId) || links[0];
    if (initLink) setActive(initLink);
  };

  return { init };
})();

/* -----------------------------------
   CART — live totals + soft AJAX sync
----------------------------------- */
const Cart = (() => {
  const { postForm, formatEuro, parseEuro } = Utils;

  // Compute one row and update line total + subtotal locally
  const computeRow = (tr) => {
    const qtyInput = tr.querySelector('.js-qty');
    const qty = Math.max(0, parseInt(qtyInput?.value || '0', 10));

    // Prefer data-unit; fallback to reading unit text
    const unit = (() => {
      if (tr.dataset.unit) return parseEuro(tr.dataset.unit);
      const unitEl = tr.querySelector('.js-unit');
      return unitEl ? parseEuro(unitEl.textContent) : 0;
    })();

    const total = qty * unit;

    const lineEl = tr.querySelector('.js-line-total');
    if (lineEl) {
      lineEl.textContent = formatEuro(total);
      lineEl.dataset.value = String(total.toFixed(2));
    }

    // recompute subtotal from all line totals
    let sum = 0;
    document.querySelectorAll('.js-line-total').forEach(el => {
      sum += parseEuro(el.dataset.value || el.textContent || 0);
    });
    const sub = document.getElementById('js-cart-subtotal');
    if (sub) sub.textContent = formatEuro(sum);
  };

  // Event delegation keeps listeners after partial DOM updates
  const onInput = (e) => {
    const qty = e.target.closest('.js-qty');
    if (!qty) return;
    const tr = e.target.closest('.cart-row') || e.target.closest('tr');
    if (tr) computeRow(tr);
  };

  const onChange = async (e) => {
    const input = e.target.closest('.js-qty');
    if (!input) return;

    const tr   = input.closest('.cart-row') || input.closest('tr');
    const form = input.closest('form');
    if (!tr || !form) return;

    // local calc now
    computeRow(tr);

    // server sync (keeps source of truth precise)
    try {
      const data = await postForm(form);
      if (data && data.ok) {
        if (data.line_total != null) {
          const v = parseEuro(String(data.line_total));
          const lineEl = tr.querySelector('.js-line-total');
          if (lineEl) {
            lineEl.textContent = data.line_total_display || formatEuro(v);
            lineEl.dataset.value = String(v.toFixed(2));
          }
        }
        if (data.subtotal != null) {
          const sub = document.getElementById('js-cart-subtotal');
          if (sub) sub.textContent = data.subtotal_display || formatEuro(parseEuro(String(data.subtotal)));
        }
      }
    } catch (_) {
      // ignore — UI already updated locally
    }
  };

  const onSubmit = async (e) => {
    const form = e.target.closest('.cart-remove-form, .cart-clear-form');
    if (!form) return;
    e.preventDefault();
    try {
      const data = await postForm(form);
      // If backend returns JSON with an HTML fragment, swap it in safely
      if (typeof data === 'object' && data && data.ok && data.html) {
        const root =
          document.querySelector('.container.py-10') ||
          document.querySelector('.container.py-5') ||
          document.querySelector('.cart-container') ||
          document.querySelector('.container');
        if (root) {
          root.outerHTML = data.html;
        } else {
          location.reload();
        }
      } else {
        location.reload();
      }
    } catch (_) {
      location.reload();
    }
  };

  const init = () => {
    // no cart on this page? bail early
    if (!document.querySelector('.cart-table')) return;

    document.addEventListener('input', onInput);
    document.addEventListener('change', onChange);
    document.addEventListener('submit', onSubmit);
  };

  return { init };
})();

/* -----------------------------------
   CHECKOUT — build order summary & send via WhatsApp or Email
   (i18n-safe: reads translated labels from .cart-summary data-* if present)
----------------------------------- */
const Checkout = (() => {
  const { parseEuro } = Utils;

  // Read optional translated labels from the cart-summary element
  const readI18n = (container, shopName) => {
    const d = (container && container.dataset) || {};
    const repl = (s) => String(s || '').replace('{shop}', shopName);
    return {
      orderTitle: repl(d.i18nOrderTitle || `🛒 ${shopName} – Bestellanfrage`),
      emailSubject: repl(d.i18nEmailSubject || `${shopName} – Neue Bestellung`),
      date: d.i18nDate || 'Datum',
      qty: d.i18nQty || 'Menge',
      unit: d.i18nUnit || 'Einzelpreis',
      line: d.i18nLine || 'Gesamt',
      subtotal: d.i18nSubtotal || 'Zwischensumme',
      customerData: d.i18nCustomerData || 'Kundendaten',
      name: d.i18nName || 'Name',
      phone: d.i18nPhone || 'Telefon',
      address: d.i18nAddress || 'Adresse',
      notes: d.i18nNotes || 'Anmerkungen',
      enterWa: d.i18nEnterWa || 'WhatsApp Nummer eingeben (z. B. 436601234567):',
      enterEmail: d.i18nEnterEmail || 'Bestell-E-Mail eingeben (z. B. bestellungen@example.com):'
    };
  };

  // Derive a locale only when needed (so we don’t affect homepage load)
  const getLocale = () => {
    const lang = (document.documentElement.getAttribute('lang') || 'de').toLowerCase();
    if (lang.startsWith('ar')) return 'ar-EG';
    if (lang.startsWith('de')) return 'de-AT';
    return lang;
  };

  const buildSummary = (shopName = 'Earth Store') => {
    const container = document.querySelector('.cart-summary');
    const i18n = readI18n(container, shopName);

    const rows = [...document.querySelectorAll('.cart-row')];
    const lines = [];
    rows.forEach((tr, i) => {
      const title = tr.querySelector('.cart-title-link')?.textContent?.trim() || 'Produkt';
      const qty   = tr.querySelector('.js-qty')?.value || '1';
      const line  = tr.querySelector('.js-line-total')?.textContent?.trim() || '';
      const unit  = tr.querySelector('.js-unit')?.textContent?.trim() || '';
      lines.push(`${i+1}) ${title}\n   ${i18n.qty}: ${qty}  ·  ${i18n.unit}: ${unit}  ·  ${i18n.line}: ${line}`);
    });

    const subtotalText = document.getElementById('js-cart-subtotal')?.textContent?.trim() || '';
    const subtotalNum  = parseEuro(subtotalText);
    const d = new Date().toLocaleDateString(getLocale());

    return [
      i18n.orderTitle,
      `${i18n.date}: ${d}`,
      '',
      ...lines,
      '',
      `${i18n.subtotal}: ${subtotalText || new Intl.NumberFormat(getLocale(), {style:'currency', currency:'EUR'}).format(subtotalNum)}`,
      '',
      `${i18n.customerData}:`,
      `${i18n.name}: `,
      `${i18n.phone}: `,
      `${i18n.address}: `,
      `${i18n.notes}: `,
    ].join('\n');
  };

  const openWhatsApp = (waNumber, text, promptText) => {
    const num = (waNumber || '').replace(/[^\d]/g, '');
    if (!num) {
      const manual = prompt(promptText || 'WhatsApp Nummer eingeben (z. B. 436601234567):');
      if (!manual) return;
      return openWhatsApp(manual, text, promptText);
    }
    const url = `https://wa.me/${num}?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank', 'noopener');
  };

  const openEmail = (email, subject, body, promptText) => {
    let to = (email || '').trim();
    if (!to) {
      const manual = prompt(promptText || 'Bestell-E-Mail eingeben (z. B. bestellungen@example.com):');
      if (!manual) return;
      to = manual.trim();
    }
    const mailto = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailto;
  };

  const onClick = (e) => {
    const btn = e.target.closest('[data-channel]');
    if (!btn) return;

    const shopName = btn.dataset.shopname || 'Earth Store';
    const summary  = buildSummary(shopName);

    if (btn.dataset.channel === 'whatsapp') {
      const container = document.querySelector('.cart-summary');
      const i18n = readI18n(container, shopName);
      openWhatsApp(btn.dataset.wa || '', summary, i18n.enterWa);
    } else if (btn.dataset.channel === 'email') {
      const container = document.querySelector('.cart-summary');
      const i18n = readI18n(container, shopName);
      openEmail(btn.dataset.email || '', i18n.emailSubject, summary, i18n.enterEmail);
    }
  };

  const init = () => {
    // only on cart page
    const container = document.querySelector('.cart-summary');
    if (!container) return;
    container.addEventListener('click', onClick);
  };

  return { init };
})();

/* -----------------------------------
   BACK TO TOP — show/hide button + global scrollToTop()
----------------------------------- */
const BackToTop = (() => {
  const SELECTOR = '.back-to-top';
  const THRESHOLD = 200; // px scrolled before showing

  const scrollToTop = () => {
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      window.scrollTo(0, 0);
    }
  };

  const setVisible = (btn, on) => {
    if (!btn) return;
    btn.classList.toggle('show', !!on);
    btn.setAttribute('aria-hidden', on ? 'false' : 'true');
    btn.tabIndex = on ? 0 : -1;
  };

  const init = () => {
    const btn = document.querySelector(SELECTOR);
    if (!btn) {
      // still expose global function so inline onclick works anywhere
      window.scrollToTop = scrollToTop;
      return;
    }

    // expose global for inline onclick="scrollToTop()"
    window.scrollToTop = scrollToTop;

    // also bind click (works even without inline)
    btn.addEventListener('click', (e) => {
      // if it's used inside <button onclick="...">, this is harmless
      e.preventDefault();
      scrollToTop();
    });

    // show/hide on scroll (throttled via rAF)
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        setVisible(btn, window.scrollY > THRESHOLD);
        ticking = false;
      });
    };

    // initial state + listeners
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
  };

  return { init };
})();
