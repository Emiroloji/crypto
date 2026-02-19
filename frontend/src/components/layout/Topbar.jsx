import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Play, Square, RotateCcw, AlertTriangle, Loader2 } from 'lucide-react';
import { API } from '../../services/api';

const PAGE_TITLES = {
    '/': 'Dashboard',
    '/signals': 'Sinyaller',
    '/positions': 'Pozisyonlar',
    '/settings': 'Ayarlar',
};

export default function Topbar({ status, onRefresh }) {
    const location = useLocation();
    const title = PAGE_TITLES[location.pathname] ?? 'CryptoBot';
    const [busy, setBusy] = useState(null);

    const handle = async (action, label) => {
        setBusy(label);
        try {
            await action();
            onRefresh?.();
        } catch (e) {
            console.error(e);
        } finally {
            setBusy(null);
        }
    };

    return (
        <header className="topbar">
            <span className="topbar-title">{title}</span>

            <div className="topbar-actions">
                {/* Capital badge */}
                <span className="badge badge-default" style={{ fontFamily: 'var(--mono)' }}>
                    ${(status?.capital ?? 0).toFixed(2)}
                </span>

                <div className="btn-divider" />

                {/* Kill-switch */}
                {status?.kill_switch_active ? (
                    <button
                        className="btn btn-warning btn-sm"
                        onClick={() => handle(API.deactivateKS, 'ks')}
                        disabled={!!busy}
                    >
                        {busy === 'ks' ? <Loader2 size={12} className="spin" /> : <AlertTriangle size={12} />}
                        KS Devre Dışı
                    </button>
                ) : (
                    <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => handle(API.activateKS, 'ks')}
                        disabled={!!busy}
                    >
                        <AlertTriangle size={12} />
                        Kill-Switch
                    </button>
                )}

                {/* Start / Stop */}
                {status?.running ? (
                    <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handle(API.stopBot, 'bot')}
                        disabled={!!busy}
                    >
                        {busy === 'bot' ? <Loader2 size={12} className="spin" /> : <Square size={12} />}
                        Durdur
                    </button>
                ) : (
                    <button
                        className="btn btn-success btn-sm"
                        onClick={() => handle(API.startBot, 'bot')}
                        disabled={!!busy}
                    >
                        {busy === 'bot' ? <Loader2 size={12} className="spin" /> : <Play size={12} />}
                        Başlat
                    </button>
                )}

                {/* Refresh */}
                <button className="btn btn-ghost btn-icon btn-sm" onClick={onRefresh}>
                    <RotateCcw size={14} />
                </button>
            </div>
        </header>
    );
}
