import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
    DollarSign, TrendingUp, TrendingDown, Activity,
    Radio, BarChart2, ShieldAlert, CheckCircle2, XCircle
} from 'lucide-react';
import { API } from '../services/api';

function StatCard({ label, value, sub, color, icon: Icon }) {
    return (
        <div className="stat-card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="stat-label">{label}</span>
                {Icon && <Icon size={14} style={{ color: color ?? 'var(--text-dim)' }} />}
            </div>
            <div className="stat-value" style={{ color: color ?? 'var(--text-main)' }}>{value}</div>
            {sub && <div className="stat-sub">{sub}</div>}
        </div>
    );
}

function PnlColor({ val }) {
    if (val == null) return <span className="text-dim">—</span>;
    const c = val > 0 ? 'var(--success)' : val < 0 ? 'var(--danger)' : 'var(--text-muted)';
    const sign = val > 0 ? '+' : '';
    return <span style={{ color: c, fontFamily: 'var(--mono)' }}>{sign}{val.toFixed(2)}</span>;
}

function DirectionBadge({ dir }) {
    if (!dir) return null;
    return (
        <span className={`badge badge-${dir === 'LONG' ? 'success' : 'danger'}`}>
            {dir === 'LONG' ? '▲' : '▼'} {dir}
        </span>
    );
}

export default function Dashboard() {
    const { status, tick, wsData } = useOutletContext();
    const [signals, setSignals] = useState([]);
    const [positions, setPositions] = useState([]);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        const fetchAll = async () => {
            try {
                setError(null);
                const [sig, pos] = await Promise.all([
                    API.getSignals(10),
                    API.getPositions(),
                ]);
                if (!cancelled) {
                    setSignals(sig);
                    setPositions(pos);
                }
            } catch (e) {
                if (!cancelled) setError(e.message);
            }

            // Fetch performance summary separately — silently ignore if not available
            try {
                const sum = await API.getPerformanceSummary(30);
                if (!cancelled) setSummary(sum);
            } catch (_) {
                // endpoint may not be active yet; no-op
            }

            if (!cancelled) setLoading(false);
        };
        fetchAll();
        return () => { cancelled = true; };
    }, [tick]);

    // Handle incoming realtime signals
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
        } else if (wsData.type === 'trade_executed') {
            // A new trade execution usually implies a signal was actued upon, refreshing signals can be helpful
            // or we could optimistically update if we had enough data
        }
    }, [wsData]);


    const totalPnl = positions.reduce((a, p) => a + (p.unrealized_pnl ?? 0), 0);
    const winRateDisp = summary ? `${summary.win_rate.toFixed(1)}%` : '—';
    const netPnlDisp = summary ? `$${summary.net_pnl.toFixed(2)}` : '—';

    return (
        <div className="page">
            {/* Stats Row */}
            <div className="grid-4">
                <StatCard
                    label="Toplam Sermaye"
                    value={`$${(status?.capital ?? 0).toFixed(2)}`}
                    sub="USDT"
                    icon={DollarSign}
                />
                <StatCard
                    label="Açık Pozisyonlar"
                    value={positions.length}
                    sub={`Unrealized P&L: $${totalPnl.toFixed(2)}`}
                    icon={Activity}
                    color={totalPnl > 0 ? 'var(--success)' : totalPnl < 0 ? 'var(--danger)' : undefined}
                />
                <StatCard
                    label="Win Rate (30g)"
                    value={winRateDisp}
                    sub={summary ? `${summary.total_trades} işlem` : ''}
                    icon={BarChart2}
                    color={summary?.win_rate > 50 ? 'var(--success)' : 'var(--danger)'}
                />
                <StatCard
                    label="Net P&L (30g)"
                    value={netPnlDisp}
                    sub={summary ? `${summary.winning_trades}W / ${summary.losing_trades}L` : ''}
                    icon={summary?.net_pnl >= 0 ? TrendingUp : TrendingDown}
                    color={summary?.net_pnl >= 0 ? 'var(--success)' : 'var(--danger)'}
                />
            </div>

            {/* Kill-switch warning */}
            {status?.kill_switch_active && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                    borderRadius: 'var(--r-lg)', padding: '12px 16px', color: 'var(--danger)',
                }}>
                    <ShieldAlert size={16} />
                    <strong>Kill-Switch AKTİF</strong> — Tüm işlemler durduruldu. Topbar'dan devre dışı bırakabilirsiniz.
                </div>
            )}

            {error && (
                <div style={{
                    background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                    borderRadius: 'var(--r-lg)', padding: '12px 16px', color: 'var(--danger)', fontSize: 13,
                }}>
                    Veri yüklenirken hata: {error}
                </div>
            )}

            <div className="grid-2">
                {/* Recent Signals */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Son Sinyaller</span>
                        <span className="badge badge-default">{signals.length}</span>
                    </div>
                    {loading ? (
                        <div className="loading">Yükleniyor…</div>
                    ) : signals.length === 0 ? (
                        <div className="empty-state">Henüz sinyal yok</div>
                    ) : (
                        <div className="table-wrap">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Sembol</th>
                                        <th>Yön</th>
                                        <th className="th-right">Güven</th>
                                        <th className="th-right">R/R</th>
                                        <th className="th-right">Durum</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {signals.map(s => (
                                        <tr key={s.id}>
                                            <td><span className="mono" style={{ fontWeight: 600 }}>{s.symbol}</span></td>
                                            <td><DirectionBadge dir={s.direction} /></td>
                                            <td className="td-right">
                                                <span className="mono" style={{
                                                    color: s.confidence_score > 80 ? 'var(--success)'
                                                        : s.confidence_score > 60 ? 'var(--warning)'
                                                            : 'var(--danger)',
                                                }}>
                                                    {s.confidence_score?.toFixed(1)}%
                                                </span>
                                            </td>
                                            <td className="td-right mono">{s.risk_reward_ratio?.toFixed(2)}</td>
                                            <td className="td-right">
                                                {s.executed
                                                    ? <span className="badge badge-success"><CheckCircle2 size={10} /> İşleme</span>
                                                    : <span className="badge badge-default">Bekliyor</span>}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* Open Positions */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Açık Pozisyonlar</span>
                        <span className="badge badge-default">{positions.length}</span>
                    </div>
                    {loading ? (
                        <div className="loading">Yükleniyor…</div>
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
                                        <th className="th-right">Güncel</th>
                                        <th className="th-right">P&L</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {positions.map(p => (
                                        <tr key={p.id}>
                                            <td><span className="mono" style={{ fontWeight: 600 }}>{p.symbol}</span></td>
                                            <td><DirectionBadge dir={p.direction} /></td>
                                            <td className="td-right mono">${p.entry_price?.toFixed(2)}</td>
                                            <td className="td-right mono">${p.current_price?.toFixed(2)}</td>
                                            <td className="td-right"><PnlColor val={p.unrealized_pnl} /></td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {/* Performance Summary Row */}
            {summary && (
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Performans Özeti (30 Gün)</span>
                    </div>
                    <div className="grid-4">
                        <StatCard label="Sharpe Ratio" value={summary.sharpe_ratio?.toFixed(2) ?? '—'} icon={BarChart2} />
                        <StatCard label="Max Drawdown" value={`${summary.max_drawdown?.toFixed(2)}%`} color="var(--danger)" />
                        <StatCard label="En İyi Gün" value={`$${summary.best_day_pnl?.toFixed(2)}`} color="var(--success)" />
                        <StatCard label="Toplam Komisyon" value={`$${summary.total_fees?.toFixed(2)}`} color="var(--warning)" />
                    </div>
                </div>
            )}
        </div>
    );
}
