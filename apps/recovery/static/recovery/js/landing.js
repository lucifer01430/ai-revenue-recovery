/**
 * AI Revenue Recovery — Landing Page Interactions
 * Premium B2B Fintech SaaS
 *
 * Features:
 * - Scroll-aware sticky header
 * - Mobile menu toggle
 * - Intersection Observer scroll reveal (with staggered grid support)
 * - Workflow interactive tabs with animated transitions
 * - 3D tilt effect on product cards
 * - SVG chart draw-on animation
 * - Smooth anchor scrolling (offset for sticky header)
 * - Respects prefers-reduced-motion
 */
(function () {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ============================================================
  // HEADER — scroll-aware
  // ============================================================
  const header = document.querySelector('[data-header]');
  let lastScrollY = 0;
  let ticking = false;

  const updateHeader = () => {
    if (!header) return;
    const scrolled = window.scrollY > 12;
    header.classList.toggle('scrolled', scrolled);
    ticking = false;
  };

  const onScroll = () => {
    lastScrollY = window.scrollY;
    if (!ticking) {
      requestAnimationFrame(updateHeader);
      ticking = true;
    }
  };

  updateHeader();
  window.addEventListener('scroll', onScroll, { passive: true });


  // ============================================================
  // MOBILE MENU
  // ============================================================
  const menuToggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');

  if (menuToggle && menu) {
    menuToggle.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', String(open));
    });

    // Close menu on link click
    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        menu.classList.remove('open');
        menuToggle.setAttribute('aria-expanded', 'false');
      });
    });

    // Close menu on outside click
    document.addEventListener('click', (e) => {
      if (!menu.contains(e.target) && !menuToggle.contains(e.target)) {
        menu.classList.remove('open');
        menuToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }


  // ============================================================
  // SMOOTH ANCHOR SCROLLING (with header offset)
  // ============================================================
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const targetId = anchor.getAttribute('href');
      if (targetId === '#') return;

      const target = document.querySelector(targetId);
      if (!target) return;

      e.preventDefault();

      const headerHeight = header ? header.offsetHeight : 0;
      const elementTop = target.getBoundingClientRect().top + window.scrollY;
      const offset = elementTop - headerHeight - 20;

      window.scrollTo({
        top: offset,
        behavior: reducedMotion ? 'auto' : 'smooth'
      });
    });
  });


  // ============================================================
  // SCROLL REVEAL — IntersectionObserver
  // ============================================================
  const reveals = document.querySelectorAll('.reveal');

  if (reducedMotion || !('IntersectionObserver' in window)) {
    // Immediately show everything if reduced motion or no IO support
    reveals.forEach((el) => el.classList.add('visible'));
  } else {
    const revealObserver = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          obs.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -40px 0px'
    });

    reveals.forEach((el) => revealObserver.observe(el));
  }


  // ============================================================
  // CHART DRAW ANIMATION
  // ============================================================
  const chartElements = document.querySelectorAll('.chart-animate');

  if (!reducedMotion && 'IntersectionObserver' in window && chartElements.length) {
    const chartObserver = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    chartElements.forEach((el) => chartObserver.observe(el));
  }


  // ============================================================
  // WORKFLOW — Interactive tabs
  // ============================================================
  const detail = document.querySelector('[data-workflow-detail]');
  const workflowData = [
    {
      kicker: '01 / DETECT',
      icon: 'bi-radar',
      title: 'Payment failure detected.',
      body: 'A Razorpay payment event enters the recovery workflow and becomes a case that can be reasoned about, acted on and audited.',
      next: 'Next: Diagnose',
      tag: 'INGRESS',
      tagClass: 'tag-blue'
    },
    {
      kicker: '02 / DIAGNOSE',
      icon: 'bi-search',
      title: 'The likely cause becomes visible.',
      body: 'AI analyzes the failure reason, payment amount, customer history and recovery history as structured context.',
      next: 'Next: Decide',
      tag: 'CONTEXT',
      tagClass: 'tag-blue'
    },
    {
      kicker: '03 / DECIDE',
      icon: 'bi-lightbulb',
      title: 'A bounded recommendation is formed.',
      body: 'The AI suggests one of the documented recovery actions and a timing signal. It has no execution authority.',
      next: 'Next: Guard',
      tag: 'ADVISORY',
      tagClass: 'tag-blue'
    },
    {
      kicker: '04 / GUARD',
      icon: 'bi-shield-check',
      title: 'Policy checks the recommendation.',
      body: 'Deterministic rules apply retry limits, recovery windows, duplicate prevention, escalation and stopping conditions.',
      next: 'Next: Act',
      tag: 'CONTROLLED',
      tagClass: 'tag-teal'
    },
    {
      kicker: '05 / ACT',
      icon: 'bi-lightning-charge',
      title: 'Only an approved action executes.',
      body: 'The recovery boundary translates the approved action into a bounded Test Mode or simulated operation.',
      next: 'Next: Recover',
      tag: 'APPROVED ONLY',
      tagClass: 'tag-teal'
    },
    {
      kicker: '06 / RECOVER',
      icon: 'bi-check2-circle',
      title: 'The outcome is confirmed.',
      body: 'A recovery result is recorded separately from the action. Execution alone never means recovery.',
      next: 'Next: Measure',
      tag: 'OUTCOME',
      tagClass: 'tag-teal'
    },
    {
      kicker: '07 / MEASURE',
      icon: 'bi-bar-chart',
      title: 'Actual recovery is calculated.',
      body: 'Revenue recovered and recovery performance come from persisted payment and result records.',
      next: 'Next: Audit',
      tag: 'PERSISTED DATA',
      tagClass: 'tag-blue'
    },
    {
      kicker: '08 / AUDIT',
      icon: 'bi-journal-check',
      title: 'The full trail stays reviewable.',
      body: 'Diagnosis, recommendation, guardrail decision, action, outcome and important transitions remain connected to the case.',
      next: 'Workflow complete',
      tag: 'AUDIT TRAIL',
      tagClass: 'tag-blue'
    }
  ];

  const workflowItems = document.querySelectorAll('[data-workflow]');

  const setWorkflow = (index) => {
    if (!detail) return;

    const item = workflowData[index];
    if (!item) return;

    // Add fade-out / fade-in transition
    if (!reducedMotion) {
      detail.style.opacity = '0';
      detail.style.transform = 'translateY(8px)';

      setTimeout(() => {
        renderWorkflowContent(item);
        detail.style.opacity = '1';
        detail.style.transform = 'translateY(0)';
      }, 150);
    } else {
      renderWorkflowContent(item);
    }

    workflowItems.forEach((btn, btnIndex) => {
      btn.classList.toggle('active', btnIndex === index);
    });
  };

  const renderWorkflowContent = (item) => {
    detail.innerHTML =
      '<div class="detail-kicker">STAGE ' + item.kicker + '</div>' +
      '<div class="detail-icon"><i class="bi ' + item.icon + '"></i></div>' +
      '<h3>' + item.title + '</h3>' +
      '<p>' + item.body + '</p>' +
      '<div class="detail-foot">' +
        '<span><i class="bi bi-arrow-right"></i> ' + item.next + '</span>' +
        '<span class="tag ' + item.tagClass + '">' + item.tag + '</span>' +
      '</div>';
  };

  // Apply transition styles to detail panel
  if (detail && !reducedMotion) {
    detail.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
  }

  workflowItems.forEach((btn) => {
    btn.addEventListener('click', () => {
      setWorkflow(Number(btn.dataset.workflow));
    });
  });


  // ============================================================
  // 3D TILT EFFECT
  // ============================================================
  if (!reducedMotion) {
    document.querySelectorAll('[data-tilt]').forEach((card) => {
      card.addEventListener('pointermove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        const tiltX = y * -3;
        const tiltY = x * 3;

        card.style.transform =
          'perspective(1200px) rotateX(' + tiltX + 'deg) rotateY(' + tiltY + 'deg)';
      });

      card.addEventListener('pointerleave', () => {
        card.style.transform = '';
      });
    });
  }


  // ============================================================
  // ACTIVE NAV HIGHLIGHTING (based on scroll position)
  // ============================================================
  const navLinks = document.querySelectorAll('.site-menu a[href^="#"]');
  const sections = [];

  navLinks.forEach((link) => {
    const targetId = link.getAttribute('href');
    const section = document.querySelector(targetId);
    if (section) {
      sections.push({ link, section });
    }
  });

  if (sections.length > 0) {
    const highlightNav = () => {
      const scrollPos = window.scrollY + (header ? header.offsetHeight : 0) + 60;

      let currentSection = null;
      sections.forEach(({ link, section }) => {
        if (section.offsetTop <= scrollPos) {
          currentSection = link;
        }
      });

      navLinks.forEach((link) => {
        link.style.color = '';
      });

      if (currentSection) {
        currentSection.style.color = 'var(--blue)';
      }
    };

    window.addEventListener('scroll', highlightNav, { passive: true });
    highlightNav();
  }

})();
