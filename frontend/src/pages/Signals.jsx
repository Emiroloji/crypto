import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { API } from '../services/api';

const DIRECTION_OPTS = ['Tüm Yönler', 'LONG', 'SHORT'];
const LIMIT_OPTS = [20, 50, 100];

function ScoreBar({ value, max = 100 }) {
    const pct = Math.min(100, Math.max(0, ((value ?? 0) / max) * 100));
    const color = pct > 66 ? 'var(--success)' : pct > 33 ? 'var(--warning)' : 'var(--danger)';
    return (
        <div className="score-bar-wrap">
            <div className="score-bar-track">
                <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span className="score-bar-label">{(value ?? 0).toFixed(0)}</span>
        </div>
    );
}

export default function Signals() {
    const { tick } = useOutletContext();
    const [signals, setSignals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [dirFilter, setDirFilter] = useState('Tüm Yönler');
    const [limit, setLimit] = useState(50);

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        API.getSignals(limit)
            .then(d => { if (!cancelled) { setSignals(d); setLoading(false); } })
            .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
        return () => { cancelled = true; };
    }, [tick, limit]);

    const filtered = dirFilter === 'Tüm Yönler'
        ? signals
        : signals.filter(s => s.direction === dirFilter);

    const fmt = (ts) => {
        if (!ts) return '—';
        const d = new Date(ts);
        return d.toLocaleString('tr-TR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="page">
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Trading Sinyalleri</span>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <select
                            className="form-select"
                            style={{ width: 'auto', padding: '6px 10px', fontSize: 12 }}
                            value={dirFilter}
                            onChange={e => setDirFilter(e.target.value)}
                        >
                            {DIRECTION_OPTS.map(o => <option key={o}>{o}</option>)}
                        </select>
                        <select
                            className="form-select"
                            style={{ width: 'auto', padding: '6px 10px', fontSize: 12 }}
                            value={limit}
                            onChange={e => setLimit(Number(e.target.value))}
                        >
                            {LIMIT_OPTS.map(o => <option key={o} value={o}>Son {o}</option>)}
                        </select>
                    </div>
                </div>

                {loading ? (
                    <div className="loading">Sinyaller yükleniyor…</div>
                ) : error ? (
                    <div className="empty-state" style={{ color: 'var(--danger)' }}>{error}</div>
                ) : filtered.length === 0 ? (
                    <div className="empty-state">Sinyal bulunamadı</div>
                ) : (
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Zaman</th>
                                    <th>Sembol</th>
                                    <th>Yön</th>
                                    <th className="th-right">Güven</th>
                                    <th>Trend</th>
                                    <th>Momentum</th>
                                    <th>Volume</th>
                                    <th className="th-right">R/R</th>
                                    <th className="th-right">Giriş</th>
                                    <th className="th-right">Stop</th>
                                    <th className="th-right">TP</th>
                                    <th>Tip</th>
                                    <th>Durum</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map(s => (
                                    <tr key={s.id}>
                                        <td className="mono text-muted" style={{ fontSize: 11 }}>{fmt(s.timestamp)}</td>
                                        <td><strong className="mono">{s.symbol}</strong></td>
                                        <td>
                                            <span className={`badge badge-${s.direction === 'LONG' ? 'success' : 'danger'}`}>
                                                {s.direction === 'LONG' ? '▲' : '▼'} {s.direction}
                                            </span>
                                        </td>
                                        <td className="td-right">
                                            <span className="mono" style={{
                                                fontWeight: 600,
                                                color: s.confidence_score > 80 ? 'var(--success)'
                                                    : s.confidence_score > 60 ? 'var(--warning)'
                                                        : 'var(--danger)',
                                            }}>
                                                {s.confidence_score?.toFixed(1)}%
                                            </span>
                                        </td>
                                        <td style={{ minWidth: 80 }}><ScoreBar value={s.trend_score} /></td>
                                        <td style={{ minWidth: 80 }}><ScoreBar value={s.momentum_score} /></td>
                                        <td style={{ minWidth: 80 }}><ScoreBar value={s.volume_score} /></td>
                                        <td className="td-right mono">{s.risk_reward_ratio?.toFixed(2)}</td>
                                        <td className="td-right mono">${s.entry_price?.toFixed(2)}</td>
                                        <td className="td-right mono" style={{ color: 'var(--danger)' }}>
                                            ${s.stop_loss?.toFixed(2)}
                                        </td>
                                        <td className="td-right mono" style={{ color: 'var(--success)' }}>
                                            ${s.take_profit?.toFixed(2)}
                                        </td>
                                        <td>
                                            {s.signal_type ? (
                                                <span className="badge badge-info">{s.signal_type}</span>
                                            ) : <span className="text-dim">—</span>}
                                        </td>
                                        <td>
                                            {s.executed
                                                ? <span className="badge badge-success">İşleme Alındı</span>
                                                : <span className="badge badge-default">Bekliyor</span>}
                                        </td>
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
