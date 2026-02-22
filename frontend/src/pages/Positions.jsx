import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { X, Loader2 } from 'lucide-react';
import { API } from '../services/api';

function PnlBadge({ val }) {
    if (val == null) return <span className="text-dim">—</span>;
    const color = val > 0 ? 'var(--success)' : val < 0 ? 'var(--danger)' : 'var(--text-muted)';
    const sign = val > 0 ? '+' : '';
    return <span style={{ color, fontFamily: 'var(--mono)', fontWeight: 600 }}>{sign}{val.toFixed(2)}</span>;
}

function PctBadge({ val }) {
    if (val == null) return <span className="text-dim">—</span>;
    const color = val > 0 ? 'var(--success)' : val < 0 ? 'var(--danger)' : 'var(--text-muted)';
    const sign = val > 0 ? '+' : '';
    return <span style={{ color, fontFamily: 'var(--mono)', fontSize: 11 }}>{sign}{val.toFixed(2)}%</span>;
}

function StatusBadge({ status }) {
    const map = {
        OPEN: 'badge-success',
        CLOSED: 'badge-default',
        PENDING: 'badge-warning',
        CANCELLED: 'badge-danger',
    };
    return <span className={`badge ${map[status] ?? 'badge-default'}`}>{status}</span>;
}

export default function Positions() {
    const { tick, wsData } = useOutletContext();
    const [positions, setPositions] = useState([]);
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [closing, setClosing] = useState(null);

    const fetchData = async () => {
        try {
            setError(null);
            const [pos, trd] = await Promise.all([
                API.getPositions(),
                API.getTrades(50),
            ]);
            setPositions(pos);
            setTrades(trd);
            setLoading(false);
        } catch (e) {
            setError(e.message);
            setLoading(false);
        }
    };

    useEffect(() => {
        setLoading(true);
        fetchData();
    }, [tick]);

    // Handle real-time position updates
    useEffect(() => {
        if (!wsData) return;

        if (wsData.type === 'positions_update') {
            setPositions(prev => {
                const map = new Map(prev.map(p => [p.symbol, p]));
                wsData.data.forEach(update => {
                    if (map.has(update.symbol)) {
                        map.set(update.symbol, { ...map.get(update.symbol), ...update });
                    }
                });
                return Array.from(map.values());
            });
        }
    }, [wsData]);

    const handleClose = async (symbol) => {
        setClosing(symbol);
        try {
            await API.closePosition(symbol);
            await fetchData();
        } catch (e) {
            alert(`Hata: ${e.message}`);
        } finally {
            setClosing(null);
        }
    };

    const fmt = (ts) => {
        if (!ts) return '—';
        const d = new Date(ts);
        return d.toLocaleString('tr-TR', {
            day: '2-digit', month: '2-digit', year: '2-digit',
            hour: '2-digit', minute: '2-digit',
        });
    };

    return (
        <div className="page">
            {/* Open Positions */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Açık Pozisyonlar</span>
                    <span className="badge badge-default">{positions.length}</span>
                </div>
                {loading ? (
                    <div className="loading">Yükleniyor…</div>
                ) : error ? (
                    <div className="empty-state" style={{ color: 'var(--danger)' }}>{error}</div>
                ) : positions.length === 0 ? (
                    <div className="empty-state">Açık pozisyon yok</div>
                ) : (
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Sembol</th>
                                    <th>Yön</th>
                                    <th className="th-right">Giriş</th>
                                    <th className="th-right">Güncel Fiyat</th>
                                    <th className="th-right">Boyut</th>
                                    <th className="th-right">Stop</th>
                                    <th className="th-right">TP</th>
                                    <th className="th-right">Unrealized P&L</th>
                                    <th className="th-right">Açılış</th>
                                    <th className="td-center">İşlem</th>
                                </tr>
                            </thead>
                            <tbody>
                                {positions.map(p => (
                                    <tr key={p.id}>
                                        <td><strong className="mono">{p.symbol}</strong></td>
                                        <td>
                                            <span className={`badge badge-${p.direction === 'LONG' ? 'success' : 'danger'}`}>
                                                {p.direction === 'LONG' ? '▲' : '▼'} {p.direction}
                                            </span>
                                        </td>
                                        <td className="td-right mono">${p.entry_price?.toFixed(2)}</td>
                                        <td className="td-right mono">${p.current_price?.toFixed(2)}</td>
                                        <td className="td-right mono">{p.position_size?.toFixed(4)}</td>
                                        <td className="td-right mono" style={{ color: 'var(--danger)' }}>
                                            ${p.stop_loss?.toFixed(2)}
                                        </td>
                                        <td className="td-right mono" style={{ color: 'var(--success)' }}>
                                            ${p.take_profit?.toFixed(2)}
                                        </td>
                                        <td className="td-right"><PnlBadge val={p.unrealized_pnl} /></td>
                                        <td className="td-right mono text-muted" style={{ fontSize: 11 }}>
                                            {fmt(p.opened_at)}
                                        </td>
                                        <td className="td-center">
                                            <button
                                                className="btn btn-danger btn-sm"
                                                onClick={() => handleClose(p.symbol)}
                                                disabled={closing === p.symbol}
                                            >
                                                {closing === p.symbol
                                                    ? <Loader2 size={11} />
                                                    : <X size={11} />
                                                }
                                                Kapat
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Trade History */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">İşlem Geçmişi</span>
                    <span className="badge badge-default">Son 50</span>
                </div>
                {loading ? (
                    <div className="loading">Yükleniyor…</div>
                ) : trades.length === 0 ? (
                    <div className="empty-state">İşlem geçmişi yok</div>
                ) : (
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Tarih</th>
                                    <th>Sembol</th>
                                    <th>Yön</th>
                                    <th className="th-right">Giriş</th>
                                    <th className="th-right">Çıkış</th>
                                    <th className="th-right">P&L</th>
                                    <th className="th-right">%</th>
                                    <th className="th-right">Komisyon</th>
                                    <th>Durum</th>
                                </tr>
                            </thead>
                            <tbody>
                                {trades.map(t => (
                                    <tr key={t.id}>
                                        <td className="mono text-muted" style={{ fontSize: 11 }}>{fmt(t.created_at)}</td>
                                        <td><strong className="mono">{t.symbol}</strong></td>
                                        <td>
                                            <span className={`badge badge-${t.direction === 'LONG' ? 'success' : 'danger'}`}>
                                                {t.direction === 'LONG' ? '▲' : '▼'} {t.direction}
                                            </span>
                                        </td>
                                        <td className="td-right mono">${t.entry_price?.toFixed(2)}</td>
                                        <td className="td-right mono">
                                            {t.exit_price != null ? `$${t.exit_price.toFixed(2)}` : <span className="text-dim">—</span>}
                                        </td>
                                        <td className="td-right"><PnlBadge val={t.pnl} /></td>
                                        <td className="td-right"><PctBadge val={t.pnl_percent} /></td>
                                        <td className="td-right mono text-muted">
                                            {t.fees != null ? `$${t.fees.toFixed(4)}` : '—'}
                                        </td>
                                        <td><StatusBadge status={t.status} /></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
