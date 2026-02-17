// Shared JavaScript for all pages
const API_BASE = 'http://localhost:8000';
let botRunning = false;
let killSwitchActive = false;

// Toast Notifications
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// API Fetch Helper
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'API error');
        }

        return data;
    } catch (error) {
        console.error(`Error fetching ${endpoint}:`, error);
        showToast(`Error: ${error.message}`, 'error');
        return null;
    }
}

// Bot Control
async function startBot() {
    const data = await fetchAPI('/bot/start', { method: 'POST' });
    if (data) {
        showToast('Bot started!', 'success');
        updateBotStatus(true);
    }
}

async function stopBot() {
    const data = await fetchAPI('/bot/stop', { method: 'POST' });
    if (data) {
        showToast('Bot stopped!', 'warning');
        updateBotStatus(false);
    }
}

function updateBotStatus(running) {
    botRunning = running;
    const statusDot = document.getElementById('botStatus');
    const statusText = document.getElementById('botStatusText');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');

    if (statusDot) {
        statusDot.className = running ? 'status-dot active' : 'status-dot';
    }
    if (statusText) {
        statusText.textContent = running ? 'Running' : 'Stopped';
    }
    if (startBtn) {
        startBtn.disabled = running;
    }
    if (stopBtn) {
        stopBtn.disabled = !running;
    }
}

// Load Status
async function loadStatus() {
    const status = await fetchAPI('/status');
    if (status) {
        // Update capital
        const capitalEl = document.getElementById('capital');
        if (capitalEl) {
            capitalEl.textContent = `$${status.capital.toLocaleString()}`;
        }

        // Update open positions
        const positionsEl = document.getElementById('openPositions');
        if (positionsEl) {
            positionsEl.textContent = status.open_positions;
        }

        // Update bot status
        updateBotStatus(status.running);

        // Update mode badge
        const modeBadge = document.getElementById('modeBadge');
        if (modeBadge) {
            if (status.paper_trading) {
                modeBadge.textContent = '🎮 DEMO MODE';
                modeBadge.className = 'badge badge-demo';
            } else {
                modeBadge.textContent = '🔴 LIVE TRADING';
                modeBadge.className = 'badge badge-danger';
            }
        }
    }
}

// Load Data (to be called from pages)
async function loadData() {
    await loadStatus();
    showToast('Data refreshed', 'success');
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('tr-TR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format number
function formatNumber(num, decimals = 2) {
    return num.toFixed(decimals);
}

// Set active nav link
function setActiveNav() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-link').forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}
