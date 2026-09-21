(function () {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const header = document.querySelector('[data-header]');
  const menuToggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');

  const updateHeader = () => {
    if (header) header.classList.toggle('scrolled', window.scrollY > 12);
  };
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  if (menuToggle && menu) {
    menuToggle.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      menuToggle.setAttribute('aria-expanded', String(open));
    });
    menu.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      menu.classList.remove('open');
      menuToggle.setAttribute('aria-expanded', 'false');
    }));
  }

  const reveals = document.querySelectorAll('.reveal');
  if (reducedMotion || !('IntersectionObserver' in window)) {
    reveals.forEach((item) => item.classList.add('visible'));
  } else {
    const observer = new IntersectionObserver((entries, currentObserver) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          currentObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    reveals.forEach((item) => observer.observe(item));
  }

  const detail = document.querySelector('[data-workflow-detail]');
  const workflow = [
    ['01 / DETECT', 'bi-radar', 'Payment failure detected.', 'A Razorpay payment event enters the recovery workflow and becomes a case that can be reasoned about, acted on and audited.', 'Next: Diagnose', 'INGRESS', 'tag-blue'],
    ['02 / DIAGNOSE', 'bi-search', 'The likely cause becomes visible.', 'AI analyzes the failure reason, payment amount, customer history and recovery history as structured context.', 'Next: Decide', 'CONTEXT', 'tag-blue'],
    ['03 / DECIDE', 'bi-lightbulb', 'A bounded recommendation is formed.', 'The AI suggests one of the documented recovery actions and a timing signal. It has no execution authority.', 'Next: Guard', 'ADVISORY', 'tag-blue'],
    ['04 / GUARD', 'bi-shield-check', 'Policy checks the recommendation.', 'Deterministic rules apply retry limits, recovery windows, duplicate prevention, escalation and stopping conditions.', 'Next: Act', 'CONTROLLED', 'tag-teal'],
    ['05 / ACT', 'bi-lightning-charge', 'Only an approved action executes.', 'The recovery boundary translates the approved action into a bounded Test Mode or simulated operation.', 'Next: Recover', 'APPROVED ONLY', 'tag-teal'],
    ['06 / RECOVER', 'bi-check2-circle', 'The outcome is confirmed.', 'A recovery result is recorded separately from the action. Execution alone never means recovery.', 'Next: Measure', 'OUTCOME', 'tag-teal'],
    ['07 / MEASURE', 'bi-bar-chart', 'Actual recovery is calculated.', 'Revenue recovered and recovery performance come from persisted payment and result records.', 'Next: Audit', 'PERSISTED DATA', 'tag-blue'],
    ['08 / AUDIT', 'bi-journal-check', 'The full trail stays reviewable.', 'Diagnosis, recommendation, guardrail decision, action, outcome and important transitions remain connected to the case.', 'Workflow complete', 'AUDIT TRAIL', 'tag-blue'],
  ];
  const items = document.querySelectorAll('[data-workflow]');
  const setWorkflow = (index) => {
    if (!detail) return;
    const item = workflow[index];
    detail.innerHTML = '<div class="detail-kicker">STAGE ' + item[0] + '</div>'
      + '<div class="detail-icon"><i class="bi ' + item[1] + '"></i></div>'
      + '<h3>' + item[2] + '</h3><p>' + item[3] + '</p>'
      + '<div class="detail-foot"><span><i class="bi bi-arrow-right"></i> ' + item[4] + '</span><span class="tag ' + item[6] + '">' + item[5] + '</span></div>';
    items.forEach((button, buttonIndex) => button.classList.toggle('active', buttonIndex === index));
  };
  items.forEach((item) => item.addEventListener('click', () => setWorkflow(Number(item.dataset.workflow))));

  if (!reducedMotion) {
    document.querySelectorAll('[data-tilt]').forEach((card) => {
      card.addEventListener('pointermove', (event) => {
        const rect = card.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = 'perspective(1100px) rotateX(' + (y * -2) + 'deg) rotateY(' + (x * 2) + 'deg)';
      });
      card.addEventListener('pointerleave', () => { card.style.transform = ''; });
    });
  }
})();
