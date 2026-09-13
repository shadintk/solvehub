(function () {
  'use strict';

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var qs = function (s, r) { return (r || document).querySelector(s); };
  var qsa = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function toast(message, type) {
    var wrap = qs('.toast-wrap');
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'toast-wrap'; document.body.appendChild(wrap); }
    var el = document.createElement('div');
    el.className = 'toast ' + (type || 'success');
    el.textContent = message;
    wrap.appendChild(el);
    requestAnimationFrame(function () { el.classList.add('show'); });
    setTimeout(function () { el.classList.remove('show'); setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 250); }, 3000);
  }
  window.showToast = toast;

  function setupPageEntrance() {
    var main = qs('#page-content');
    if (main && !reduceMotion) main.classList.add('page-ready');
    // Do not intercept navigation. Native browser navigation is instant and reliable;
    // the new document gets a lightweight entrance animation instead of a blocking curtain.
    qsa('a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (a.target === '_blank' || a.hasAttribute('download') || a.getAttribute('href') === '#') return;
        if (!reduceMotion) document.body.classList.add('leaving');
      }, { passive: true });
    });
    window.addEventListener('pageshow', function () {
      document.body.classList.remove('leaving');
    });
  }

  function setupProgress() {
    var bar = qs('.scroll-progress');
    if (!bar) return;
    var ticking = false;
    function update() {
      var max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      bar.style.transform = 'scaleX(' + Math.min(1, window.scrollY / max) + ')';
      ticking = false;
    }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    update();
  }

  function setupReveal() {
    var els = qsa('.reveal, .hero-reveal, .feature-detail, .org-cards article, .about-flow > div, .contact-item, .detail-card, .form-card, .list-card, .map-side, .side-card, .stat-card, .process-card, .coverage-card, .mode-card, .issue-card, .voice-card, .life-step, .intel-metric, .mini-panel, .dashboard-showcase, .ecosystem-orbit');
    if (!els.length) return;
    if (reduceMotion || !('IntersectionObserver' in window)) { els.forEach(function (e) { e.classList.add('is-visible'); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        io.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -7% 0px' });
    els.forEach(function (el, i) { el.style.setProperty('--reveal-delay', Math.min(i % 6, 5) * 55 + 'ms'); io.observe(el); });
  }

  function setupCounters() {
    var els = qsa('[data-count]');
    if (!els.length) return;
    els.forEach(function (el) {
      var target = Number(el.dataset.count || 0), done = false;
      function run() {
        if (done) return; done = true;
        if (reduceMotion) { el.textContent = target.toLocaleString(); return; }
        var start = performance.now(), duration = 900;
        function tick(now) {
          var p = Math.min(1, (now - start) / duration), eased = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(target * eased).toLocaleString();
          if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
      }
      if ('IntersectionObserver' in window && !reduceMotion) {
        var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { run(); io.disconnect(); } }, { threshold: .45 });
        io.observe(el);
      } else run();
    });
  }

  function setupMobileNav() {
    var nav = qs('.nav-links'), header = qs('.navbar');
    if (!nav || !header || qs('.mobile-nav-toggle')) return;
    var button = document.createElement('button');
    button.type = 'button'; button.className = 'mobile-nav-toggle'; button.setAttribute('aria-label', 'Open navigation'); button.setAttribute('aria-expanded', 'false');
    button.innerHTML = '<span></span><span></span><span></span>';
    header.appendChild(button);
    button.addEventListener('click', function () {
      var open = header.classList.toggle('mobile-open');
      button.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) header.classList.remove('mobile-open'); });
  }

  function setupActiveNav() {
    var path = window.location.pathname;
    qsa('.nav-links a').forEach(function (a) { try { if (new URL(a.href, location.href).pathname === path) a.classList.add('nav-current'); } catch (e) {} });
  }

  function setupCards() {
    if (reduceMotion || !window.matchMedia('(pointer:fine)').matches) return;
    qsa('.process-card,.coverage-card,.mode-card,.issue-card,.voice-card,.feature-detail,.org-cards article,.stat-card,.detail-card,.mini-panel,.life-step,.problem-card,.list-card').forEach(function (card) {
      card.addEventListener('pointermove', function (e) {
        var r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        card.style.transform = 'perspective(900px) rotateX(' + (-y * 2.5).toFixed(2) + 'deg) rotateY(' + (x * 3).toFixed(2) + 'deg) translateY(-3px)';
      });
      card.addEventListener('pointerleave', function () { card.style.transform = ''; });
    });
  }

  function setupFlash() {
    qsa('.flash').forEach(function (el, i) {
      if (!reduceMotion) el.style.animationDelay = (i * 70) + 'ms';
      setTimeout(function () { el.classList.add('flash-hide'); }, 3500 + i * 100);
    });
  }

  function setupForms() {
    qsa('input, textarea, select').forEach(function (field) {
      field.addEventListener('focus', function () { var l = field.closest('label'); if (l) l.classList.add('field-active'); });
      field.addEventListener('blur', function () { var l = field.closest('label'); if (l) l.classList.remove('field-active'); });
    });
  }

  function supportProblem(id) {
    var btn = document.querySelector('[data-support-id="' + id + '"]') || document.querySelector('button[onclick*="supportProblem(' + id + ')"]');
    if (btn) btn.disabled = true;
    fetch('/support/' + encodeURIComponent(id), { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin' })
      .then(function (r) { if (r.status === 401) throw new Error('login'); if (!r.ok) throw new Error('request'); return r.json(); })
      .then(function (data) { var count = qs('#supportCount'); if (count) count.textContent = data.count; if (btn) { btn.classList.add('supported'); btn.innerHTML = '♥ <span id="supportCount">' + data.count + '</span> Supported'; } toast('Thanks — your support was added.'); })
      .catch(function (e) { if (btn) btn.disabled = false; if (e.message === 'login') location.href = '/login?next=' + encodeURIComponent(location.pathname); else toast('Could not update support.', 'danger'); });
  }
  window.supportProblem = supportProblem;

  function setupPasswordToggles() {
    qsa('.password-toggle').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var wrap = btn.closest('.password-wrap');
        if (!wrap) return;
        var input = qs('input', wrap);
        if (!input) return;

        var showIcon = qs('.eye-show', btn);
        var hideIcon = qs('.eye-hide', btn);

        if (input.type === 'password') {
          input.type = 'text';
          if (showIcon) showIcon.style.display = 'none';
          if (hideIcon) hideIcon.style.display = 'inline-block';
          btn.setAttribute('aria-label', 'Hide password');
          btn.title = 'Hide password';
        } else {
          input.type = 'password';
          if (showIcon) showIcon.style.display = 'inline-block';
          if (hideIcon) hideIcon.style.display = 'none';
          btn.setAttribute('aria-label', 'Show password');
          btn.title = 'Show password';
        }
        input.focus();
      });
    });
  }

  function setupTriage() {
    var input = qs('#triageInput'), run = qs('#runTriage'), result = qs('#triageResult');
    if (!input || !run || !result) return;
    var placeholder = qs('.triage-placeholder', result), content = qs('.triage-result-content', result), busy = false;
    function render(data) {
      if (placeholder) placeholder.hidden = true; if (content) content.hidden = false;
      var map = { triageConfidence: data.confidence + '%', triageCategory: data.category, triageUrgency: data.urgency, triageDepartment: data.department, triageImpact: data.impact, triageAction: data.action, routeTeam: (data.department || '').replace(' Team','').replace(' Response','') };
      Object.keys(map).forEach(function (id) { var el = qs('#' + id); if (el) el.textContent = map[id]; });
      result.classList.remove('triage-pulse'); void result.offsetWidth; result.classList.add('triage-pulse');
    }
    function fallback(text) {
      var t = text.toLowerCase(), rules = [
        [['flood','drain','waterlog','rain','overflow'],['Water & Drainage','Water & Sanitation Team','High','Community-wide','Verify location and assign a field inspection',92]],
        [['road','pothole','footpath','bridge','traffic'],['Roads & Infrastructure','Infrastructure Response Team','High','Public','Create a geo-tagged field inspection task',91]],
        [['garbage','waste','trash','dump','litter'],['Waste Management','Waste Management Team','Medium','Community-wide','Cluster nearby reports and schedule collection',91]],
        [['light','lighting','lamp','dark','unsafe'],['Street Safety & Lighting','Public Safety & Electrical Team','High','Public','Verify the location and create a repair task',90]],
        [['power','electric','wire','transformer','outage'],['Electricity','Electrical Response Team','High','Public','Escalate for safety inspection',91]],
        [['campus','college','hostel','classroom','canteen','facility'],['Campus & Facilities','Institution Facilities Team','Medium','Institutional','Assign to the relevant campus facility owner',89]],
        [['wifi','internet','network','signal'],['Connectivity','IT / Connectivity Team','Medium','Users','Run a connectivity check and assign IT support',90]]
      ], best = ['Other Community Issue','Civic Coordination Team','Medium','To be assessed','Review the report and route it to the closest owner',72];
      rules.forEach(function (r) { if (r[0].some(function (k) { return t.indexOf(k) >= 0; })) best = r[1]; });
      render({ category:best[0], department:best[1], urgency:best[2], impact:best[3], action:best[4], confidence:best[5] });
    }
    function analyze() {
      var text = input.value.trim(); if (!text || busy) { if (!text) { input.focus(); input.classList.add('shake-field'); setTimeout(function(){ input.classList.remove('shake-field'); }, 450); } return; }
      busy = true; run.disabled = true; run.classList.add('is-busy'); var label = qs('span', run); if (label) label.textContent = 'Analyzing…';
      fetch('/api/triage', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text:text}) })
        .then(function(r){ if(!r.ok) throw new Error('triage'); return r.json(); }).then(render).catch(function(){ fallback(text); })
        .finally(function(){ busy=false; run.disabled=false; run.classList.remove('is-busy'); if(label) label.textContent='Analyze problem'; });
    }
    run.addEventListener('click', analyze); input.addEventListener('keydown', function(e){ if((e.ctrlKey||e.metaKey)&&e.key==='Enter') analyze(); });
    qsa('.prompt-chip').forEach(function(chip){ chip.addEventListener('click',function(){ input.value=chip.dataset.prompt||''; input.focus(); }); });
  }

  function setupHomeInteractions() {
    var toastEl = qs('#constellationToast');
    qsa('.constellation-node').forEach(function(node){ node.addEventListener('click',function(){
      qsa('.constellation-node').forEach(function(n){n.classList.remove('selected');}); node.classList.add('selected');
      if(toastEl){ var role=node.dataset.node||'Node'; var text={Citizen:'brings the real-world need and evidence.', 'AI Engine':'turns the report into a structured signal.', University:'adds research, students and domain expertise.', Industry:'helps prototype, fund or scale the response.', Community:'validates the outcome and creates shared impact.'}; toastEl.innerHTML='<b>'+role+'</b> — '+(text[role]||'connects to the solution flow.'); }
    }); });
    var selected = qs('#matchSelected');
    qsa('.match-person').forEach(function(card){ card.addEventListener('click',function(){ qsa('.match-person').forEach(function(c){c.classList.remove('active');}); card.classList.add('active'); if(selected) selected.innerHTML='AI match selected: <b>'+card.dataset.match+'</b>'; }); });
    var dashNew = qs('[data-dashboard-new-report]'); if (dashNew) dashNew.addEventListener('click', function(){ location.href='/report'; });
  }

  document.addEventListener('DOMContentLoaded', function () {
    setupPageEntrance(); setupProgress(); setupReveal(); setupCounters(); setupMobileNav(); setupActiveNav(); setupCards(); setupFlash(); setupForms(); setupPasswordToggles(); setupTriage(); setupHomeInteractions();
  });
})();
