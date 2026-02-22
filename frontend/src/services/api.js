import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
    baseURL: BASE_URL,
    headers: { 'Content-Type': 'application/json' },
    timeout: 10000,
});

// Response interceptor for error handling
api.interceptors.response.use(
    (res) => res,
    (err) => {
        const msg = err.response?.data?.detail || err.message || 'Bilinmeyen hata';
        return Promise.reject(new Error(msg));
    }
);

export const API = {
    // System
    getStatus: () => api.get('/status').then(r => r.data),
    getConfig: () => api.get('/config').then(r => r.data),
    updateConfig: (data) => api.post('/config', data).then(r => r.data),
    startBot: () => api.post('/bot/start').then(r => r.data),
    stopBot: () => api.post('/bot/stop').then(r => r.data),
    activateKS: () => api.post('/killswitch/activate').then(r => r.data),
    deactivateKS: () => api.post('/killswitch/deactivate').then(r => r.data),
    health: () => api.get('/health').then(r => r.data),

    // Market Data
    getSignals: (limit = 50) => api.get(`/signals?limit=${limit}`).then(r => r.data),
    getTrades: (limit = 50) => api.get(`/trades?limit=${limit}`).then(r => r.data),
    getPositions: () => api.get('/positions').then(r => r.data),

    // Performance
    getPerformance: (days = 30) => api.get(`/performance?days=${days}`).then(r => r.data),
    getPerformanceSummary: (days = 30) => api.get(`/performance/summary?days=${days}`).then(r => r.data),

    // Actions
    closePosition: (symbol) => api.post(`/positions/${encodeURIComponent(symbol)}/close`).then(r => r.data),
};

export default api;
