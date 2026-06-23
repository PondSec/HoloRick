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
const workspacePanel = $('#workspacePanel');
const workspaceBody = $('#workspaceBody');

let chats = [];
let currentChatId = 0;
let currentProjectId = 0;
let projects = [];
let currentProject = null;
let currentProjectMemory = [];
let archivedView = false;
let me = { authenticated: false };
let selectedFiles = [];
let settings = {};
let loading = false;
let csrfToken = '';
let aiMode = 'holo';
let responseFormat = 'auto';
let currentChatHasContext = false;
let currentShareToken = '';
let currentSharedChat = false;
let workspaceTab = localStorage.getItem('holo_rick_workspace_tab') || 'answer';
let workspaceCollapsed = localStorage.getItem('holo_rick_workspace_collapsed') !== 'false';
let workspaceOpen = false;
let currentArtifacts = [];
let selectedArtifactId = '';
let selectedAnswer = null;
let selectedMetadata = null;
let memoryItems = [];
let memoryFilters = { q: '', scope: 'all', archived: false };
let editingMemoryId = '';
let onboardingStepIndex = 0;
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
  summary: { label: 'Kurz', icon: 'file-text' },
  tasks: { label: 'To-dos', icon: 'list-checks' },
  risks: { label: 'Risiken', icon: 'alert-triangle' }
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
  'home': '<svg viewBox="0 0 24 24"><path d="m3 11 9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>',
  'trash': '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>',
  'briefcase': '<svg viewBox="0 0 24 24"><path d="M10 6V5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2v1"/><rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 12h18"/></svg>',
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
  'brain': '<svg viewBox="0 0 24 24"><path d="M9 3a3 3 0 0 0-3 3v1a3 3 0 0 0-2 5.2A3.5 3.5 0 0 0 7.5 19H9V3Z"/><path d="M15 3a3 3 0 0 1 3 3v1a3 3 0 0 1 2 5.2A3.5 3.5 0 0 1 16.5 19H15V3Z"/><path d="M9 8H7.5M15 8h1.5M9 14H7.5M15 14h1.5"/></svg>',
  'layout-panel-right': '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/><path d="m10 9-3 3 3 3"/></svg>',
  'workspace-expand': '<svg viewBox="0 0 24 24"><path d="M20 4v16"/><path d="M4 12h12"/><path d="m10 6-6 6 6 6"/></svg>',
  'key-round': '<svg viewBox="0 0 24 24"><path d="M2 18v3h3l9.2-9.2"/><circle cx="16.5" cy="7.5" r="5.5"/></svg>',
  'smartphone': '<svg viewBox="0 0 24 24"><rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/></svg>',
  'copy': '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><rect x="2" y="2" width="13" height="13" rx="2"/></svg>',
  'download': '<svg viewBox="0 0 24 24"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>',
  'folder': '<svg viewBox="0 0 24 24"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.5L10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2Z"/></svg>',
  'more-horizontal': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>',
  'list-checks': '<svg viewBox="0 0 24 24"><path d="m3 7 2 2 4-4"/><path d="M11 7h10"/><path d="m3 17 2 2 4-4"/><path d="M11 17h10"/></svg>',
  'alert-triangle': '<svg viewBox="0 0 24 24"><path d="m12 3 10 18H2Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
  'help-circle': '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 1 1 5.8 1c-.7 1-1.9 1.3-2.4 2.4"/><path d="M12 17h.01"/></svg>'
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

function artifactLabel(artifact = {}) {
  const lang = artifact.language ? ` · ${artifact.language}` : '';
  return `${artifact.type || 'text'}${lang} · v${artifact.version || 1}`;
}

function updateWorkspaceShell() {
  workspacePanel?.classList.toggle('collapsed', workspaceCollapsed);
  workspacePanel?.classList.toggle('open', workspaceOpen);
  document.body.classList.toggle('workspace-collapsed', workspaceCollapsed);
  document.body.classList.toggle('workspace-open', workspaceOpen);
  $('#workspaceTabs')?.querySelectorAll('button').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === workspaceTab));
  const collapseBtn = $('#collapseWorkspaceBtn');
  if (collapseBtn) {
    collapseBtn.innerHTML = workspaceCollapsed ? icons['workspace-expand'] : icons['layout-panel-right'];
    collapseBtn.title = workspaceCollapsed ? 'Workspace ausklappen' : 'Workspace einklappen';
    collapseBtn.setAttribute('aria-label', collapseBtn.title);
  }
}

function setWorkspaceTab(tab, open = true) {
  workspaceTab = tab || 'answer';
  localStorage.setItem('holo_rick_workspace_tab', workspaceTab);
  if (open) {
    workspaceCollapsed = false;
    workspaceOpen = true;
    localStorage.setItem('holo_rick_workspace_collapsed', 'false');
  }
  renderWorkspace();
}

function selectedArtifact() {
  if (!selectedArtifactId && currentArtifacts.length) selectedArtifactId = currentArtifacts[0].id;
  return currentArtifacts.find(a => a.id === selectedArtifactId) || currentArtifacts[0] || null;
}

function mergeArtifacts(artifacts = []) {
  const byId = new Map(currentArtifacts.map(a => [a.id, a]));
  artifacts.forEach(artifact => {
    if (artifact?.id) byId.set(artifact.id, { ...(byId.get(artifact.id) || {}), ...artifact });
  });
  currentArtifacts = Array.from(byId.values()).sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')));
  if (!selectedArtifactId && currentArtifacts[0]) selectedArtifactId = currentArtifacts[0].id;
}

function collectArtifactsFromMessages(list = []) {
  currentArtifacts = [];
  selectedArtifactId = '';
  (list || []).forEach(message => mergeArtifacts((message.artifacts || []).map(a => ({ ...a, message_id: message.id }))));
}

function workspaceEmpty() {
  return `<div class="workspace-empty"><strong>Noch kein Artifact.</strong><p>Wenn Holo Rick Dateien, Code, Tabellen oder Vorschauen erzeugt, erscheinen sie hier.</p></div>`;
}

function renderAnswerTab() {
  if (!selectedAnswer) return workspaceEmpty();
  const meta = parseMeta(selectedAnswer.meta);
  const usage = meta.efficiency || {};
  const stats = usage.model ? `
    <div class="usage-grid">
      <span>Modell</span><strong>${esc(usage.model)}</strong>
      <span>Cache</span><strong>${esc(usage.cache_status || 'n/a')}</strong>
      <span>Input</span><strong>${esc(usage.input_tokens || 0)} Token</strong>
      <span>Output</span><strong>${esc(usage.output_tokens || 0)} Token</strong>
    </div>` : '<p class="muted">Für diese Antwort sind keine Token-Metriken gespeichert.</p>';
  return `
    <div class="workspace-section">
      <h3>Aktuelle Antwort</h3>
      <div class="workspace-answer">${selectedAnswer.content_html || plainTextToHtml(selectedAnswer.content || '')}</div>
      ${stats}
    </div>`;
}

function renderFilesTab() {
  if (!currentArtifacts.length) return workspaceEmpty();
  const artifact = selectedArtifact();
  const rows = currentArtifacts.map(item => `
    <button class="artifact-row ${item.id === artifact?.id ? 'active' : ''}" data-id="${esc(item.id)}" type="button">
      <strong>${esc(item.title || 'Artifact')}</strong>
      <small>${esc(artifactLabel(item))}</small>
    </button>`).join('');
  const editable = artifact && !['file/export'].includes(artifact.type);
  const content = artifact ? esc(artifact.content || '') : '';
  const versions = (artifact?.versions || [{ version: artifact?.version || 1, created_at: artifact?.updated_at, title: artifact?.title }]).map(v => `
    <div class="version-row"><strong>v${esc(v.version)}</strong><span>${esc(v.title || artifact?.title || 'Artifact')}</span><small>${v.created_at ? new Date(v.created_at).toLocaleString('de-DE') : ''}</small></div>`).join('');
  return `
    <div class="artifact-layout">
      <div class="artifact-list">${rows}</div>
      <div class="artifact-detail">
        ${artifact ? `
          <div class="artifact-detail-head">
            <div><h3>${esc(artifact.title || 'Artifact')}</h3><small>${esc(artifactLabel(artifact))}</small></div>
            <div class="artifact-tools">
              <button class="ghost mini-action" id="copyArtifactBtn" type="button">Kopieren</button>
              <button class="ghost mini-action" id="downloadArtifactBtn" type="button">Download</button>
              ${editable ? '<button class="primary mini-action" id="saveArtifactBtn" type="button">Speichern</button>' : ''}
              <button class="ghost mini-action danger-text" id="deleteArtifactBtn" type="button">Löschen</button>
            </div>
          </div>
          ${editable ? `<textarea class="artifact-editor" id="artifactEditor">${content}</textarea>` : `<pre class="artifact-pre">${content}</pre>`}
          <div class="artifact-versions"><h4>Versionen</h4>${versions}</div>
        ` : workspaceEmpty()}
      </div>
    </div>`;
}

function renderPreviewTab() {
  const artifact = selectedArtifact();
  if (!artifact) return workspaceEmpty();
  if (artifact.type === 'html') {
    return `<iframe class="artifact-preview" sandbox="allow-forms allow-popups" srcdoc="${esc(artifact.content || '')}"></iframe>`;
  }
  if (artifact.type === 'json') {
    let formatted = artifact.content || '';
    try { formatted = JSON.stringify(JSON.parse(formatted), null, 2); } catch {}
    return `<pre class="artifact-pre">${esc(formatted)}</pre>`;
  }
  if (artifact.type === 'markdown' || artifact.type === 'table/csv') {
    return `<pre class="artifact-pre">${esc(artifact.content || '')}</pre>`;
  }
  return `<div class="workspace-empty"><strong>Keine Vorschau für diesen Typ.</strong><p>Nutze den Dateien-Tab zum Anzeigen und Bearbeiten.</p></div>`;
}

function renderConsoleTab() {
  const logs = currentArtifacts.filter(a => a.type === 'log/result');
  if (!logs.length) {
    return `<div class="workspace-empty"><strong>Noch keine Konsolenläufe.</strong><p>Agent-Logs und Resultate werden hier sichtbar, sobald Holo Rick Läufe speichert.</p></div>`;
  }
  return logs.map(log => `<div class="log-card"><strong>${esc(log.title)}</strong><pre>${esc(log.content || '')}</pre></div>`).join('');
}

function renderTasksTab() {
  const tasks = parseMeta(selectedAnswer?.meta).tasks || [];
  if (!tasks.length) {
    return `<div class="workspace-empty"><strong>Keine Tasks.</strong><p>Vorbereitete Agent-Status: pending, running, success, failed, cancelled.</p></div>`;
  }
  return tasks.map(task => `<div class="task-row ${esc(task.status || 'pending')}"><strong>${esc(task.title || task.label || 'Task')}</strong><span>${esc(task.status || 'pending')}</span></div>`).join('');
}

function renderSourcesTab() {
  const md = selectedMetadata || selectedAnswer?.answer_metadata || {};
  const sources = md.sources || [];
  const work = md.work_summary || [];
  const uncertainties = md.uncertainties || [];
  const checked = md.checked_items || [];
  const sourceHtml = sources.length
    ? sources.map(s => `<div class="source-row"><strong>${esc(s.title || 'Quelle')}</strong><span>${esc(s.type || 'manual')}</span>${s.excerpt ? `<p>${esc(s.excerpt)}</p>` : ''}</div>`).join('')
    : '<p class="muted">Für diese Antwort wurden keine Quellen gespeichert.</p>';
  const workHtml = work.length
    ? work.map(w => `<div class="work-row ${esc(w.status || 'done')}"><strong>${esc(w.label || 'Schritt')}</strong><span>${esc(w.status || 'done')}</span>${w.detail ? `<p>${esc(w.detail)}</p>` : ''}</div>`).join('')
    : '<p class="muted">Kein Arbeitsnachweis vorhanden.</p>';
  return `
    <div class="workspace-section">
      <h3>Quellen</h3>${sourceHtml}
      <h3>Arbeitsnachweis</h3>${workHtml}
      <h3>Unsicherheit</h3>
      <div class="confidence ${esc(md.confidence || 'medium')}">${esc(md.confidence || 'medium')}</div>
      ${uncertainties.length ? `<ul class="plain-list">${uncertainties.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '<p class="muted">Keine Unsicherheiten gespeichert.</p>'}
      <h3>Kontext</h3>
      ${checked.length ? `<ul class="plain-list">${checked.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : '<p class="muted">Kein geprüfter Kontext gespeichert.</p>'}
    </div>`;
}

function renderWorkspace() {
  if (!workspaceBody) return;
  updateWorkspaceShell();
  const renderers = {
    answer: renderAnswerTab,
    files: renderFilesTab,
    preview: renderPreviewTab,
    console: renderConsoleTab,
    tasks: renderTasksTab,
    sources: renderSourcesTab
  };
  workspaceBody.innerHTML = (renderers[workspaceTab] || renderAnswerTab)();
  enhanceContent(workspaceBody);
  bindWorkspaceContent();
}

function bindWorkspaceContent() {
  workspaceBody?.querySelectorAll('.artifact-row').forEach(btn => {
    btn.onclick = () => {
      selectedArtifactId = btn.dataset.id || '';
      renderWorkspace();
    };
  });
  $('#copyArtifactBtn')?.addEventListener('click', () => {
    const artifact = selectedArtifact();
    if (!artifact) return;
    navigator.clipboard.writeText(artifact.content || '').then(() => toast('Artifact kopiert'));
  });
  $('#downloadArtifactBtn')?.addEventListener('click', () => {
    const artifact = selectedArtifact();
    if (!artifact) return;
    const blob = new Blob([artifact.content || ''], { type: artifact.type === 'html' ? 'text/html' : 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(artifact.title || 'artifact').replace(/[^\w.-]+/g, '_')}.${artifact.language || (artifact.type === 'html' ? 'html' : 'txt')}`;
    a.click();
    URL.revokeObjectURL(url);
  });
  $('#saveArtifactBtn')?.addEventListener('click', async () => {
    const artifact = selectedArtifact();
    if (!artifact) return;
    const content = $('#artifactEditor')?.value || '';
    const updated = await api('/api/artifacts/' + artifact.id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...artifact, content })
    });
    mergeArtifacts([updated]);
    selectedArtifactId = updated.id;
    renderWorkspace();
    toast('Artifact gespeichert');
  });
  $('#deleteArtifactBtn')?.addEventListener('click', async () => {
    const artifact = selectedArtifact();
    if (!artifact || !confirm('Artifact wirklich löschen?')) return;
    await api('/api/artifacts/' + artifact.id, { method: 'DELETE' });
    currentArtifacts = currentArtifacts.filter(a => a.id !== artifact.id);
    selectedArtifactId = currentArtifacts[0]?.id || '';
    renderWorkspace();
    toast('Artifact gelöscht');
  });
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

function addMsg(role, content, meta = {}, contentHtml = '', messageId = null, extras = {}) {
  const row = document.createElement('div');
  row.className = `msg ${role}`;
  const avatar = role === 'assistant' ? '<div class="avatar h">H</div>' : '<div class="avatar u">Du</div>';
  const html = role === 'assistant' ? (contentHtml || plainTextToHtml(content)) : plainTextToHtml(content);
  const parsedMeta = parseMeta(meta);
  const generatedImage = role === 'assistant' ? generatedImageMarkup(parsedMeta) : '';
  const artifacts = extras.artifacts || [];
  const answerMetadata = extras.answer_metadata || null;
  const smartActions = role === 'assistant' && !generatedImage
    ? Object.entries(actionLabels).map(([key, action]) => `<button class="action-icon smart-action" type="button" data-action="${key}" title="${esc(action.label)}" aria-label="${esc(action.label)}">${icons[action.icon]}</button>`).join('')
    : '';
  const trustActions = role === 'assistant'
    ? `
      ${artifacts.length ? `<button class="action-icon artifact-open" type="button" title="Artifact öffnen" aria-label="Artifact öffnen">${icons.folder}</button>` : ''}
      <button class="action-icon sources-open" type="button" data-panel="sources" title="Quellen" aria-label="Quellen">${icons.file}</button>
      <button class="action-icon work-open" type="button" data-panel="sources" title="Arbeitsnachweis" aria-label="Arbeitsnachweis">${icons['shield-check']}</button>
      <button class="action-icon uncertainty-open" type="button" data-panel="sources" title="Unsicherheit" aria-label="Unsicherheit">${icons['help-circle']}</button>
      <button class="action-icon context-open" type="button" data-panel="sources" title="Kontext" aria-label="Kontext">${icons.brain}</button>`
    : '';
  row.innerHTML = `
    ${avatar}
    <div class="bubble">
      <div class="content">${html}</div>
      ${generatedImage}
      <div class="uploads">${uploadMarkup(parsedMeta)}</div>
      <div class="actions">
        <button class="action-icon copy-msg" type="button" title="Kopieren" aria-label="Kopieren">${icons.copy}</button>
        ${smartActions}
        ${role === 'assistant' ? `<button class="action-icon use-as-context" type="button" title="Weiterfragen" aria-label="Weiterfragen">${icons['message-circle']}</button>` : ''}
        ${trustActions}
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
  if (role === 'assistant') {
    const answerState = {
      id: messageId,
      content,
      content_html: contentHtml,
      meta: parsedMeta,
      artifacts,
      answer_metadata: answerMetadata
    };
    row.querySelector('.artifact-open')?.addEventListener('click', () => {
      selectedAnswer = answerState;
      selectedMetadata = answerMetadata;
      mergeArtifacts(artifacts);
      if (artifacts[0]) selectedArtifactId = artifacts[0].id;
      setWorkspaceTab('files');
    });
    row.querySelectorAll('.sources-open,.work-open,.uncertainty-open,.context-open').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedAnswer = answerState;
        selectedMetadata = answerMetadata;
        mergeArtifacts(artifacts);
        setWorkspaceTab('sources');
      });
    });
    if (!selectedAnswer) {
      selectedAnswer = answerState;
      selectedMetadata = answerMetadata;
      mergeArtifacts(artifacts);
      renderWorkspace();
    }
  }
  scrollBottom();
}

function renderMessages(list) {
  messagesEl.innerHTML = '';
  selectedAnswer = null;
  selectedMetadata = null;
  collectArtifactsFromMessages(list || []);
  if (!list || !list.length) {
    renderEmpty();
    renderWorkspace();
    return;
  }
  list.forEach(m => addMsg(m.role, m.content, m.meta, m.content_html, m.id, m));
  renderWorkspace();
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


const onboardingSteps = [
  {
    selector: '[data-tour="chat"]',
    title: 'Chat: dein ruhiger Startpunkt',
    text: 'Stelle Fragen, hänge Dateien an und arbeite Schritt für Schritt weiter. Alles bleibt in deinem Konto wiederauffindbar.'
  },
  {
    selector: '[data-tour="memory"]',
    title: 'Memory: wichtige Dinge bleiben präsent',
    text: 'Lege dauerhafte Notizen, Präferenzen und Projektdetails ab, damit Holo Rick weniger raten muss und hilfreicher antwortet.'
  },
  {
    selector: '[data-tour="workspace"]',
    title: 'Workspace: Ergebnisse sauber ordnen',
    text: 'Hier findest du Antworten, Dateien, Quellen, Tasks und Artefakte getrennt vom Chat – professioneller Kontext statt Fenster-Chaos.'
  }
];

function clearOnboardingFocus() {
  const spotlight = $('#onboardingSpotlight');
  if (spotlight) spotlight.classList.add('hidden');
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function placeOnboardingSpotlight(target) {
  const spotlight = $('#onboardingSpotlight');
  if (!spotlight || !target) return null;
  const rect = target.getBoundingClientRect();
  const pad = 8;
  const box = {
    left: clamp(rect.left - pad, 10, window.innerWidth - 20),
    top: clamp(rect.top - pad, 10, window.innerHeight - 20),
    width: Math.min(rect.width + pad * 2, window.innerWidth - 20),
    height: Math.min(rect.height + pad * 2, window.innerHeight - 20)
  };
  spotlight.style.left = `${box.left}px`;
  spotlight.style.top = `${box.top}px`;
  spotlight.style.width = `${box.width}px`;
  spotlight.style.height = `${box.height}px`;
  spotlight.classList.remove('hidden');
  return box;
}

function positionOnboardingCard(target) {
  const card = $('#onboardingCard');
  if (!card || !target) return;
  const box = placeOnboardingSpotlight(target) || target.getBoundingClientRect();
  const cardRect = card.getBoundingClientRect();
  const gap = 18;
  const margin = 16;
  const spaces = {
    right: window.innerWidth - (box.left + box.width),
    left: box.left,
    bottom: window.innerHeight - (box.top + box.height),
    top: box.top
  };
  let left;
  let top;
  if (spaces.top >= cardRect.height + gap) {
    left = box.left + box.width / 2 - cardRect.width / 2;
    top = box.top - cardRect.height - gap;
  } else if (spaces.bottom >= cardRect.height + gap) {
    left = box.left + box.width / 2 - cardRect.width / 2;
    top = box.top + box.height + gap;
  } else if (spaces.right >= cardRect.width + gap) {
    left = box.left + box.width + gap;
    top = box.top + box.height / 2 - cardRect.height / 2;
  } else if (spaces.left >= cardRect.width + gap) {
    left = box.left - cardRect.width - gap;
    top = box.top + box.height / 2 - cardRect.height / 2;
  } else {
    left = window.innerWidth - cardRect.width - margin;
    top = margin;
  }
  card.style.left = `${clamp(left, margin, window.innerWidth - cardRect.width - margin)}px`;
  card.style.top = `${clamp(top, margin, window.innerHeight - cardRect.height - margin)}px`;
}

function renderOnboardingStep() {
  const layer = $('#onboardingLayer');
  if (!layer) return;
  const step = onboardingSteps[onboardingStepIndex];
  const target = document.querySelector(step.selector);
  clearOnboardingFocus();
  if (target) {
    target.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
  }
  $('#onboardingTitle').textContent = step.title;
  $('#onboardingText').textContent = step.text;
  $('#onboardingProgress').innerHTML = onboardingSteps.map((_, i) => `<span class="${i <= onboardingStepIndex ? 'active' : ''}"></span>`).join('');
  $('#onboardingNextBtn').textContent = onboardingStepIndex === onboardingSteps.length - 1 ? 'Abschließen' : 'Weiter';
  setTimeout(() => positionOnboardingCard(target || document.body), 120);
}

function startOnboarding() {
  if (!me.authenticated || !me.needs_onboarding) return;
  onboardingStepIndex = 0;
  workspaceCollapsed = false;
  workspaceOpen = true;
  updateWorkspaceShell();
  $('#onboardingLayer')?.classList.remove('hidden');
  renderOnboardingStep();
}

async function finishOnboarding(dismissed = false) {
  $('#onboardingLayer')?.classList.add('hidden');
  clearOnboardingFocus();
  me.needs_onboarding = false;
  try {
    await api('/api/onboarding/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dismissed })
    });
  } catch (e) {
    showError(e, 'Onboarding konnte nicht gespeichert werden');
  }
}

function nextOnboardingStep() {
  if (onboardingStepIndex >= onboardingSteps.length - 1) {
    finishOnboarding(false);
    return;
  }
  onboardingStepIndex += 1;
  renderOnboardingStep();
}

async function loadProjects() {
  if (!me.authenticated) { projects = []; return; }
  projects = await api('/api/projects');
}

function renderProjectsView() {
  showProjectsSurface();
  const rows = projects.map(p => `
    <div class="project-row" data-id="${p.id}">
      <button class="project-open" type="button">
        <span class="project-icon">${icons.folder}</span>
        <span><strong>${esc(p.name)}</strong><small>${esc(p.description || 'Keine Beschreibung')}</small></span>
        <em>${new Date(p.updated_at).toLocaleDateString('de-DE')}</em>
      </button>
      <button class="project-delete" type="button" title="Projekt löschen">${icons['trash-2'] || icons.trash}</button>
    </div>`).join('');
  $('#projectsView').innerHTML = `
    <div class="projects-shell">
      <div class="projects-head"><div><h1>Projekte</h1><p>Chats, Dateien und verdichtete Erinnerung bleiben pro Projekt zusammen – viel Kontext, wenig Tokens.</p></div><div class="project-tools"><input class="input" id="projectSearch" placeholder="Projekte suchen"><button class="primary" id="newProjectBtn" type="button">Neu</button></div></div>
      <div class="project-tabs"><button class="active">Alle</button><button>Von dir erstellt</button></div>
      <div class="project-table"><div class="project-table-head"><span>Name</span><span>Geändert</span></div>${rows || '<div class="empty-list">Noch keine Projekte.</div>'}</div>
    </div>`;
  $('#newProjectBtn').onclick = () => openProjectModal();
  $('#projectSearch').oninput = e => { const q=e.target.value.toLowerCase(); document.querySelectorAll('.project-row').forEach(r => r.classList.toggle('hidden', !r.textContent.toLowerCase().includes(q))); };
  document.querySelectorAll('.project-row').forEach(r => {
    r.querySelector('.project-open').onclick = () => openProject(Number(r.dataset.id));
    r.querySelector('.project-delete').onclick = async e => {
      e.stopPropagation();
      const name = r.querySelector('strong')?.textContent || 'dieses Projekt';
      if (!confirm(`Projekt „${name}“ inklusive aller Chats wirklich löschen?`)) return;
      await api('/api/projects/' + r.dataset.id, { method: 'DELETE' });
      toast('Projekt gelöscht');
      await showProjects();
    };
  });
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
  currentProjectMemory = d.memory || [];
  memoryItems = currentProjectMemory;
  showChatSurface();
  setActiveNav('projectsBtn');
  messagesEl.innerHTML = `<div class="project-home"><div class="project-title">${icons.folder}<h1>${esc(d.project.name)}</h1><button class="ghost" id="editProjectBtn" type="button">Kontext</button></div><div class="composer-preview" id="projectNewChat">+ Neuer Chat in ${esc(d.project.name)}</div><div class="project-tabs"><button class="active" id="projectChatsTab" type="button">Chats</button><button id="projectMemoryTab" type="button">Memory</button><button id="projectSourcesTab" type="button">Quellen</button></div><div class="project-chat-list">${d.chats.map(c => `<button class="project-chat-row" data-id="${c.id}"><span><strong>${esc(c.title)}</strong><small>Projektchat</small></span><em>${new Date(c.updated_at).toLocaleDateString('de-DE')}</em></button>`).join('') || '<div class="empty-list">Noch keine Chats im Projekt.</div>'}</div></div>`;
  $('#editProjectBtn').onclick = () => openProjectModal(d.project);
  $('#projectNewChat').onclick = newChat;
  $('#projectMemoryTab').onclick = () => renderMemoryView({ embedded: true, project: d.project });
  $('#projectSourcesTab').onclick = () => {
    selectedMetadata = null;
    setWorkspaceTab('sources');
  };
  document.querySelectorAll('.project-chat-row').forEach(r => r.onclick = () => loadChat(Number(r.dataset.id)));
}

function memoryDate(value) {
  return value ? new Date(value).toLocaleString('de-DE') : 'nie';
}

function filteredMemoryItems() {
  const q = memoryFilters.q.toLowerCase();
  return (memoryItems || []).filter(item => {
    if (!memoryFilters.archived && item.is_archived) return false;
    if (memoryFilters.scope !== 'all' && item.scope !== memoryFilters.scope) return false;
    const haystack = [item.title, item.content, item.source, (item.tags || []).join(' ')].join(' ').toLowerCase();
    return !q || haystack.includes(q);
  });
}

function renderMemoryView(options = {}) {
  showProjectsSurface();
  setActiveNav('memoryBtn');
  const project = options.project || currentProject;
  const defaultScope = project?.id ? 'project' : currentChatId ? 'chat' : 'global';
  const rows = filteredMemoryItems().map(item => `
    <div class="memory-row ${item.is_pinned ? 'pinned' : ''} ${item.is_archived ? 'archived' : ''}" data-id="${esc(item.id)}">
      <div>
        <strong>${esc(item.title)}</strong>
        <p>${esc(item.content)}</p>
        <div class="memory-meta">
          <span>${esc(item.scope)}</span>
          <span>erstellt ${memoryDate(item.created_at)}</span>
          <span>aktualisiert ${memoryDate(item.updated_at)}</span>
          ${item.source ? `<span>Quelle: ${esc(item.source)}</span>` : ''}
          ${item.confidence ? `<span>Confidence: ${esc(item.confidence)}</span>` : ''}
        </div>
        <div class="memory-tags">${(item.tags || []).map(tag => `<span>${esc(tag)}</span>`).join('')}</div>
      </div>
      <div class="memory-actions">
        <button class="mini-btn edit-memory" type="button" title="Bearbeiten">${icons['edit-3']}</button>
        <button class="mini-btn pin-memory" type="button" title="Pinnen">${item.is_pinned ? '★' : '☆'}</button>
        <button class="mini-btn archive-memory" type="button" title="Archivieren">${icons.archive}</button>
        <button class="mini-btn delete-memory" type="button" title="Löschen">${icons['trash-2']}</button>
      </div>
    </div>`).join('');
  $('#projectsView').innerHTML = `
    <div class="projects-shell memory-shell">
      <div class="projects-head">
        <div><h1>Memory</h1><p>Sichtbar, editierbar, löschbar. Keine magische Datenbank im Schatten.</p></div>
        <div class="project-tools"><input class="input" id="memorySearch" placeholder="Memory suchen"><button class="primary" id="newMemoryBtn" type="button">Neu</button></div>
      </div>
      <div class="memory-filters">
        <button class="${memoryFilters.scope === 'all' ? 'active' : ''}" data-scope="all">Alle</button>
        <button class="${memoryFilters.scope === 'global' ? 'active' : ''}" data-scope="global">Global</button>
        <button class="${memoryFilters.scope === 'project' ? 'active' : ''}" data-scope="project">Projekt</button>
        <button class="${memoryFilters.scope === 'chat' ? 'active' : ''}" data-scope="chat">Chat</button>
        <label class="check small-check"><input type="checkbox" id="memoryArchived" ${memoryFilters.archived ? 'checked' : ''}><span>Archiv zeigen</span></label>
      </div>
      <div class="memory-editor hidden" id="memoryEditor">
        <div class="grid-2">
          <div><label>Titel</label><input class="input" id="memoryTitle"></div>
          <div><label>Scope</label><select class="input" id="memoryScope"><option value="global">global</option><option value="project">project</option><option value="chat">chat</option></select></div>
          <div><label>Tags</label><input class="input" id="memoryTags" placeholder="komma, getrennt"></div>
          <div><label>Confidence</label><select class="input" id="memoryConfidence"><option value="">nicht gesetzt</option><option value="low">low</option><option value="medium">medium</option><option value="high">high</option></select></div>
        </div>
        <label>Quelle</label><input class="input" id="memorySource" placeholder="manuell, Datei, Chat...">
        <label>Inhalt</label><textarea class="textarea context-area" id="memoryContent"></textarea>
        <div class="context-actions"><button class="ghost" id="cancelMemoryBtn" type="button">Abbrechen</button><button class="primary" id="saveMemoryBtn" type="button">Memory speichern</button></div>
      </div>
      <div class="memory-list">${rows || '<div class="empty-list">Noch kein Memory. Du entscheidest, was gespeichert wird.</div>'}</div>
    </div>`;
  $('#memorySearch').value = memoryFilters.q;
  $('#memorySearch').oninput = e => { memoryFilters.q = e.target.value; renderMemoryView({ project }); };
  $('#memoryArchived').onchange = e => { memoryFilters.archived = e.target.checked; renderMemoryView({ project }); };
  document.querySelectorAll('.memory-filters button').forEach(btn => btn.onclick = () => { memoryFilters.scope = btn.dataset.scope || 'all'; renderMemoryView({ project }); });
  $('#newMemoryBtn').onclick = () => openMemoryEditor({ scope: defaultScope, project_id: project?.id || null, chat_id: currentChatId || null });
  $('#cancelMemoryBtn').onclick = () => $('#memoryEditor').classList.add('hidden');
  $('#saveMemoryBtn').onclick = () => saveMemoryItem().catch(e => showError(e, 'Memory konnte nicht gespeichert werden'));
  document.querySelectorAll('.memory-row').forEach(row => {
    const item = memoryItems.find(x => x.id === row.dataset.id);
    row.querySelector('.edit-memory').onclick = () => openMemoryEditor(item);
    row.querySelector('.pin-memory').onclick = () => patchMemoryItem(item.id, { is_pinned: !item.is_pinned });
    row.querySelector('.archive-memory').onclick = () => patchMemoryItem(item.id, { is_archived: !item.is_archived });
    row.querySelector('.delete-memory').onclick = () => deleteMemoryItem(item.id);
  });
  injectIcons($('#projectsView'));
}

function openMemoryEditor(item = {}) {
  editingMemoryId = item.id || '';
  $('#memoryEditor').classList.remove('hidden');
  $('#memoryTitle').value = item.title || '';
  $('#memoryScope').value = item.scope || (currentProjectId ? 'project' : currentChatId ? 'chat' : 'global');
  $('#memoryTags').value = Array.isArray(item.tags) ? item.tags.join(', ') : '';
  $('#memoryConfidence').value = item.confidence || '';
  $('#memorySource').value = item.source || 'manuell';
  $('#memoryContent').value = item.content || '';
  $('#memoryTitle').focus();
}

function upsertMemoryLocal(item) {
  const idx = memoryItems.findIndex(x => x.id === item.id);
  if (idx >= 0) memoryItems[idx] = item;
  else memoryItems.unshift(item);
  currentProjectMemory = memoryItems;
}

async function saveMemoryItem() {
  const scope = $('#memoryScope').value;
  const body = {
    title: $('#memoryTitle').value || 'Memory',
    scope,
    content: $('#memoryContent').value,
    tags: $('#memoryTags').value.split(',').map(x => x.trim()).filter(Boolean),
    confidence: $('#memoryConfidence').value || null,
    source: $('#memorySource').value || 'manuell',
    project_id: scope === 'project' ? currentProjectId || currentProject?.id : null,
    chat_id: scope === 'chat' ? currentChatId : null
  };
  const item = editingMemoryId
    ? await api('/api/memory/' + editingMemoryId, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    : await api('/api/memory', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  upsertMemoryLocal(item);
  editingMemoryId = '';
  renderMemoryView({ project: currentProject });
  toast('Memory gespeichert');
}

async function patchMemoryItem(id, patch) {
  const existing = memoryItems.find(x => x.id === id);
  if (!existing) return;
  const updated = await api('/api/memory/' + id, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...existing, ...patch })
  });
  upsertMemoryLocal(updated);
  renderMemoryView({ project: currentProject });
}

async function deleteMemoryItem(id) {
  if (!confirm('Memory-Eintrag endgültig löschen?')) return;
  await api('/api/memory/' + id, { method: 'DELETE' });
  memoryItems = memoryItems.filter(x => x.id !== id);
  currentProjectMemory = memoryItems;
  renderMemoryView({ project: currentProject });
  toast('Memory gelöscht');
}

async function showMemory() {
  if (!me.authenticated) { setAuthMode('login'); $('#loginModal').classList.remove('hidden'); return; }
  if (currentProject?.id && currentProjectMemory.length) {
    memoryItems = currentProjectMemory;
  } else {
    const qs = new URLSearchParams({ archived: 'all' });
    if (currentProjectId) qs.set('project_id', currentProjectId);
    if (currentChatId) qs.set('chat_id', currentChatId);
    memoryItems = await api('/api/memory?' + qs.toString());
    currentProjectMemory = memoryItems;
  }
  renderMemoryView({ project: currentProject });
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
        <button class="mini-btn rename-chat" type="button" title="Umbenennen">${icons['edit-3']}</button>
        <button class="mini-btn archive-chat" type="button" title="${archivedView ? 'Wiederherstellen' : 'Archivieren'}">${icons.archive}</button>
        <button class="mini-btn delete-chat" type="button" title="Löschen">${icons['trash-2']}</button>
      </div>`;
    item.querySelector('.chat-open').onclick = () => loadChat(c.id);
    item.querySelector('.rename-chat').onclick = async e => {
      e.stopPropagation();
      const title = prompt('Chat umbenennen', c.title);
      if (title === null) return;
      const trimmed = title.trim();
      if (!trimmed || trimmed === c.title) return;
      await api('/api/chats/' + c.id, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: trimmed }) });
      await loadChats();
      toast('Chat umbenannt');
    };
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
  currentShareToken = '';
  currentSharedChat = false;
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
  currentShareToken = '';
  currentSharedChat = false;
  currentChatHasContext = false;
  currentArtifacts = [];
  selectedArtifactId = '';
  selectedAnswer = null;
  selectedMetadata = null;
  updateContextIndicator();
  renderEmpty();
  renderWorkspace();
  renderChats();
  closeSidebar();
  input.focus();
}

function thinkingMarkup() {
  return `
    <div class="thinking-state" aria-label="Holo Rick denkt">
      <span class="thinking-orb" aria-hidden="true"></span>
      <span>${aiMode === 'deep' ? 'Analysiere gründlich...' : 'Denke nach...'}</span>
    </div>`;
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
  if (currentShareToken) fd.append('share_token', currentShareToken);
  fd.append('ai_mode', aiMode);
  fd.append('response_format', responseFormat);
  selectedFiles.forEach(f => fd.append('files', f));
  selectedFiles = [];

  const wait = document.createElement('div');
  wait.className = 'msg assistant';
  wait.innerHTML = `<div class="avatar h">H</div><div class="bubble"><div class="content typing">${thinkingMarkup()}</div></div>`;
  messagesEl.appendChild(wait);
  scrollBottom();

  try {
    const d = await api('/api/send', { method: 'POST', body: fd });
    wait.remove();
    addMsg('assistant', d.assistant_message.content, d.assistant_message.meta || {}, d.assistant_message.content_html, d.assistant_message.id, d.assistant_message);
    selectedAnswer = {
      id: d.assistant_message.id,
      content: d.assistant_message.content,
      content_html: d.assistant_message.content_html,
      meta: parseMeta(d.assistant_message.meta),
      artifacts: d.assistant_message.artifacts || [],
      answer_metadata: d.assistant_message.answer_metadata || null
    };
    selectedMetadata = d.assistant_message.answer_metadata || null;
    mergeArtifacts(d.assistant_message.artifacts || []);
    renderWorkspace();
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
    addMsg('assistant', d.assistant_message.content, d.assistant_message.meta || {}, d.assistant_message.content_html, d.assistant_message.id, d.assistant_message);
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
  ['homeBtn', 'searchBtn', 'projectsBtn', 'memoryBtn', 'archiveBtn'].forEach(navId => {
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
    startOnboarding();
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

async function createShareLink() {
  if (!me.authenticated) {
    setAuthMode('login');
    $('#loginModal').classList.remove('hidden');
    return;
  }
  if (!currentChatId) {
    toast('Erst einen Chat starten, dann teilen.');
    return;
  }
  const d = await api('/api/chats/' + currentChatId + '/share', { method: 'POST' });
  $('#shareLinkInput').value = d.url;
  try {
    await navigator.clipboard.writeText(d.url);
    toast('Teillink kopiert');
  } catch {
    toast('Teillink erstellt');
  }
}

async function openSharedChatFromUrl() {
  const match = location.pathname.match(/^\/share\/([^/]+)$/);
  if (!match) return false;
  currentShareToken = decodeURIComponent(match[1]);
  currentSharedChat = true;
  showChatSurface();
  const d = await api('/api/shared/' + encodeURIComponent(currentShareToken));
  currentChatId = d.chat.chat_id;
  currentProjectId = d.chat.project_id || 0;
  currentChatHasContext = !!(d.chat.project_context || currentProjectId);
  updateContextIndicator();
  renderMessages(d.messages);
  closeSidebar();
  return true;
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
  $('#sectionNewChatBtn')?.addEventListener('click', newChat);
  $('#projectsBtn').onclick = () => showProjects().catch(e => showError(e, 'Projekte nicht verfügbar'));
  $('#memoryBtn').onclick = () => showMemory().catch(e => showError(e, 'Memory nicht verfügbar'));
  $('#searchBtn').onclick = () => { setActiveNav('searchBtn'); $('#chatSearch').focus(); };
  $('#openWorkspaceBtn')?.addEventListener('click', () => {
    workspaceOpen = true;
    workspaceCollapsed = false;
    localStorage.setItem('holo_rick_workspace_collapsed', 'false');
    renderWorkspace();
  });
  $('#closeWorkspaceBtn')?.addEventListener('click', () => {
    workspaceOpen = false;
    updateWorkspaceShell();
  });
  $('#collapseWorkspaceBtn')?.addEventListener('click', () => {
    workspaceCollapsed = !workspaceCollapsed;
    localStorage.setItem('holo_rick_workspace_collapsed', String(workspaceCollapsed));
    renderWorkspace();
  });
  $('#workspaceTabs')?.querySelectorAll('button').forEach(tab => {
    tab.onclick = () => setWorkspaceTab(tab.dataset.tab || 'answer', false);
  });
  $('#closeProjectBtn')?.addEventListener('click', () => $('#projectModal')?.classList.add('hidden'));
  $('#closeShareBtn')?.addEventListener('click', () => $('#shareModal')?.classList.add('hidden'));
  $('#createShareBtn')?.addEventListener('click', () => createShareLink().catch(e => showError(e, 'Teillink konnte nicht erstellt werden')));
  $('#copyShareBtn')?.addEventListener('click', () => {
    const link = $('#shareLinkInput').value;
    if (!link) return createShareLink().catch(e => showError(e, 'Teillink konnte nicht erstellt werden'));
    navigator.clipboard.writeText(link).then(() => toast('Teillink kopiert'));
  });
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
  backdrop.onclick = () => {
    closeSidebar();
    workspaceOpen = false;
    updateWorkspaceShell();
  };
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
  $('.share-btn').onclick = () => {
    $('#shareModal').classList.remove('hidden');
    if (currentShareToken) $('#shareLinkInput').value = location.href;
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
  $('#onboardingNextBtn').onclick = nextOnboardingStep;
  $('#onboardingSkipBtn').onclick = () => finishOnboarding(true);
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
      $('#onboardingLayer')?.classList.add('hidden');
      clearOnboardingFocus();
      workspaceOpen = false;
      updateWorkspaceShell();
      closeSidebar();
    }
  });
}

async function boot() {
  injectIcons();
  bindEvents();
  updateModeUi();
  updateContextIndicator();
  renderWorkspace();
  renderEmpty();
  await refreshMe();
  if (await openSharedChatFromUrl()) {
    input.focus();
    return;
  }
  if (me.authenticated) {
    if (me.role === 'admin') await loadSettings();
    await loadChats();
    startOnboarding();
  }
  input.focus();
}

boot().catch(e => toast(e.error || String(e)));
