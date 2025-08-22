document.addEventListener('DOMContentLoaded', function () {
  const navbar = document.querySelector('.navbar');
  const hasHero = document.querySelector('.hero-section');
  const isHome = document.querySelector(".homepage-hero");

  // Handle scroll background toggle
  function handleNavbarScroll() {
    if (window.scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }

  if (hasHero) {
    window.addEventListener('scroll', handleNavbarScroll);
    handleNavbarScroll(); // run on load
  } else {
    navbar.classList.add('scrolled'); // for non-hero pages
  }

  // Smooth scroll for in-page anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (!target) return;

      const yOffset = -60;
      const y = target.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    });
  });

  // Homepage entrance animation
  if (!isHome) return;

  document.body.classList.add("lock-scroll");

  const heroHeading = document.querySelector(".hero-heading");
  const heroContent = document.querySelector(".hero-content");
  const revealNext = document.querySelector(".reveal-next");

  // 1. Heading animates into position
  setTimeout(() => {
    heroHeading.classList.add("animate-to-position");
  }, 100);

  // 2. Navbar and hero content fade/slide in
  setTimeout(() => {
    navbar.classList.add("show-nav");
    heroContent.classList.add("show");
  }, 1300);

  // 3. White section slides up and scroll unlocks
  setTimeout(() => {
    revealNext?.classList.add("show");
    document.body.classList.remove("lock-scroll");
  }, 1800);
});

// 4. Scroll to top button
function scrollToTop() {
window.scrollTo({ top: 0, behavior: 'smooth' });
}
