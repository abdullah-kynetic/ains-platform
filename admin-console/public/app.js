'use strict';

// Entirely fictional demo records. No backend, requests, or credentials are used.
const firms = [
  { id: 'harbor', name: 'Harbor & Pine Advisory', plan: 'Enterprise', status: 'Active', users: 24, seats: 30, engagements: 7, storage: 18.4, activity: 'Today, 10:42 AM' },
  { id: 'cedar', name: 'Cedar Vale Securities', plan: 'Professional', status: 'Active', users: 12, seats: 15, engagements: 4, storage: 8.2, activity: 'Today, 9:18 AM' },
  { id: 'northline', name: 'Northline Capital Partners', plan: 'Enterprise', status: 'Active', users: 38, seats: 50, engagements: 11, storage: 32.7, activity: 'Today, 8:56 AM' },
  { id: 'willow', name: 'Willow Creek Financial', plan: 'Starter', status: 'Trial', users: 4, seats: 5, engagements: 1, storage: 1.1, activity: 'Yesterday, 4:30 PM' },
  { id: 'stonebridge', name: 'Stonebridge Market Group', plan: 'Professional', status: 'Active', users: 9, seats: 15, engagements: 3, storage: 6.8, activity: 'Yesterday, 2:15 PM' },
  { id: 'juniper', name: 'Juniper Ridge Advisors', plan: 'Starter', status: 'Suspended', users: 3, seats: 5, engagements: 0, storage: 2.3, activity: 'Oct 18, 2026' },
  { id: 'bayshore', name: 'Bayshore Meridian Partners', plan: 'Professional', status: 'Trial', users: 6, seats: 15, engagements: 2, storage: 3.6, activity: 'Oct 23, 2026' },
  { id: 'elmstead', name: 'Elmstead Brokerage Group', plan: 'Enterprise', status: 'Active', users: 21, seats: 30, engagements: 6, storage: 15.9, activity: 'Today, 11:05 AM' },
];
const fictionalNames = ['Avery Linden', 'Morgan Finch', 'Casey Rowan', 'Jordan Vale', 'Taylor Reed', 'Riley Ash', 'Cameron Brooks', 'Parker Lane', 'Drew Hollis', 'Skyler Quinn', 'Alex Wren', 'Sage Ellis', 'Robin Hart', 'Jamie Moss', 'Reese Alder', 'Emerson Clay', 'Blair Field', 'Hayden Lake', 'Finley Stone', 'Kendall Birch', 'Dakota Wynn', 'Ellery Frost', 'Arden West', 'Quinn Dale'];
const users = firms.flatMap((firm, fi) => Array.from({ length: firm.users }, (_, i) => ({
  id: `${firm.id}-${i}`, firmId: firm.id,
  name: `${fictionalNames[(fi * 3 + i) % fictionalNames.length]}${i >= 24 ? ' Jr.' : ''}`,
  email: `member${i + 1}@${firm.id}.example.com`,
  role: i === 0 ? 'Owner' : i % 3 === 1 ? 'Auditor' : 'Client',
  mfa: i % 5 !== 2,
  lastSignIn: firm.status === 'Suspended' ? 'Oct 18, 2026' : i % 3 === 0 ? 'Today, 9:12 AM' : i % 3 === 1 ? 'Oct 23, 2026' : 'Oct 22, 2026',
})));
const events = [
  ['Oct 24, 2026 · 11:05', 'Platform administrator', 'License seats updated', 'Elmstead Brokerage Group'],
  ['Oct 24, 2026 · 10:42', 'Avery Linden', 'Firm member invited', 'Harbor & Pine Advisory'],
  ['Oct 24, 2026 · 09:18', 'Jordan Vale', 'Multi-factor authentication enabled', 'Cedar Vale Securities'],
  ['Oct 23, 2026 · 16:30', 'Platform administrator', 'Trial workspace provisioned', 'Willow Creek Financial'],
  ['Oct 23, 2026 · 14:15', 'Platform administrator', 'Plan changed to Professional', 'Stonebridge Market Group'],
  ['Oct 22, 2026 · 11:40', 'Platform administrator', 'Trial workspace provisioned', 'Bayshore Meridian Partners'],
  ['Oct 18, 2026 · 08:20', 'Platform administrator', 'Workspace suspended', 'Juniper Ridge Advisors'],
];
const app = document.querySelector('#app');
let mfaStep = false;
let email = '';
let toastTimer;
let menuOpen = false;
let signedIn = readStorage(sessionStorage, 'kien-demo-session') === 'active';
function readStorage(storage, key) { try { return storage.getItem(key); } catch { return null; } }
function saveStorage(storage, key, value) { try { if (value === null) storage.removeItem(key); else storage.setItem(key, value); } catch { /* Preview still works without browser persistence. */ } }
const savedTheme = readStorage(localStorage, 'kien-demo-theme');
if (['light', 'dark'].includes(savedTheme)) document.documentElement.dataset.theme = savedTheme;
function isDark() { return document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; }
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]); }
function themeButton() { return `<button class="button" data-action="theme" aria-label="Switch to ${isDark() ? 'light' : 'dark'} theme">${isDark() ? 'Light' : 'Dark'} theme</button>`; }
function brand() { return '<a class="brand" href="#overview"><img src="./favicon.svg" alt=""><span><strong>Kien Solutions</strong><small>Platform administration</small></span></a>'; }
function badge(status) { return `<span class="badge ${status.toLowerCase()}">${status}</span>`; }
function toast() { const target = document.querySelector('#toast'); target.textContent = 'Demo only, nothing was changed'; clearTimeout(toastTimer); toastTimer = setTimeout(() => { target.textContent = ''; }, 4500); }
function login() {
  app.innerHTML = `<div class="login-layout"><section class="login-story">${brand()}<div><div class="story-mark" aria-hidden="true">↗</div><p class="eyebrow">Kien Admin</p><h1>A clear view.<br>Room to grow.</h1><p>A considered workspace for the people behind your platform.</p></div><small class="small">Kien Solutions · Platform owner preview</small></section><section class="login-area"><div class="login-tools">${themeButton()}</div><main id="main" class="login-form"><p class="eyebrow">Platform owner access</p><h1>${mfaStep ? 'One more step.' : 'Welcome back.'}</h1><p class="subtitle">${mfaStep ? 'Enter your demo verification code to continue.' : 'Sign in to your Kien Admin workspace.'}</p><div class="notice">${mfaStep ? 'Synthetic demo only. Use code 123456.' : 'Mock sign-in. Use any non-empty email and password. Do not enter a real password.'}</div><form id="login-form">${mfaStep ? '<label for="code">Verification code</label><input id="code" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="123456" required aria-describedby="login-error">' : '<label for="email">Email address</label><input id="email" name="email" type="text" inputmode="email" autocomplete="off" placeholder="admin@kiensolutions.com" required><label for="password">Demo password</label><input id="password" name="password" type="password" autocomplete="off" placeholder="Any non-empty demo password" required>'}<p id="login-error" class="error" role="alert"></p><button class="button primary" type="submit">${mfaStep ? 'Verify & enter workspace' : 'Continue'}</button></form>${mfaStep ? '<button class="button section" data-action="back-login">Back to sign in</button>' : ''}<p class="footnote">Fictional records. No real authentication.</p></main></section></div>`;
  document.querySelector('#login-form').addEventListener('submit', event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!mfaStep) {
      if (!String(form.get('email')).trim() || !String(form.get('password')).trim()) { document.querySelector('#login-error').textContent = 'Enter a non-empty email and demo password.'; return; }
      email = String(form.get('email')).trim(); mfaStep = true; login(); document.querySelector('#code').focus();
    } else if (form.get('code') !== '123456') document.querySelector('#login-error').textContent = 'Use the synthetic demo code 123456.';
    else { signedIn = true; saveStorage(sessionStorage, 'kien-demo-session', 'active'); mfaStep = false; render(true); }
  });
}
const navigation = [['overview', '◫', 'Overview'], ['firms', '▦', 'Firms'], ['users', '♙', 'Users'], ['audit-log', '≡', 'Audit log'], ['settings', '⚙', 'Settings']];
function pageHeading(title, description) { return `<p class="eyebrow">Kien Admin / Platform</p><div class="heading-row"><div><h1>${title}</h1><p class="subtitle">${description}</p></div><span class="date-label">October 24, 2026 · Demo snapshot</span></div>`; }
function firmRows(list) { return list.map(f => `<tr class="firm-row" data-firm="${f.id}"><td><a class="firm-link" href="#firms/${f.id}">${f.name}</a><small>${f.id}.kiensolutions.com</small></td><td>${f.plan}</td><td>${badge(f.status)}</td><td>${f.users}</td><td>${f.seats}</td><td>${f.engagements}</td><td>${f.storage} GB</td><td>${f.activity}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">No fictional firms match these filters.</td></tr>'; }
function firmTable(list) { return `<div class="card table-card"><div class="table-scroll"><table><caption class="sr-only" hidden>Fictional firms and workspace usage</caption><thead><tr>${['Firm / subdomain', 'Plan', 'Status', 'Users', 'Seats', 'Engagements', 'Storage used', 'Last activity'].map(t => `<th scope="col">${t}</th>`).join('')}</tr></thead><tbody id="firm-rows">${firmRows(list)}</tbody></table></div></div>`; }
function overview() {
  const licensed = firms.filter(f => f.status === 'Active').length;
  return `${pageHeading('Your platform, at a glance.', 'A little perspective on the work moving through your platform.')}<div class="kpis">${[[licensed, 'Licensed firms', `${firms.length} total workspaces · ${firms.filter(f => f.status === 'Trial').length} trials`], [users.filter(u => firms.find(f => f.id === u.firmId).status !== 'Suspended').length, 'Active users', 'Across active and trial firms'], ['2,486', 'Documents processed this month', '<span>↑ 12.8%</span> vs. September · synthetic'], [firms.reduce((sum, f) => sum + f.engagements, 0), 'Open engagements', 'Across all fictional firms']].map(([value, label, note]) => `<div class="card"><div class="kpi-label">${label}</div><div class="kpi-value">${value}</div><div class="kpi-note">${note}</div></div>`).join('')}</div><div class="grid-two"><section class="card"><div class="card-header"><h2>Steady momentum</h2><span class="small"><span class="dot"></span>Documents processed</span></div><svg class="chart" viewBox="0 0 600 250" role="img" aria-labelledby="chart-title chart-desc"><title id="chart-title">Monthly document usage, May to October 2026</title><desc id="chart-desc">Synthetic counts: May 1,100; June 1,450; July 1,320; August 1,870; September 2,204; October 2,486.</desc>${[0, 1, 2, 3].map(i => `<line x1="45" y1="${20 + i * 60}" x2="580" y2="${20 + i * 60}"/><text x="0" y="${24 + i * 60}">${3000 - i * 1000}</text>`).join('')}${[1100, 1450, 1320, 1870, 2204, 2486].map((v, i) => `<rect x="${68 + i * 86}" y="${200 - v * .06}" width="38" height="${v * .06}" rx="4" fill="currentColor" opacity="${i === 5 ? 1 : .6}"/><text x="${87 + i * 86}" y="228" text-anchor="middle">${['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'][i]}</text>`).join('')}</svg><p class="small">Monthly usage · May–October 2026 · fictional values</p></section><section class="card"><div class="card-header"><h2>Recent activity</h2><a class="small" href="#audit-log">View log →</a></div><ul class="activity">${events.slice(0, 4).map(e => `<li><strong>${e[2]}</strong><small>${e[3]}<br>${e[0]}</small></li>`).join('')}</ul></section></div><section class="section"><div class="card-header"><h2>Firm directory</h2><a class="small" href="#firms">View all firms →</a></div>${firmTable(firms.slice(0, 4))}</section>`;
}
function firmsPage() { return `${pageHeading('Firms', 'A home for every firm on your platform. All records are fictional.')}<div class="filters"><div class="search-field"><label for="firm-search">Search firms</label><input id="firm-search" type="search" placeholder="Firm name or subdomain"></div><div><label for="status-filter">Status</label><select id="status-filter"><option value="">All statuses</option><option>Active</option><option>Trial</option><option>Suspended</option></select></div><span class="count" id="firm-count" role="status">${firms.length} fictional firms</span></div>${firmTable(firms)}`; }
function userRows(list) { return list.map(u => `<tr><td><strong>${u.name}</strong><small>${u.email}</small></td><td><a href="#firms/${u.firmId}">${firms.find(f => f.id === u.firmId).name}</a></td><td>${u.role}</td><td><span class="badge ${u.mfa ? 'active' : 'trial'}">${u.mfa ? 'On' : 'Off'}</span></td><td>${u.lastSignIn}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">No fictional users match your search.</td></tr>'; }
function userTable(list) { return `<div class="card table-card"><div class="table-scroll"><table aria-label="Fictional users"><thead><tr>${['User', 'Firm', 'Role', 'MFA', 'Last sign-in'].map(t => `<th scope="col">${t}</th>`).join('')}</tr></thead><tbody id="user-rows">${userRows(list)}</tbody></table></div></div>`; }
function detail(f) { return `<a href="#firms" class="back-link">← All firms</a>${pageHeading(f.name, `${f.id}.kiensolutions.com · Fictional workspace`)}${badge(f.status)} <span class="small">${f.plan} plan</span><div class="actions"><button class="button ${f.status === 'Suspended' ? '' : 'danger'}" data-action="status" data-id="${f.id}">${f.status === 'Suspended' ? 'Reactivate' : 'Suspend'}</button><button class="button" data-action="branding" data-id="${f.id}">Reset branding</button></div><p class="small">Actions simulate this preview only and reset when the page reloads. No service is connected.</p><div class="grid-two section"><section class="card"><h2>Workspace usage</h2><div class="usage-line"><span>Licensed seats</span><strong>${f.users} / ${f.seats}</strong></div><progress aria-label="Licensed seats used" value="${f.users}" max="${f.seats}"></progress><div class="usage-line"><span>Storage used</span><strong>${f.storage} / 100 GB</strong></div><progress aria-label="Storage used in gigabytes" value="${f.storage}" max="100"></progress><div class="usage-line"><span>Open engagements</span><strong>${f.engagements}</strong></div></section><section class="card"><h2>Workspace details</h2><dl class="settings-list section"><div><dt>Branding</dt><dd>${f.brandingReset ? 'Kien Solutions default (simulated)' : 'Custom firm identity (mock)'}</dd></div><div><dt>Last activity</dt><dd>${f.activity}</dd></div><div><dt>Data</dt><dd>Synthetic only</dd></div></dl></section></div><section class="section"><div class="card-header"><h2>Firm users</h2><span class="small">${f.users} fictional members</span></div>${userTable(users.filter(u => u.firmId === f.id))}</section>`; }
function usersPage() { return `${pageHeading('Users', 'The people in your fictional firm workspaces.')}<div class="filters"><div class="search-field"><label for="user-search">Search users</label><input id="user-search" type="search" placeholder="Name, email, firm, or role"></div><span class="count" id="user-count" role="status">${users.length} fictional users</span></div>${userTable(users)}`; }
function auditPage() { return `${pageHeading('Audit log', 'A mock history of platform administration events.')}<div class="card table-card"><div class="table-scroll"><table aria-label="Synthetic platform events"><thead><tr>${['Timestamp', 'Actor', 'Event', 'Firm'].map(t => `<th scope="col">${t}</th>`).join('')}</tr></thead><tbody>${events.map(e => `<tr>${e.map(v => `<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div><p class="footnote">Static synthetic history. Demo actions do not create real audit events.</p>`; }
function settingsPage() { return `${pageHeading('Settings', 'Your platform configuration, shown as a read-only mock.')}<div class="grid-two"><section class="card"><div class="card-header"><h2>Platform identity</h2><span class="badge">Read-only</span></div><dl class="settings-list">${[['Platform', 'Kien Solutions'], ['Workspace', 'Kien Admin'], ['Primary domain', 'kiensolutions.com (illustrative)'], ['Environment', 'Synthetic preview'], ['Default locale', 'English (United States)']].map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl></section><section class="card"><h2>Security & access</h2><dl class="settings-list section">${[['Owner MFA policy', 'Required (mock)'], ['Session', 'Current browser tab'], ['Authentication', 'Demo gate only'], ['Integrations', 'None connected'], ['Data persistence', 'Theme and demo session only']].map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl></section></div><p class="footnote">These values are illustrative. This preview has no backend and does not enforce production security policies.</p>`; }
function render(focus = false) {
  if (!signedIn) { document.title = 'Sign in · Kien Admin'; login(); return; }
  const route = location.hash.slice(1) || 'overview';
  const [view, id] = route.split('/');
  const f = view === 'firms' && id ? firms.find(item => item.id === id) : null;
  let content;
  if (view === 'firms' && id) content = f ? detail(f) : `${pageHeading('Firm not found', 'This fictional workspace does not exist.')}<a href="#firms">Return to firms</a>`;
  else content = ({ overview, firms: firmsPage, users: usersPage, 'audit-log': auditPage, settings: settingsPage }[route] || (() => `${pageHeading('Page not found', 'Choose a workspace view from the navigation.')}<a href="#overview">Return to overview</a>`))();
  document.title = `${f ? f.name : navigation.find(n => n[0] === view)?.[2] || 'Page not found'} · Kien Admin`;
  app.innerHTML = `<div class="shell ${menuOpen ? 'menu-open' : ''}"><aside class="sidebar" id="sidebar">${brand()}<nav aria-label="Main navigation">${navigation.map(([key, icon, label]) => `<a href="#${key}" ${view === key ? 'aria-current="page"' : ''}><span class="nav-icon" aria-hidden="true">${icon}</span>${label}</a>`).join('')}</nav><div class="sidebar-foot"><strong>Kien Admin</strong>Platform owner workspace<br>Fictional demo environment</div></aside><div class="workspace"><header class="topbar"><button class="button menu-button" data-action="menu" aria-controls="sidebar" aria-expanded="${menuOpen}">Menu</button><span class="topbar-label">Platform owner workspace</span><div class="tools">${themeButton()}<span class="avatar" aria-hidden="true">KS</span><button class="button" data-action="signout">Sign out</button></div></header><main id="main" tabindex="-1">${content}<footer class="footnote">Kien Solutions · All firms, people, and activity are fictional.</footer></main></div></div>`;
  if (focus) { document.querySelector('#main').focus(); window.scrollTo(0, 0); }
  document.querySelector('#firm-search')?.addEventListener('input', filterFirms);
  document.querySelector('#status-filter')?.addEventListener('change', filterFirms);
  document.querySelector('#user-search')?.addEventListener('input', event => {
    const query = event.target.value.trim().toLowerCase();
    const matches = users.filter(u => `${u.name} ${u.email} ${u.role} ${firms.find(firm => firm.id === u.firmId).name}`.toLowerCase().includes(query));
    document.querySelector('#user-rows').innerHTML = userRows(matches);
    document.querySelector('#user-count').textContent = `${matches.length} fictional users`;
  });
}
function filterFirms() {
  const query = document.querySelector('#firm-search').value.trim().toLowerCase();
  const status = document.querySelector('#status-filter').value;
  const matches = firms.filter(f => `${f.name} ${f.id}.kiensolutions.com`.toLowerCase().includes(query) && (!status || f.status === status));
  document.querySelector('#firm-rows').innerHTML = firmRows(matches);
  document.querySelector('#firm-count').textContent = `${matches.length} fictional firms`;
}
app.addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (button) {
    switch (button.dataset.action) {
      case 'theme': {
        const theme = isDark() ? 'light' : 'dark';
        document.documentElement.dataset.theme = theme;
        saveStorage(localStorage, 'kien-demo-theme', theme);
        button.textContent = `${theme === 'dark' ? 'Light' : 'Dark'} theme`;
        button.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
        break;
      }
      case 'menu': menuOpen = !menuOpen; document.querySelector('.shell').classList.toggle('menu-open', menuOpen); button.setAttribute('aria-expanded', String(menuOpen)); break;
      case 'signout': signedIn = false; mfaStep = false; email = ''; menuOpen = false; saveStorage(sessionStorage, 'kien-demo-session', null); document.querySelector('#toast').textContent = ''; render(); document.querySelector('#email').focus(); break;
      case 'back-login': mfaStep = false; login(); document.querySelector('#email').value = email; document.querySelector('#email').focus(); break;
      case 'status': { const firm = firms.find(f => f.id === button.dataset.id); firm.status = firm.status === 'Suspended' ? 'Active' : 'Suspended'; render(); document.querySelector('[data-action="status"]').focus(); toast(); break; }
      case 'branding': { firms.find(f => f.id === button.dataset.id).brandingReset = true; render(); document.querySelector('[data-action="branding"]').focus(); toast(); break; }
    }
    return;
  }
  const row = event.target.closest('[data-firm]');
  if (row && !event.target.closest('a')) location.hash = `firms/${row.dataset.firm}`;
});
window.addEventListener('hashchange', () => { menuOpen = false; render(true); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (!document.documentElement.dataset.theme) {
    const button = document.querySelector('[data-action="theme"]');
    if (button) { button.textContent = `${isDark() ? 'Light' : 'Dark'} theme`; button.setAttribute('aria-label', `Switch to ${isDark() ? 'light' : 'dark'} theme`); }
  }
});
render();
