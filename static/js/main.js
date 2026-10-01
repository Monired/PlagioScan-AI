/**
 * PlagioScan AI — Main JavaScript
 * Dark/light mode, animated counters, score bars, charts, dropzone
 */

/* ═══════════════ Theme ══════════════════════════════════════════════ */
const THEME_KEY = 'plagioscan_theme';

function getTheme() {
  return localStorage.getItem(THEME_KEY) || 'dark';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  const icon = document.getElementById('themeIcon');
  if (icon) icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
}

function toggleTheme() {
  applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
}

/* Apply on load */
document.addEventListener('DOMContentLoaded', () => {
  applyTheme(getTheme());
  initAll();
});

function initAll() {
  initCounters();
  initScoreBars();
  initSimBars();
  initScoreCards();
  initDropzone();
  initAlerts();
  initPasswordToggle();
  initPasswordStrength();
  initUserSearch();
  initHighlightTooltips();
  initSyncScroll();
}


/* ═══════════════ Animated Counters ═══════════════════════════════════ */
function initCounters() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target  = parseFloat(el.dataset.count) || 0;
    const isFloat = el.dataset.float === 'true';
    const suffix  = el.dataset.suffix || '';
    const dur     = 900;
    const steps   = 45;
    const inc     = target / steps;
    let cur = 0;
    const t = setInterval(() => {
      cur = Math.min(cur + inc, target);
      el.textContent = (isFloat ? cur.toFixed(1) : Math.round(cur)) + suffix;
      if (cur >= target) clearInterval(t);
    }, dur / steps);
  });
}


/* ═══════════════ Score Progress Bars ════════════════════════════════ */
function initScoreBars() {
  setTimeout(() => {
    document.querySelectorAll('.score-fill[data-w]').forEach(el => {
      el.style.width = Math.min(parseFloat(el.dataset.w || 0), 100) + '%';
    });
    document.querySelectorAll('.progress-bar[data-w]').forEach(el => {
      el.style.width = Math.min(parseFloat(el.dataset.w || 0), 100) + '%';
    });
  }, 200);
}

function initSimBars() {
  setTimeout(() => {
    document.querySelectorAll('.sim-fill[data-sim]').forEach(el => {
      el.style.width = Math.min(parseFloat(el.dataset.sim || 0), 100) + '%';
    });
  }, 400);
}


/* ═══════════════ Score Card Animations ══════════════════════════════ */
function initScoreCards() {
  const cards = document.querySelectorAll('.score-card');
  cards.forEach((card, i) => {
    setTimeout(() => card.classList.add('shown'), i * 90);
  });
}


/* ═══════════════ Auto-dismiss Alerts ═══════════════════════════════ */
function initAlerts() {
  document.querySelectorAll('.flash-toast').forEach(el => {
    setTimeout(() => {
      try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch(e) {}
    }, 5500);
  });
}


/* ═══════════════ Dropzone ════════════════════════════════════════════ */
function initDropzone() {
  const zone  = document.getElementById('dropZone');
  const input = document.getElementById('fileInput');
  if (!zone || !input) return;

  const inner    = document.getElementById('dropInner');
  const selected = document.getElementById('fileSelected');
  const fname    = document.getElementById('selectedName');
  const fsize    = document.getElementById('selectedSize');
  const ftype    = document.getElementById('selectedTypeIcon');
  const submitBtn= document.getElementById('submitBtn');
  const clearBtn = document.getElementById('clearFile');

  const typeIcons = { pdf: '📄', docx: '📝', txt: '📃', rtf: '📋', odt: '📋',
                      png: '🖼️', jpg: '🖼️', jpeg: '🖼️', zip: '📦' };

  function showFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    inner.classList.add('d-none');
    selected.classList.remove('d-none');
    fname.textContent = file.name;
    fsize.textContent = formatSize(file.size);
    if (ftype) ftype.textContent = typeIcons[ext] || '📄';
    if (submitBtn) submitBtn.removeAttribute('disabled');
  }

  function clearFile() {
    input.value = '';
    inner.classList.remove('d-none');
    selected.classList.add('d-none');
    if (submitBtn) submitBtn.setAttribute('disabled', '');
  }

  input.addEventListener('change', () => {
    if (input.files[0]) showFile(input.files[0]);
  });

  zone.addEventListener('click', e => {
    if (!selected.classList.contains('d-none') && !e.target.closest('#dropInner')) return;
    input.click();
  });

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files;
      showFile(file);
    }
  });

  if (clearBtn) clearBtn.addEventListener('click', e => { e.stopPropagation(); clearFile(); });

  // Submit animation
  const uploadForm = document.getElementById('uploadForm');
  if (uploadForm && submitBtn) {
    uploadForm.addEventListener('submit', () => {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading & Analyzing…';
    });
  }
}

function formatSize(bytes) {
  if (bytes < 1024)       return bytes + ' B';
  if (bytes < 1048576)    return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}


/* ═══════════════ Password Show/Hide ════════════════════════════════ */
function initPasswordToggle() {
  document.querySelectorAll('[data-pw-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.pwToggle);
      const icon   = btn.querySelector('i');
      if (!target) return;
      target.type = target.type === 'password' ? 'text' : 'password';
      if (icon) icon.className = target.type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
  });
}


/* ═══════════════ Password Strength ════════════════════════════════ */
function initPasswordStrength() {
  const pwField = document.getElementById('reg-password');
  const bar     = document.getElementById('pwStrengthBar');
  const lbl     = document.getElementById('pwStrengthLbl');
  const regBtn  = document.getElementById('regBtn');
  const usernameField = document.getElementById('reg-username');
  const emailField    = document.getElementById('reg-email');
  const confirmField  = document.getElementById('reg-confirm');

  if (!pwField) return;

  function strength(pw) {
    let s = 0;
    if (pw.length >= 6)  s++;
    if (pw.length >= 10) s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return s;
  }

  function validate() {
    const u = usernameField ? usernameField.value.trim() : 'ok';
    const e = emailField    ? emailField.value.trim() : 'a@b.c';
    const p = pwField.value;
    const c = confirmField  ? confirmField.value : p;

    if (bar && lbl && p.length > 0) {
      const s = strength(p);
      const colors = ['#e84393','#e84393','#f9ca24','#f9ca24','#00c9a7'];
      const labels = ['','Weak','Fair','Good','Strong'];
      bar.style.width = (s * 20) + '%';
      bar.style.background = colors[s-1] || '#e84393';
      lbl.textContent = labels[s] || 'Weak';
      lbl.style.color = colors[s-1] || '#e84393';
    }

    if (regBtn) {
      const emailOk = e.includes('@') && e.includes('.');
      regBtn.disabled = !(u.length >= 3 && emailOk && p.length >= 6 && p === c);
    }
  }

  [pwField, usernameField, emailField, confirmField].forEach(f => {
    if (f) f.addEventListener('input', validate);
  });
}


/* ═══════════════ Admin User Search ═════════════════════════════════ */
function initUserSearch() {
  const input = document.getElementById('userSearch');
  if (!input) return;
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase();
    document.querySelectorAll('.user-row').forEach(row => {
      const name = row.querySelector('.user-name')?.textContent.toLowerCase() || '';
      const email = row.querySelector('.user-email')?.textContent.toLowerCase() || '';
      row.style.display = (name.includes(q) || email.includes(q)) ? '' : 'none';
    });
  });
}


/* ═══════════════ Highlight Tooltips ════════════════════════════════ */
function initHighlightTooltips() {
  document.querySelectorAll('mark[data-score]').forEach(el => {
    el.style.cursor = 'help';
    el.addEventListener('click', () => {
      const score = el.dataset.score;
      const tip   = el.title || `Similarity: ${score}%`;
      showToast(tip, score > 60 ? 'danger' : score > 30 ? 'warning' : 'info');
    });
  });
}

function showToast(msg, type = 'info') {
  const d = document.createElement('div');
  d.className = `alert alert-${type} alert-dismissible fade show flash-toast position-fixed`
              + ` bottom-0 end-0 m-3`;
  d.style.zIndex = 9999;
  d.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3000);
}


/* ═══════════════ Synchronized Scroll (Compare) ═════════════════════ */
function initSyncScroll() {
  const left  = document.getElementById('leftPane');
  const right = document.getElementById('rightPane');
  if (!left || !right) return;
  let syncing = false;
  left.addEventListener('scroll', () => {
    if (syncing) return; syncing = true;
    right.scrollTop = left.scrollTop * (right.scrollHeight / left.scrollHeight);
    setTimeout(() => syncing = false, 50);
  });
  right.addEventListener('scroll', () => {
    if (syncing) return; syncing = true;
    left.scrollTop = right.scrollTop * (left.scrollHeight / right.scrollHeight);
    setTimeout(() => syncing = false, 50);
  });
}


/* ═══════════════ Chart.js Defaults (dark) ══════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  if (typeof Chart !== 'undefined') {
    Chart.defaults.color          = '#7986cb';
    Chart.defaults.borderColor    = 'rgba(255,255,255,0.07)';
    Chart.defaults.font.family    = "'Inter', sans-serif";
    Chart.defaults.font.size      = 11;
    Chart.defaults.animation      = { duration: 900 };
  }
});


/* ═══════════════ Copy to Clipboard ════════════════════════════════ */
function copyText(elementId, btnId) {
  const el = document.getElementById(elementId);
  const btn = document.getElementById(btnId);
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-check me-1"></i>Copied!';
      btn.classList.add('btn-accent');
      btn.classList.remove('btn-outline-accent');
      setTimeout(() => { btn.innerHTML = orig; btn.classList.remove('btn-accent'); btn.classList.add('btn-outline-accent'); }, 2000);
    }
  });
}
