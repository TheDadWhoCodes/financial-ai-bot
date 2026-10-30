// --- Configuration ---
const OWNER = 'edmundchan';
const REPO = 'financial-ai-bot';
const CONFIG_FILE = 'bot_config.json';

// --- Auth ---
// Build-time injected password (GitHub Actions replaces this during build)
const PASSWORD = "__DASHBOARD_PASSWORD__";

const enabledToggle = document.getElementById('enabledToggle');
const threadsUserIdInput = document.getElementById('threadsUserId');
const accessTokenInput = document.getElementById('accessToken');
const saveBtn = document.getElementById('saveBtn');
const statusBtn = document.getElementById('statusBtn');
const output = document.getElementById('output');
const statusText = document.getElementById('statusText');
const loginScreen = document.getElementById('login-screen');
const protectedContent = document.getElementById('protected-content');

// --- Auth Gate ---
function checkAuth() {
  const savedAuth = sessionStorage.getItem('authenticated');
  if (savedAuth === 'true') {
    showDashboard();
  } else {
    showLogin();
  }
}

function login() {
  const input = document.getElementById('passInput').value;
  if (input === PASSWORD) {
    sessionStorage.setItem('authenticated', 'true');
    showDashboard();
  } else {
    document.getElementById('auth-error').style.display = 'block';
    document.getElementById('passInput').value = '';
  }
}

function showLogin() {
  loginScreen.style.display = 'flex';
  protectedContent.style.display = 'none';
}

function showDashboard() {
  loginScreen.style.display = 'none';
  protectedContent.style.display = 'block';
  initDashboard();
}

// --- Dashboard ---
function initDashboard() {
  // Load persisted settings from localStorage
  if (localStorage.getItem('bot_enabled') !== null) {
    enabledToggle.checked = localStorage.getItem('bot_enabled') === 'true';
    statusText.textContent = enabledToggle.checked ? 'On' : 'Off';
  }
  const savedUserId = localStorage.getItem('threads_user_id');
  if (savedUserId) threadsUserIdInput.value = savedUserId;
  const savedToken = localStorage.getItem('gh_pat');
  if (savedToken) accessTokenInput.value = savedToken;

  enabledToggle.addEventListener('change', () => {
    localStorage.setItem('bot_enabled', String(enabledToggle.checked));
    statusText.textContent = enabledToggle.checked ? 'On' : 'Off';
  });

  saveBtn.addEventListener('click', handleSave);
  statusBtn.addEventListener('click', handleStatus);
}

function log(msg) {
  const div = document.createElement('div');
  div.textContent = new Date().toLocaleTimeString() + ' ' + msg;
  output.appendChild(div);
  output.scrollTop = output.scrollHeight;
  console.log(msg);
}

async function request(method, url, body) {
  const token = accessTokenInput.value.trim();
  if (!token) throw new Error('Please enter your GitHub Personal Access Token first.');
  const headers = {
    'Authorization': 'Bearer ' + token,
    'X-GitHub-Api-Version': '2022-11-28',
    'Accept': 'application/vnd.github+json'
  };
  const opts = { method: method, headers: headers };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  let data = {};
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) {
    throw new Error('HTTP ' + res.status + ': ' + (data.message || JSON.stringify(data)));
  }
  return data;
}

async function saveConfigFile() {
  const enabled = enabledToggle.checked;
  const userId = threadsUserIdInput.value.trim();
  const filePath = 'https://api.github.com/repos/' + OWNER + '/' + REPO + '/contents/' + CONFIG_FILE;

  // Get current file SHA (if exists)
  let sha = null;
  try {
    const current = await request('GET', filePath);
    sha = current.sha;
  } catch (e) {
    log('Creating bot_config.json...');
  }

  const configContent = JSON.stringify({ enabled: enabled, threads_user_id: userId }, null, 2);
  const contentB64 = btoa(configContent);
  await request('PUT', filePath, {
    message: '🤖 Update bot config from control panel',
    content: contentB64,
    sha: sha,
    branch: 'main'
  });
}

async function triggerWorkflow() {
  const enabled = enabledToggle.checked;
  const userId = threadsUserIdInput.value.trim();
  const dispatchUrl = 'https://api.github.com/repos/' + OWNER + '/' + REPO + '/actions/workflows/daily_post.yml/dispatches';
  const inputs = { enabled: String(enabled) };
  if (userId) inputs.threads_user_id = userId;
  await request('POST', dispatchUrl, { ref: 'main', inputs: inputs });
}

async function getLastRun() {
  const runsUrl = 'https://api.github.com/repos/' + OWNER + '/' + REPO + '/actions/workflows/daily_post.yml/runs?per_page=1';
  return request('GET', runsUrl);
}

async function handleSave() {
  const token = accessTokenInput.value.trim();
  if (!token) { alert('Please paste your GitHub Personal Access Token.'); return; }
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';
  output.innerHTML = '';
  try {
    await saveConfigFile();
    log('✅ Config file saved to repository');
    await triggerWorkflow();
    log('✅ Workflow triggered');
    alert('Bot settings saved and workflow dispatched!');
  } catch (e) {
    log('❌ ' + e.message);
    alert('Error: ' + e.message);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = 'Save & Run Now';
  }
}

async function handleStatus() {
  statusBtn.disabled = true;
  statusBtn.textContent = 'Checking...';
  output.innerHTML = '';
  try {
    const data = await getLastRun();
    const run = data.workflow_runs && data.workflow_runs[0];
    if (!run) { log('No workflow runs found.'); return; }
    log('Last run: ' + run.status + (run.conclusion ? ' (' + run.conclusion + ')' : ''));
    log('Created: ' + new Date(run.created_at).toLocaleString());
    log('Updated: ' + new Date(run.updated_at).toLocaleString());
    log('Actions URL: ' + run.html_url);
  } catch (e) {
    log('❌ ' + e.message);
  } finally {
    statusBtn.disabled = false;
    statusBtn.textContent = 'Check Last Run';
  }
}

// --- Initialize ---
window.onload = checkAuth;