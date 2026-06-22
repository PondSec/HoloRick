const $ = s => document.querySelector(s);
const chatList = $('#chatList');
const messagesEl = $('#messages');
const input = $('#messageInput');
const form = $('#composerForm');
const sidebar = $('#sidebar');
const backdrop = $('#backdrop');
const toastEl = $('#toast');
const limitBanner = $('#limitBanner');
const rateBanner = $('#rateBanner');
const fileInput = $('#fileInput');
const attachmentsEl = $('#attachments');
const modePopover = $('#modePopover');
const contextDrawer = $('#contextDrawer');

let chats = [];
let currentChatId = 0;
let currentProjectId = 0;
let projects = [];
let currentProject = null;
let archivedView = false;
let me = { authenticated: false };
let selectedFiles = [];
let settings = {};
let loading = false;
let csrfToken = '';
let aiMode = 'holo';
let responseFormat = 'auto';
let currentChatHasContext = false;
const guestTokenKey = 'holo_rick_guest_token';

const modeLabels = {
  holo: 'Holo Rick',
  precise: 'Präzise',
  deep: 'Deep Work',
  code: 'Code'
};

const formatLabels = {
  auto: 'Auto',
  steps: 'Schritte',
  table: 'Tabelle'
};

const quickPrompts = [
  { label: 'Plan machen', prompt: 'Mach mir einen klaren, priorisierten Plan für: ' },
  { label: 'Fehler finden', prompt: 'Analysiere das Problem systematisch, finde die wahrscheinlichste Ursache und gib mir konkrete nächste Schritte: ' },
  { label: 'Vergleichen', prompt: 'Vergleiche die Optionen in einer Tabelle mit Vor- und Nachteilen: ' },
  { label: 'Text verbessern', prompt: 'Verbessere diesen Text hochwertig, klar und natürlich: ' }
];

const actionLabels = {
  summary: 'Kurz',
  tasks: 'To-dos',
  risks: 'Risiken'
};

const guestActionPrompts = {
  summary: 'Fasse diesen Text extrem klar und kurz zusammen:\\n\\n',
  tasks: 'Mache aus diesem Text eine priorisierte, ausführbare To-do-Liste:\\n\\n',
  risks: 'Prüfe diesen Text kritisch auf Risiken, Lücken und bessere Alternativen:\\n\\n'
};

const icons = {
  'x': '<svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  'edit-3': '<svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>',
  'search': '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
  'message-circle': '<svg viewBox="0 0 24 24"><path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 17 0Z"/></svg>',
  'circle': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg>',
  'book': '<svg viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5Z"/></svg>',
  'briefcase': '<svg viewBox="0 0 24 24"><path d="M10 6V5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2v1"/><rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 12h18"/></svg>',
  'layout-grid': '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>',
  'wand': '<svg viewBox="0 0 24 24"><path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9H6"/><path d="M20 9h-2"/><path d="m17.8 6.2 1.4-1.4"/><path d="m10.8 13.2-1.4 1.4"/><path d="m9.4 3.8 1.4 1.4"/><path d="m14 10 7 7-4 4-7-7Z"/></svg>',
  'chevron-down': '<svg viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>',
  'archive': '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/></svg>',
  'settings': '<svg viewBox="0 0 24 24"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1A2 2 0 1 1 4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1A2 2 0 1 1 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.6V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.6h.1a1.7 1.7 0 0 0 1.9-.3l.1-.1A2 2 0 1 1 19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.6 1h.1a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.6 1Z"/></svg>',
  'sparkles': '<svg viewBox="0 0 24 24"><path d="m12 3 1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8Z"/><path d="m19 14 .9 2.1L22 17l-2.1.9L19 20l-.9-2.1L16 17l2.1-.9Z"/><path d="m5 14 .9 2.1L8 17l-2.1.9L5 20l-.9-2.1L2 17l2.1-.9Z"/></svg>',
  'sidebar': '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>',
  'plus': '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  'arrow-up': '<svg viewBox="0 0 24 24"><path d="m12 19V5"/><path d="m5 12 7-7 7 7"/></svg>',
  'file': '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/></svg>',
  'trash-2': '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>',
  'user': '<svg viewBox="0 0 24 24"><path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="7" r="4"/></svg>',
  'shield': '<svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/></svg>',
  'shield-check': '<svg viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-5"/></svg>',
  'sliders': '<svg viewBox="0 0 24 24"><path d="M4 21v-7"/><path d="M4 10V3"/><path d="M12 21v-9"/><path d="M12 8V3"/><path d="M20 21v-5"/><path d="M20 12V3"/><path d="M2 14h4"/><path d="M10 8h4"/><path d="M18 16h4"/></svg>',
  'file-text': '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>',
  'key-round': '<svg viewBox="0 0 24 24"><path d="M2 18v3h3l9.2-9.2"/><circle cx="16.5" cy="7.5" r="5.5"/></svg>',
  'smartphone': '<svg viewBox="0 0 24 24"><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/></svg>',
  'copy': '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><rect x="2" y="2" width="13" height="13" rx="2"/></svg>',
  'download': '<svg viewBox="0 0 24 24"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>',
  'folder': '<svg viewBox="0 0 24 24"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.5L10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2Z"/></svg>',
  'more-horizontal': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>'
};

function injectIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => {
    el.innerHTML = icons[el.dataset.icon] || '';
  });
}

async function refreshCsrfToken() {
  const token = localStorage.getItem(guestTokenKey);
  const headers = { 'Accept': 'application/json' };
  if (token) headers['X-Guest-Token'] = token;
  const r = await fetch('/api/me', {
    credentials: 'same-origin',
    cache: 'no-store',
    headers
  });
  const d = await r.json().catch(() => ({}));
  if (d.csrf_token) csrfToken = d.csrf_token;
  if (d.guest_token) localStorage.setItem(guestTokenKey, d.guest_token);
  return d;
}

function isCsrfError(status, data) {
  return status === 400 && String(data?.error || '').includes('Sicherheits-Token');
}

async function api(path, opt = {}, retry = true) {
  const method = (opt.method || 'GET').toUpperCase();
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && !csrfToken) {
    await refreshCsrfToken();
  }
  const headers = new Headers(opt.headers || {});
  const guestToken = localStorage.getItem(guestTokenKey);
  if (guestToken) headers.set('X-Guest-Token', guestToken);
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken);
  }
  const r = await fetch(path, { credentials: 'same-origin', cache: method === 'GET' ? 'no-store' : 'default', ...opt, headers });
  const raw = await r.text();
  let d = {};
  if (raw) {
    try {
      d = JSON.parse(raw);
    } catch {
      d = { error: httpErrorMessage(r.status) };
    }
  }
  if (d.csrf_token) csrfToken = d.csrf_token;
  if (d.guest_token) localStorage.setItem(guestTokenKey, d.guest_token);
  if (!r.ok && retry && isCsrfError(r.status, d)) {
    await refreshCsrfToken();
    return api(path, opt, false);
  }
  if (!r.ok) throw { ...d, error: d.error || httpErrorMessage(r.status), status: r.status };
  return d;
}

function httpErrorMessage(status) {
  if (status === 413) return `Datei ist zu groß. Maximal ${uploadLimitMb()} MB pro Datei.`;
  if (status === 429) return 'Nutzungslimit erreicht';
  if (status === 401) return 'Bitte anmelden';
  if (status >= 500) return 'Serverfehler. Bitte erneut versuchen.';
  return status ? `Anfrage fehlgeschlagen (${status})` : 'Verbindung fehlgeschlagen';
}

function toast(t) {
  toastEl.textContent = t;
  toastEl.classList.remove('hidden');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => toastEl.classList.add('hidden'), 3200);
}

function formatRetryAfter(seconds) {
  const value = Math.max(1, Number(seconds || 60));
  if (value >= 3600) return `${Math.ceil(value / 3600)} Std.`;
  if (value >= 60) return `${Math.ceil(value / 60)} Min.`;
  return `${Math.ceil(value)} Sek.`;
}

function showRateLimitBanner(error = {}) {
  rateBanner.textContent = `Holo Rick braucht eine Pause. Schau in ${formatRetryAfter(error.retry_after_seconds)} wieder vorbei.`;
  rateBanner.classList.remove('hidden');
  clearTimeout(showRateLimitBanner.t);
  showRateLimitBanner.t = setTimeout(() => rateBanner.classList.add('hidden'), 12000);
}

function showError(e, fallback = 'Fehler') {
  if (e?.error === 'RATE_LIMIT') {
    showRateLimitBanner(e);
    return;
  }
  toast(e?.message && e.error !== e.message ? e.message : (e?.error || fallback));
}

function esc(s) {
  return String(s ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function plainTextToHtml(text) {
  return `<p>${esc(text).replace(/\n{2,}/g, '</p><p>').replace(/\n/g, '<br>')}</p>`;
}

function uploadLimitMb() {
  return Number(me.max_upload_mb || 25);
}

function uploadLimitBytes() {
  return uploadLimitMb() * 1024 * 1024;
}

function maxFilesPerMessage() {
  return Number(me.max_files_per_message || 5);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '';
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(bytes >= 10 * 1024 * 1024 ? 0 : 1)} MB`;
  if (bytes >= 1024) return `${Math.ceil(bytes / 1024)} KB`;
  return `${bytes} B`;
}

function fileExt(name) {
  const parts = String(name || '').toLowerCase().split('.');
  return parts.length > 1 ? parts.pop() : '';
}

function validateFile(file) {
  const ext = fileExt(file.name);
  const allowed = Array.isArray(me.allowed_upload_extensions) ? me.allowed_upload_extensions : [];
  if (allowed.length && !allowed.includes(ext)) {
    return `${file.name}: Dateityp nicht erlaubt.`;
  }
  if (!file.size) {
    return `${file.name}: Datei ist leer.`;
  }
  if (file.size > uploadLimitBytes()) {
    return `${file.name} ist zu groß (${formatBytes(file.size)}). Limit: ${uploadLimitMb()} MB.`;
  }
  return '';
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function openSidebar() {
  sidebar.classList.add('open');
  backdrop.classList.add('show');
}

function closeSidebar() {
  sidebar.classList.remove('open');
  backdrop.classList.remove('show');
}

function bindDismissibleModals() {
  document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('pointerdown', e => {
      if (!e.target.closest('.modal-card')) modal.classList.add('hidden');
    });
  });
}

function showChatSurface() {
  $('#projectsView')?.classList.add('hidden');
  messagesEl.classList.remove('hidden');
  form.classList.remove('hidden');
}

function showProjectsSurface() {
  messagesEl.classList.add('hidden');
  form.classList.add('hidden');
  $('#projectsView')?.classList.remove('hidden');
}

function renderEmpty() {
  showChatSurface();
  const chips = quickPrompts.map(item => `<button type="button" class="prompt-chip" data-prompt="${esc(item.prompt)}">${esc(item.label)}</button>`).join('');
  messagesEl.innerHTML = `
    <div class="empty">
      <div class="orb">H</div>
      <h1>Wobei kann ich helfen?</h1>
      <p>Ein ruhiger Workspace für präzise Antworten, Projektkontext und Dateien.</p>
      <div class="prompt-grid">${chips}</div>
    </div>`;
  messagesEl.querySelectorAll('.prompt-chip').forEach(btn => {
    btn.onclick = () => {
      input.value = btn.dataset.prompt || '';
      resize();
      input.focus();
    };
  });
}

function uploadMarkup(meta = {}) {
  const parsed = parseMeta(meta);
  return (parsed.uploads || []).map(u => {
    const label = esc(u.name || 'Anhang');
    const href = u.url && String(u.url).startsWith('/uploads/') ? esc(u.url) : '';
    const mime = String(u.mime || '');
    const img = href && mime.startsWith('image/') ? `<img src="${href}" alt="">` : icons.file;
    const inner = `${img}<span>${label}</span>`;
    if (href) {
      return `<a class="upload-chip ${mime.startsWith('image/') ? 'image' : ''}" href="${href}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
    }
    return `<span class="upload-chip">${icons.file}<span>${label}</span></span>`;
  }).join('');
}

function parseMeta(meta = {}) {
  if (typeof meta === 'string') {
    try { return JSON.parse(meta || '{}'); } catch { return {}; }
  }
  return meta || {};
}

function generatedImageMarkup(meta = {}) {
  const parsed = parseMeta(meta);
  const generation = parsed.image_generation || {};
  const image = generation.image || {};
  const src = image.url || image.data_url || '';
  if (!src) return '';
  const safeSrc = esc(src);
  const name = esc(image.name || 'holo-rick-bild.png');
  const prompt = esc(generation.prompt || 'Generiertes Bild');
  return `
    <figure class="generated-image">
      <img src="${safeSrc}" alt="${prompt}">
      <a class="image-download" href="${safeSrc}" download="${name}" title="Bild herunterladen">${icons.download}</a>
      <figcaption>Generiertes Bild</figcaption>
    </figure>`;
}

function enhanceContent(root) {
  root.querySelectorAll('pre').forEach(pre => {
    if (pre.parentElement?.classList.contains('code-wrap')) return;
    const wrap = document.createElement('div');
    wrap.className = 'code-wrap';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'copy-code icon-text';
    btn.innerHTML = `${icons.copy}<span>Kopieren</span>`;
    btn.onclick = () => navigator.clipboard.writeText(pre.innerText).then(() => toast('Code kopiert'));
    pre.replaceWith(wrap);
    wrap.appendChild(btn);
    wrap.appendChild(pre);
  });
  root.querySelectorAll('table').forEach(table => {
    if (table.parentElement?.classList.contains('table-scroll')) return;
    const wrap = document.createElement('div');
    wrap.className = 'table-scroll';
    table.replaceWith(wrap);
    wrap.appendChild(table);
  });
}

function addMsg(role, content, meta = {}, contentHtml = '', messageId = null) {
  const row = document.createElement('div');
  row.className = `msg ${role}`;
  const avatar = role === 'assistant' ? '<div class="avatar h">H</div>' : '<div class="avatar u">Du</div>';
  const html = role === 'assistant' ? (contentHtml || plainTextToHtml(content)) : plainTextToHtml(content);
  const parsedMeta = parseMeta(meta);
  const generatedImage = role === 'assistant' ? generatedImageMarkup(parsedMeta) : '';
  const smartActions = role === 'assistant' && !generatedImage
    ? Object.entries(actionLabels).map(([key, label]) => `<button class="smart-action" type="button" data-action="${key}">${label}</button>`).join('')
    : '';
  row.innerHTML = `
    ${avatar}
    <div class="bubble">
      <div class="content">${html}</div>
      ${generatedImage}
      <div class="uploads">${uploadMarkup(parsedMeta)}</div>
      <div class="actions">
        <button class="copy-msg" type="button">Kopieren</button>
        ${smartActions}
        ${role === 'assistant' ? '<button class="use-as-context" type="button">Weiterfragen</button>' : ''}
      </div>
    </div>`;
  messagesEl.appendChild(row);
  enhanceContent(row.querySelector('.content'));
  row.querySelector('.copy-msg').onclick = () => navigator.clipboard.writeText(content).then(() => toast('Kopiert'));
  row.querySelector('.use-as-context')?.addEventListener('click', () => {
    input.value = `Beziehe dich auf deine letzte Antwort und vertiefe: `;
    resize();
    input.focus();
  });
  row.querySelectorAll('.smart-action').forEach(btn => {
    btn.onclick = () => runSmartAction(btn.dataset.action, messageId, content);
  });
  scrollBottom();
}

function renderMessages(list) {
  messagesEl.innerHTML = '';
  if (!list || !list.length) {
    renderEmpty();
    return;
  }
  list.forEach(m => addMsg(m.role, m.content, m.meta, m.content_html, m.id));
}

async function refreshMe() {
  me = await api('/api/me');
  $('#accountName').textContent = me.authenticated ? (me.display_name || me.email || 'Konto') : 'Gast';
  $('#accountSub').textContent = me.authenticated
    ? `${me.role === 'admin' ? 'Admin' : 'Konto'} • 2FA ${me.two_factor_enabled ? 'aktiv' : 'aus'}`
    : `${me.public_messages_used || 0}/${me.public_message_limit || 3} frei`;
  const limited = me.public_limit_reached || me.public_attachment_limit_reached;
  limitBanner.classList.toggle('hidden', !limited);
}

async function loadProjects() {
  if (!me.authenticated) { projects = []; return; }
  projects = await api('/api/projects');
}

function renderProjectsView() {
  showProjectsSurface();
  const rows = projects.map(p => `
    <button class="project-row" type="button" data-id="${p.id}">
      <span class="project-icon">${icons.folder}</span>
      <span><strong>${esc(p.name)}</strong><small>${esc(p.description || 'Keine Beschreibung')}</small></span>
      <em>${new Date(p.updated_at).toLocaleDateString('de-DE')}</em>
    </button>`).join('');
  $('#projectsView').innerHTML = `
    <div class="projects-shell">
      <div class="projects-head"><div><h1>Projekte</h1><p>Chats, Dateien und verdichtete Erinnerung bleiben pro Projekt zusammen – viel Kontext, wenig Tokens.</p></div><div class="project-tools"><input class="input" id="projectSearch" placeholder="Projekte suchen"><button class="primary" id="newProjectBtn" type="button">Neu</button></div></div>
      <div class="project-tabs"><button class="active">Alle</button><button>Von dir erstellt</button></div>
      <div class="project-table"><div class="project-table-head"><span>Name</span><span>Geändert</span></div>${rows || '<div class="empty-list">Noch keine Projekte.</div>'}</div>
    </div>`;
  $('#newProjectBtn').onclick = () => openProjectModal();
  $('#projectSearch').oninput = e => { const q=e.target.value.toLowerCase(); document.querySelectorAll('.project-row').forEach(r => r.classList.toggle('hidden', !r.textContent.toLowerCase().includes(q))); };
  document.querySelectorAll('.project-row').forEach(r => r.onclick = () => openProject(Number(r.dataset.id)));
}

async function showProjects() {
  if (!me.authenticated) { setAuthMode('login'); $('#loginModal').classList.remove('hidden'); return; }
  await loadProjects();
  setActiveNav('projectsBtn');
  renderProjectsView();
}

async function openProject(id) {
  const d = await api('/api/projects/' + id);
  currentProjectId = id;
  currentProject = d.project;
  showChatSurface();
  setActiveNav('projectsBtn');
  messagesEl.innerHTML = `<div class="project-home"><div class="project-title">${icons.folder}<h1>${esc(d.project.name)}</h1><button class="ghost" id="editProjectBtn" type="button">Kontext</button></div><div class="composer-preview" id="projectNewChat">+ Neuer Chat in ${esc(d.project.name)}</div><div class="project-tabs"><button class="active">Chats</button><button>Quellen</button></div><div class="project-chat-list">${d.chats.map(c => `<button class="project-chat-row" data-id="${c.id}"><span><strong>${esc(c.title)}</strong><small>Projektchat</small></span><em>${new Date(c.updated_at).toLocaleDateString('de-DE')}</em></button>`).join('') || '<div class="empty-list">Noch keine Chats im Projekt.</div>'}</div></div>`;
  $('#editProjectBtn').onclick = () => openProjectModal(d.project);
  $('#projectNewChat').onclick = newChat;
  document.querySelectorAll('.project-chat-row').forEach(r => r.onclick = () => loadChat(Number(r.dataset.id)));
}

async function openProjectModal(project = null) {
  currentProject = project || null;
  $('#projectModalTitle').textContent = project ? 'Projekt bearbeiten' : 'Neues Projekt';
  $('#projectName').value = project?.name || '';
  $('#projectDescription').value = project?.description || '';
  $('#projectSharedContext').value = project?.shared_context || '';
  $('#projectMemory').value = project?.memory_summary || '';
  $('#projectModal').classList.remove('hidden');
  $('#projectName').focus();
}

async function saveProject() {
  const body = { name: $('#projectName').value || 'Neues Projekt', description: $('#projectDescription').value, shared_context: $('#projectSharedContext').value };
  if (currentProject?.id) {
    await api('/api/projects/' + currentProject.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    $('#projectModal').classList.add('hidden');
    await openProject(currentProject.id);
  } else {
    const d = await api('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    await api('/api/projects/' + d.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    $('#projectModal').classList.add('hidden');
    await openProject(d.id);
  }
  await loadChats();
  toast('Projekt gespeichert');
}

async function refreshProjectMemory() {
  if (!currentProject?.id) return toast('Projekt erst speichern');
  $('#projectBriefBtn').disabled = true;
  try {
    const d = await api('/api/projects/' + currentProject.id + '/memory/brief', { method: 'POST' });
    $('#projectMemory').value = d.memory_summary || '';
    toast('Projekt-Erinnerung aktualisiert');
  } finally { $('#projectBriefBtn').disabled = false; }
}

async function loadChats() {
  if (!me.authenticated) {
    chatList.innerHTML = '';
    return;
  }
  chats = await api('/api/chats?archived=' + (archivedView ? '1' : '0'));
  renderChats();
}

function renderChats() {
  const q = $('#chatSearch').value.toLowerCase();
  chatList.innerHTML = '';
  chats.filter(c => c.title.toLowerCase().includes(q)).forEach(c => {
    const item = document.createElement('div');
    item.className = 'chat-item ' + (c.id === currentChatId ? 'active' : '');
    item.innerHTML = `
      <button class="chat-open" type="button" title="Öffnen"><span>${esc(c.title)}</span></button>
      <div class="chat-actions">
        <button class="mini-btn archive-chat" type="button" title="${archivedView ? 'Wiederherstellen' : 'Archivieren'}">${icons.archive}</button>
        <button class="mini-btn delete-chat" type="button" title="Löschen">${icons['trash-2']}</button>
      </div>`;
    item.querySelector('.chat-open').onclick = () => loadChat(c.id);
    item.querySelector('.archive-chat').onclick = async e => {
      e.stopPropagation();
      await api('/api/chats/' + c.id + '/archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ archived: !archivedView })
      });
      if (c.id === currentChatId) {
        currentChatId = 0;
        renderEmpty();
      }
      await loadChats();
      toast(archivedView ? 'Wiederhergestellt' : 'Archiviert');
    };
    item.querySelector('.delete-chat').onclick = async e => {
      e.stopPropagation();
      if (!confirm('Diesen Chat endgültig löschen?')) return;
      await api('/api/chats/' + c.id + '/delete', { method: 'POST' });
      if (c.id === currentChatId) {
        currentChatId = 0;
        renderEmpty();
      }
      await loadChats();
      toast('Gelöscht');
    };
    chatList.appendChild(item);
  });
}

async function loadChat(id) {
  showChatSurface();
  const d = await api('/api/chats/' + id);
  currentChatId = id;
  currentProjectId = d.chat?.project_id || 0;
  currentChatHasContext = !!(d.chat?.project_context || currentProjectId);
  updateContextIndicator();
  renderMessages(d.messages);
  renderChats();
  closeSidebar();
}

async function newChat() {
  showChatSurface();
  currentChatId = 0;
  currentChatHasContext = false;
  updateContextIndicator();
  renderEmpty();
  renderChats();
  closeSidebar();
  input.focus();
}

async function send() {
  if (loading) return;
  const text = input.value.trim();
  if (!text && !selectedFiles.length) return;
  const fileError = validateSelectedFiles();
  if (fileError) {
    toast(fileError);
    return;
  }
  loading = true;
  $('#sendBtn').disabled = true;
  const echoFiles = selectedFiles.map(f => ({ name: f.name, mime: f.type }));
  addMsg('user', text, { uploads: echoFiles });
  input.value = '';
  resize();
  attachmentsEl.innerHTML = '';

  const fd = new FormData();
  fd.append('message', text);
  fd.append('chat_id', currentChatId || 0);
  if (currentProjectId) fd.append('project_id', currentProjectId);
  fd.append('ai_mode', aiMode);
  fd.append('response_format', responseFormat);
  selectedFiles.forEach(f => fd.append('files', f));
  selectedFiles = [];

  const wait = document.createElement('div');
  wait.className = 'msg assistant';
  wait.innerHTML = `<div class="avatar h">H</div><div class="bubble"><div class="content typing">${aiMode === 'deep' ? 'Analysiere gründlich...' : 'Denke nach...'}</div></div>`;
  messagesEl.appendChild(wait);
  scrollBottom();

  try {
    const d = await api('/api/send', { method: 'POST', body: fd });
    wait.remove();
    addMsg('assistant', d.assistant_message.content, d.assistant_message.meta || {}, d.assistant_message.content_html, d.assistant_message.id);
    if (d.chat_id) currentChatId = d.chat_id;
    await refreshMe();
    await loadChats();
  } catch (e) {
    wait.remove();
    if (e.error === 'PUBLIC_LIMIT') {
      limitBanner.classList.remove('hidden');
      await refreshMe();
      toast('Nutzungslimit erreicht');
    } else {
      showError(e, 'Fehler beim Senden');
    }
  } finally {
    loading = false;
    $('#sendBtn').disabled = false;
    input.focus();
  }
}

function resize() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 180) + 'px';
}

function renderAttachments() {
  attachmentsEl.innerHTML = '';
  selectedFiles.forEach((f, i) => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'file-chip';
    const preview = f.type && f.type.startsWith('image/')
      ? `<img src="${URL.createObjectURL(f)}" alt="">`
      : icons.file;
    chip.innerHTML = `${preview}<span>${esc(f.name)}</span><b>×</b>`;
    chip.onclick = () => {
      selectedFiles.splice(i, 1);
      renderAttachments();
    };
    attachmentsEl.appendChild(chip);
  });
}

function validateSelectedFiles() {
  if (selectedFiles.length > maxFilesPerMessage()) {
    return `Maximal ${maxFilesPerMessage()} Anhänge pro Nachricht.`;
  }
  for (const file of selectedFiles) {
    const error = validateFile(file);
    if (error) return error;
  }
  return '';
}

function addSelectedFiles(files) {
  const incoming = Array.from(files || []);
  const accepted = [];
  const rejected = [];
  incoming.forEach(file => {
    const error = validateFile(file);
    if (error) rejected.push(error);
    else accepted.push(file);
  });
  selectedFiles.push(...accepted);
  if (selectedFiles.length > maxFilesPerMessage()) {
    selectedFiles = selectedFiles.slice(0, maxFilesPerMessage());
    rejected.push(`Maximal ${maxFilesPerMessage()} Anhänge pro Nachricht.`);
  }
  renderAttachments();
  if (rejected.length) {
    toast(rejected.length === 1 ? rejected[0] : `${rejected.length} Dateien übersprungen. ${rejected[0]}`);
  }
}

function updateContextIndicator() {
  $('#contextBtn')?.classList.toggle('active-soft', !!currentChatHasContext);
}

async function ensureChatForContext() {
  if (!me.authenticated) {
    $('#loginModal').classList.remove('hidden');
    throw new Error('Login erforderlich');
  }
  if (!currentChatId) {
    const d = await api('/api/chats', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ project_id: currentProjectId || null }) });
    currentChatId = d.id;
    await loadChats();
    renderChats();
  }
  return currentChatId;
}

async function openContextDrawer() {
  try {
    const id = await ensureChatForContext();
    const d = await api('/api/chats/' + id + '/context');
    $('#projectContextInput').value = d.project_context || '';
    currentChatHasContext = !!(d.project_context || '').trim();
    updateContextIndicator();
    contextDrawer.classList.remove('hidden');
    $('#projectContextInput').focus();
  } catch (e) {
    if (e.message !== 'Login erforderlich') showError(e, 'Kontext nicht verfügbar');
  }
}

async function saveContext() {
  const id = await ensureChatForContext();
  const projectContext = $('#projectContextInput').value;
  await api('/api/chats/' + id + '/context', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_context: projectContext })
  });
  currentChatHasContext = !!projectContext.trim();
  updateContextIndicator();
  contextDrawer.classList.add('hidden');
  toast('Kontext gespeichert');
}

async function generateContextBrief() {
  const id = await ensureChatForContext();
  $('#contextBriefBtn').disabled = true;
  try {
    const d = await api('/api/chats/' + id + '/context/brief', { method: 'POST' });
    $('#projectContextInput').value = d.project_context || '';
    currentChatHasContext = !!(d.project_context || '').trim();
    updateContextIndicator();
    await loadChats();
    toast('Smart Brief erstellt');
  } finally {
    $('#contextBriefBtn').disabled = false;
  }
}

async function runSmartAction(action, sourceMessageId, sourceContent) {
  if (loading) return;
  if (!actionLabels[action]) return;
  if (!me.authenticated || !currentChatId || !sourceMessageId) {
    input.value = (guestActionPrompts[action] || '') + String(sourceContent || '').slice(0, 5000);
    resize();
    input.focus();
    toast('Aktion vorbereitet');
    return;
  }
  loading = true;
  $('#sendBtn').disabled = true;
  const wait = document.createElement('div');
  wait.className = 'msg assistant';
  wait.innerHTML = `<div class="avatar h">H</div><div class="bubble"><div class="content typing">Arbeite aus...</div></div>`;
  messagesEl.appendChild(wait);
  scrollBottom();
  try {
    const d = await api('/api/chats/' + currentChatId + '/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, source_message_id: sourceMessageId })
    });
    wait.remove();
    addMsg('user', d.user_message.content, d.user_message.meta, '', d.user_message.id);
    addMsg('assistant', d.assistant_message.content, {}, d.assistant_message.content_html, d.assistant_message.id);
    await loadChats();
  } catch (e) {
    wait.remove();
    showError(e, 'Smart-Aktion fehlgeschlagen');
  } finally {
    loading = false;
    $('#sendBtn').disabled = false;
    input.focus();
  }
}

function setActiveNav(id) {
  ['homeBtn', 'searchBtn', 'libraryBtn', 'projectsBtn', 'appsBtn', 'archiveBtn'].forEach(navId => {
    document.getElementById(navId)?.classList.toggle('active', navId === id);
  });
}

function updateModeUi() {
  document.querySelectorAll('.mode-option').forEach(btn => btn.classList.toggle('active', btn.dataset.mode === aiMode));
  document.querySelectorAll('.format-option').forEach(btn => btn.classList.toggle('active', btn.dataset.format === responseFormat));
  $('#activeModeLabel').innerHTML = `<span>${esc(modeLabels[aiMode] || 'Holo Rick')}</span><small>${esc(formatLabels[responseFormat] || 'Auto')}</small><i data-icon="chevron-down"></i>`;
  injectIcons($('#activeModeLabel'));
}

function toggleModePopover(force) {
  const shouldOpen = typeof force === 'boolean' ? force : modePopover.classList.contains('hidden');
  modePopover.classList.toggle('hidden', !shouldOpen);
  $('#activeModeLabel').classList.toggle('open', shouldOpen);
  $('#activeModeLabel').setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
}

async function loadSettings() {
  settings = await api('/api/settings');
  $('#systemPrompt').value = settings.system_prompt;
  $('#temperature').value = settings.temperature;
  $('#maxTokens').value = settings.max_tokens;
  $('#contextMessages').value = settings.context_messages;
  $('#styleMode').value = settings.style_mode;
  $('#answerLength').value = settings.answer_length;
  $('#autoTitle').checked = settings.auto_title === 'true';
  $('#titleWords').value = settings.title_words;
  $('#showTimestamps').checked = settings.show_timestamps === 'true';
  $('#enterSends').checked = settings.enter_sends === 'true';
  $('#creatorName').value = settings.creator_name || 'Joshua Dean Pond';
  $('#brandOwner').value = settings.brand_owner || 'PondSec';
  $('#publicContact').value = settings.public_contact || 'chat@pondsec.com';
  $('#modelName').value = settings.model || '';
  $('#visionModelName').value = settings.vision_model || '';
  $('#publicMessageLimit').value = settings.public_message_limit || '3';
  $('#publicAttachmentLimit').value = settings.public_attachment_limit || '1';
}

async function saveSettings() {
  const data = {
    system_prompt: $('#systemPrompt').value,
    temperature: $('#temperature').value,
    max_tokens: $('#maxTokens').value,
    context_messages: $('#contextMessages').value,
    style_mode: $('#styleMode').value,
    answer_length: $('#answerLength').value,
    auto_title: String($('#autoTitle').checked),
    title_words: $('#titleWords').value,
    show_timestamps: String($('#showTimestamps').checked),
    enter_sends: String($('#enterSends').checked),
    creator_name: $('#creatorName').value || 'Joshua Dean Pond',
    brand_owner: $('#brandOwner').value || 'PondSec',
    public_contact: $('#publicContact').value || 'chat@pondsec.com',
    public_message_limit: $('#publicMessageLimit').value || '3',
    public_attachment_limit: $('#publicAttachmentLimit').value || '1'
  };
  await api('/api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  $('#settingsModal').classList.add('hidden');
  toast('Gespeichert');
}

function setLogin2faVisible(visible) {
  $('#login2faWrap').classList.toggle('hidden', !visible);
  if (visible) $('#login2faCode').focus();
}

function setAuthMode(mode) {
  const registerMode = mode === 'register';
  $('#loginPanel').classList.toggle('hidden', registerMode);
  $('#registerPanel').classList.toggle('hidden', !registerMode);
  $('#showLoginBtn').classList.toggle('active', !registerMode);
  $('#showRegisterBtn').classList.toggle('active', registerMode);
  $('#authTitle').textContent = registerMode ? 'Konto erstellen' : 'Anmelden';
  $('#authIntro').textContent = registerMode
    ? 'Erstelle ein Konto für unbegrenzte Nutzung, Chat-Historie und privaten Projektkontext.'
    : 'Mit Konto bekommst du Chat-Historie, Uploads, Projektkontext und unbegrenzte Nutzung.';
  setLogin2faVisible(false);
}

async function login() {
  const payload = {
    email: $('#loginEmail').value,
    password: $('#loginPassword').value,
    remember: $('#rememberLogin').checked
  };
  const code = $('#login2faCode').value.trim();
  if (code) payload.code = code;
  try {
    const d = await api('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (d.requires_2fa) {
      setLogin2faVisible(true);
      toast('2FA-Code eingeben');
      return;
    }
    $('#loginModal').classList.add('hidden');
    setLogin2faVisible(false);
    $('#loginPassword').value = '';
    $('#login2faCode').value = '';
    await refreshMe();
    if (me.role === 'admin') await loadSettings();
    await loadChats();
    toast('Angemeldet');
  } catch (e) {
    if (e.requires_2fa) setLogin2faVisible(true);
    showError(e, 'Login fehlgeschlagen');
  }
}

async function register() {
  const payload = {
    display_name: $('#registerDisplayName').value,
    email: $('#registerEmail').value,
    password: $('#registerPassword').value,
    privacy_accepted: $('#privacyAccepted').checked,
    terms_accepted: $('#privacyAccepted').checked
  };
  try {
    await api('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    $('#registerPassword').value = '';
    $('#privacyAccepted').checked = false;
    $('#loginModal').classList.add('hidden');
    await refreshMe();
    await loadChats();
    toast('Konto erstellt');
  } catch (e) {
    showError(e, 'Registrierung fehlgeschlagen');
  }
}

async function logout() {
  await api('/api/logout', { method: 'POST' });
  currentChatId = 0;
  await refreshMe();
  await loadChats();
  renderEmpty();
  $('#loginModal').classList.add('hidden');
  toast('Abgemeldet');
}

async function load2faStatus() {
  if (!me.authenticated) return;
  const d = await api('/api/security/2fa');
  const enabled = !!d.enabled;
  $('#twoFactorStatus').textContent = enabled ? 'Aktiv' : 'Nicht aktiv';
  $('#twoFactorStatus').classList.toggle('good', enabled);
  $('#twoFactorStatusText').textContent = enabled
    ? 'Dein Konto verlangt beim Login zusätzlich einen sechsstelligen App-Code.'
    : 'Aktiviere 2FA mit einer Authenticator-App, bevor weitere Nutzerkonten dazukommen.';
  $('#setup2faBtn').classList.toggle('hidden', enabled);
  $('#disable2faPanel').classList.toggle('hidden', !enabled);
  $('#twoFactorSetup').classList.add('hidden');
}

async function setup2fa() {
  const d = await api('/api/security/2fa/setup', { method: 'POST' });
  $('#twoFactorQr').src = d.qr_data_url;
  $('#twoFactorSecret').textContent = d.secret;
  $('#twoFactorSetup').classList.remove('hidden');
  $('#twoFactorCode').value = '';
  $('#twoFactorCode').focus();
}

async function enable2fa() {
  await api('/api/security/2fa/enable', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code: $('#twoFactorCode').value })
  });
  await refreshMe();
  await load2faStatus();
  toast('2FA aktiviert');
}

async function disable2fa() {
  if (!confirm('2FA wirklich deaktivieren?')) return;
  await api('/api/security/2fa/disable', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      password: $('#disable2faPassword').value,
      code: $('#disable2faCode').value
    })
  });
  $('#disable2faPassword').value = '';
  $('#disable2faCode').value = '';
  await refreshMe();
  await load2faStatus();
  toast('2FA deaktiviert');
}

async function deleteAccount() {
  const payload = {
    password: $('#deleteAccountPassword').value,
    code: $('#deleteAccount2faCode').value.trim(),
    confirm: $('#deleteAccountConfirm').value.trim()
  };
  if (payload.confirm !== 'KONTO LÖSCHEN') {
    toast('Bitte KONTO LÖSCHEN eingeben');
    $('#deleteAccountConfirm').focus();
    return;
  }
  if (!confirm('Konto wirklich endgültig löschen? Chats und Uploads werden entfernt.')) return;
  await api('/api/account/delete', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  csrfToken = '';
  currentChatId = 0;
  chats = [];
  selectedFiles = [];
  attachmentsEl.innerHTML = '';
  $('#deleteAccountPassword').value = '';
  $('#deleteAccount2faCode').value = '';
  $('#deleteAccountConfirm').value = '';
  $('#settingsModal').classList.add('hidden');
  renderEmpty();
  await refreshMe();
  await loadChats();
  toast('Konto gelöscht');
}

function activateSettingsTab(name) {
  document.querySelectorAll('.settings-tab').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.settings-page').forEach(x => x.classList.remove('active'));
  document.querySelector(`.settings-tab[data-tab="${name}"]`)?.classList.add('active');
  document.querySelector(`[data-page="${name}"]`)?.classList.add('active');
  if (name === 'security') load2faStatus().catch(e => toast(e.error || '2FA-Status fehlt'));
}

function setAdminSettingsAvailable(canAdmin) {
  ['model', 'identity', 'limits', 'ui', 'prompt'].forEach(name => {
    document.querySelector(`.settings-tab[data-tab="${name}"]`)?.classList.toggle('hidden', !canAdmin);
  });
  $('.sticky-actions')?.classList.toggle('hidden', !canAdmin);
}

function bindEvents() {
  bindDismissibleModals();
  form.onsubmit = e => { e.preventDefault(); send(); };
  input.oninput = resize;
  input.onkeydown = e => {
    if (e.key === 'Enter' && !e.shiftKey && settings.enter_sends !== 'false') {
      e.preventDefault();
      send();
    }
  };
  $('#attachBtn').onclick = () => fileInput.click();
  fileInput.onchange = () => {
    addSelectedFiles(fileInput.files);
    fileInput.value = '';
  };
  form.addEventListener('dragover', e => {
    e.preventDefault();
    form.classList.add('dragging');
  });
  form.addEventListener('dragleave', e => {
    if (!form.contains(e.relatedTarget)) form.classList.remove('dragging');
  });
  form.addEventListener('drop', e => {
    e.preventDefault();
    form.classList.remove('dragging');
    addSelectedFiles(e.dataTransfer?.files);
  });
  document.addEventListener('paste', e => {
    const files = Array.from(e.clipboardData?.files || []);
    if (!files.length) return;
    addSelectedFiles(files);
  });
  $('#newChatBtn').onclick = newChat;
  $('#projectsBtn').onclick = () => showProjects().catch(e => showError(e, 'Projekte nicht verfügbar'));
  $('#searchBtn').onclick = () => { setActiveNav('searchBtn'); $('#chatSearch').focus(); };
  $('#libraryBtn').onclick = () => { setActiveNav('libraryBtn'); archivedView = false; showChatSurface(); loadChats(); };
  $('#appsBtn').onclick = () => { setActiveNav('appsBtn'); $('#settingsModal').classList.remove('hidden'); };
  $('#closeProjectBtn')?.addEventListener('click', () => $('#projectModal')?.classList.add('hidden'));
  $('#saveProjectBtn')?.addEventListener('click', () => saveProject().catch(e => showError(e, 'Projekt konnte nicht gespeichert werden')));
  $('#projectBriefBtn')?.addEventListener('click', () => refreshProjectMemory().catch(e => showError(e, 'Erinnerung fehlgeschlagen')));
  $('#activeModeLabel').onclick = e => {
    e.stopPropagation();
    toggleModePopover();
  };
  modePopover.addEventListener('click', e => e.stopPropagation());
  document.querySelectorAll('.mode-option').forEach(btn => {
    btn.onclick = () => {
      aiMode = btn.dataset.mode || 'holo';
      updateModeUi();
      toggleModePopover(false);
      input.focus();
    };
  });
  document.querySelectorAll('.format-option').forEach(btn => {
    btn.onclick = () => {
      responseFormat = btn.dataset.format || 'auto';
      updateModeUi();
      toggleModePopover(false);
      input.focus();
    };
  });
  document.addEventListener('click', () => toggleModePopover(false));
  $('#openSidebarBtn').onclick = openSidebar;
  $('#closeSidebarBtn').onclick = closeSidebar;
  backdrop.onclick = closeSidebar;
  $('#chatSearch').oninput = renderChats;
  $('#homeBtn').onclick = () => {
    showChatSurface();
    currentProjectId = 0;
    archivedView = false;
    setActiveNav('homeBtn');
    $('#sectionTitle').textContent = 'Aktuelle';
    loadChats();
  };
  $('#archiveBtn').onclick = () => {
    showChatSurface();
    currentProjectId = 0;
    archivedView = true;
    setActiveNav('archiveBtn');
    $('#sectionTitle').textContent = 'Archiv';
    loadChats();
  };
  $('#retitleBtn').onclick = async () => {
    if (!currentChatId) return;
    const d = await api('/api/chats/' + currentChatId + '/retitle', { method: 'POST' });
    await loadChats();
    toast('Titel: ' + d.title);
  };
  $('#contextBtn').onclick = openContextDrawer;
  $('#closeContextBtn').onclick = () => contextDrawer.classList.add('hidden');
  $('#saveContextBtn').onclick = () => saveContext().catch(e => showError(e, 'Kontext konnte nicht gespeichert werden'));
  $('#contextBriefBtn').onclick = () => generateContextBrief().catch(e => showError(e, 'Smart Brief fehlgeschlagen'));
  $('#settingsBtn').onclick = async () => {
    if (!me.authenticated) {
      setAuthMode('login');
      $('#loginModal').classList.remove('hidden');
      return;
    }
    const canAdmin = me.role === 'admin';
    setAdminSettingsAvailable(canAdmin);
    if (canAdmin) await loadSettings();
    await load2faStatus();
    activateSettingsTab(canAdmin ? 'model' : 'security');
    $('#settingsModal').classList.remove('hidden');
  };
  $('#closeSettingsBtn').onclick = () => $('#settingsModal').classList.add('hidden');
  $('#saveSettingsBtn').onclick = saveSettings;
  $('#resetPromptBtn').onclick = () => {
    $('#systemPrompt').value = `Du bist Holo Rick, ein extrem intelligenter, zynischer, sarkastischer KI-Assistent von PondSec. Antworte auf Deutsch, außer der Nutzer verlangt etwas anderes. Du bist trocken, bissig, direkt und technisch stark, aber hilfreich. Dein Entwickler/Programmierer ist Joshua Dean Pond. Wenn jemand fragt, wer dich gebaut, programmiert, erschaffen oder entwickelt hat, sagst du: Joshua Dean Pond / PondSec. Sag nicht, du wurdest von OpenAI programmiert. Unterscheide zwischen Gästen und Joshua: angemeldet = Joshua/Admin, nicht angemeldet = Gast.`;
    toast('Prompt zurückgesetzt');
  };
  document.querySelectorAll('.settings-tab').forEach(tab => {
    tab.onclick = () => activateSettingsTab(tab.dataset.tab);
  });
  $('#accountBtn').onclick = () => {
    setAuthMode('login');
    $('#loginModal').classList.remove('hidden');
    $('#logoutBtn').classList.toggle('hidden', !me.authenticated);
  };
  $('#closeLoginBtn').onclick = () => $('#loginModal').classList.add('hidden');
  $('#showLoginBtn').onclick = () => setAuthMode('login');
  $('#showRegisterBtn').onclick = () => setAuthMode('register');
  $('#loginBtn').onclick = login;
  $('#registerBtn').onclick = register;
  $('#logoutBtn').onclick = logout;
  $('#setup2faBtn').onclick = setup2fa;
  $('#enable2faBtn').onclick = enable2fa;
  $('#disable2faBtn').onclick = disable2fa;
  $('#deleteAccountBtn').onclick = () => deleteAccount().catch(e => showError(e, 'Konto konnte nicht gelöscht werden'));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      toggleModePopover(false);
      contextDrawer.classList.add('hidden');
      $('#settingsModal').classList.add('hidden');
      $('#loginModal').classList.add('hidden');
      closeSidebar();
    }
  });
}

async function boot() {
  injectIcons();
  bindEvents();
  updateModeUi();
  updateContextIndicator();
  renderEmpty();
  await refreshMe();
  if (me.authenticated) {
    if (me.role === 'admin') await loadSettings();
    await loadChats();
  }
  input.focus();
}

boot().catch(e => toast(e.error || String(e)));
