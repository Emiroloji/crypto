import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Save, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { API } from '../services/api';

function Section({ title, children }) {
    return (
        <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: 20 }}>
                <span className="section-title">{title}</span>
            </div>
            {children}
        </div>
    );
}

function FormRow({ label, hint, children }) {
    return (
        <div className="form-group">
            <label className="form-label">{label}</label>
            {children}
            {hint && <span className="form-hint">{hint}</span>}
        </div>
    );
}

function Toggle({ label, desc, checked, onChange }) {
    return (
        <div className="toggle-row">
            <div>
                <div className="toggle-label">{label}</div>
                {desc && <div className="toggle-desc">{desc}</div>}
            </div>
            <label className="toggle">
                <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} />
                <span className="toggle-slider" />
            </label>
        </div>
    );
}

export default function Settings() {
    const { tick } = useOutletContext();
    const [cfg, setCfg] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [toast, setToast] = useState(null); // {type, msg}
    const [error, setError] = useState(null);

    // Local form state
    const [form, setForm] = useState({
        trading_pairs: '',
        timeframes: '',
        max_leverage: 5,
        max_position_size_pct: 2.0,
        max_daily_loss_pct: 5.0,
        max_concurrent_trades: 3,
        risk_per_trade_pct: 1.5,
        min_risk_reward_ratio: 2.5,
        confidence_threshold: 75.0,
        stop_loss_pct: 2.0,
        paper_trading: true,
    });

    useEffect(() => {
        let cancelled = false;
        API.getConfig()
            .then(d => {
                if (cancelled) return;
                setCfg(d);
                setForm({
                    trading_pairs: Array.isArray(d.trading_pairs) ? d.trading_pairs.join(', ') : d.trading_pairs,
                    timeframes: Array.isArray(d.timeframes) ? d.timeframes.join(', ') : d.timeframes,
                    max_leverage: d.max_leverage ?? 5,
                    max_position_size_pct: d.max_position_size_pct ?? 2.0,
                    max_daily_loss_pct: d.max_daily_loss_pct ?? 5.0,
                    max_concurrent_trades: d.max_concurrent_trades ?? 3,
                    risk_per_trade_pct: d.risk_per_trade_pct ?? 1.5,
                    min_risk_reward_ratio: d.min_risk_reward_ratio ?? 2.5,
                    confidence_threshold: d.confidence_threshold ?? 75.0,
                    stop_loss_pct: d.stop_loss_pct ?? 2.0,
                    paper_trading: d.paper_trading ?? true,
                });
                setLoading(false);
            })
            .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
        return () => { cancelled = true; };
    }, [tick]);

    const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

    const handleSave = async () => {
        setSaving(true);
        try {
            const payload = {
                trading_pairs: form.trading_pairs.split(',').map(s => s.trim()).filter(Boolean),
                timeframes: form.timeframes.split(',').map(s => s.trim()).filter(Boolean),
                max_leverage: Number(form.max_leverage),
                max_position_size_pct: Number(form.max_position_size_pct),
                max_daily_loss_pct: Number(form.max_daily_loss_pct),
                max_concurrent_trades: Number(form.max_concurrent_trades),
                risk_per_trade_pct: Number(form.risk_per_trade_pct),
                min_risk_reward_ratio: Number(form.min_risk_reward_ratio),
                confidence_threshold: Number(form.confidence_threshold),
                stop_loss_pct: Number(form.stop_loss_pct),
            };
            await API.updateConfig(payload);
            setToast({ type: 'success', msg: 'Ayarlar kaydedildi (runtime). Kalıcı için .env güncellenmeli.' });
        } catch (e) {
            setToast({ type: 'danger', msg: `Hata: ${e.message}` });
        } finally {
            setSaving(false);
            setTimeout(() => setToast(null), 4000);
        }
    };

    if (loading) return <div className="loading">Ayarlar yükleniyor…</div>;
    if (error) return <div className="empty-state" style={{ color: 'var(--danger)' }}>{error}</div>;

    return (
        <div className="page">
            {/* Toast */}
            {toast && (
                <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    background: toast.type === 'success' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
                    border: `1px solid ${toast.type === 'success' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
                    borderRadius: 'var(--r-lg)', padding: '12px 16px', fontSize: 13,
                    color: toast.type === 'success' ? 'var(--success)' : 'var(--danger)',
                }}>
                    {toast.type === 'success'
                        ? <CheckCircle2 size={16} />
                        : <AlertCircle size={16} />
                    }
                    {toast.msg}
                </div>
            )}

            {/* Environment info */}
            <div style={{
                display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center',
                padding: '10px 16px',
                background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)',
                fontSize: 12,
            }}>
                <span className="text-muted">Ortam:</span>
                <span className="badge badge-primary">{cfg?.environment ?? '—'}</span>
                <span className="text-muted">Log seviyesi:</span>
                <span className="badge badge-default">{cfg?.log_level ?? '—'}</span>
                <span className="text-muted">Mod:</span>
                {cfg?.paper_trading
                    ? <span className="badge badge-warning">Demo (Paper Trading)</span>
                    : <span className="badge badge-danger">Canlı Trading</span>}
            </div>

            <div className="grid-2">
                {/* Trading Params */}
                <Section title="İşlem Parametreleri">
                    <FormRow label="Güven Eşiği (%)" hint="Minimum sinyal güven skoru">
                        <input
                            type="number" className="form-input" min={50} max={100} step={0.5}
                            value={form.confidence_threshold}
                            onChange={e => set('confidence_threshold', e.target.value)}
                        />
                    </FormRow>
                    <FormRow label="Min Risk/Reward Oranı" hint="Örn: 2.5">
                        <input
                            type="number" className="form-input" min={1} max={10} step={0.1}
                            value={form.min_risk_reward_ratio}
                            onChange={e => set('min_risk_reward_ratio', e.target.value)}
                        />
                    </FormRow>
                    <FormRow label="Max Pozisyon Büyüklüğü (%)" hint="Sermayenin yüzdesi">
                        <input
                            type="number" className="form-input" min={0.1} max={10} step={0.1}
                            value={form.max_position_size_pct}
                            onChange={e => set('max_position_size_pct', e.target.value)}
                        />
                    </FormRow>
                    <FormRow label="İşlem Başına Risk (%)" hint="Her işlem için risk">
                        <input
                            type="number" className="form-input" min={0.5} max={5} step={0.1}
                            value={form.risk_per_trade_pct}
                            onChange={e => set('risk_per_trade_pct', e.target.value)}
                        />
                    </FormRow>
                    <FormRow label="Stop Loss (%)" hint="Varsayılan stop loss">
                        <input
                            type="number" className="form-input" min={0.5} max={10} step={0.1}
                            value={form.stop_loss_pct}
                            onChange={e => set('stop_loss_pct', e.target.value)}
                        />
                    </FormRow>
                    <FormRow label="Max Eşzamanlı İşlem">
                        <input
                            type="number" className="form-input" min={1} max={10} step={1}
                            value={form.max_concurrent_trades}
                            onChange={e => set('max_concurrent_trades', e.target.value)}
                        />
                    </FormRow>
                </Section>

                {/* Risk + Exchange */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    <Section title="Risk Yönetimi">
                        <FormRow label="Günlük Max Kayıp (%)" hint="Kill-switch eşiği">
                            <input
                                type="number" className="form-input" min={1} max={20} step={0.5}
                                value={form.max_daily_loss_pct}
                                onChange={e => set('max_daily_loss_pct', e.target.value)}
                            />
                        </FormRow>
                        <FormRow label="Max Kaldıraç" hint="1x – 20x">
                            <input
                                type="number" className="form-input" min={1} max={20} step={1}
                                value={form.max_leverage}
                                onChange={e => set('max_leverage', e.target.value)}
                            />
                        </FormRow>
                        <Toggle
                            label="Paper Trading (Demo)"
                            desc="Gerçek para kullanmadan test et"
                            checked={form.paper_trading}
                            onChange={v => set('paper_trading', v)}
                        />
                    </Section>

                    <Section title="Borsa & Çiftler">
                        <FormRow label="İşlem Çiftleri" hint="Virgülle ayırın — örn: BTC/USDT, ETH/USDT">
                            <input
                                type="text" className="form-input"
                                value={form.trading_pairs}
                                onChange={e => set('trading_pairs', e.target.value)}
                                placeholder="BTC/USDT, ETH/USDT"
                            />
                        </FormRow>
                        <FormRow label="Zaman Dilimleri" hint="Virgülle ayırın — örn: 1m, 5m, 15m">
                            <input
                                type="text" className="form-input"
                                value={form.timeframes}
                                onChange={e => set('timeframes', e.target.value)}
                                placeholder="1m, 5m, 15m"
                            />
                        </FormRow>
                    </Section>
                </div>
            </div>

            {/* Save button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                    {saving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
                    {saving ? 'Kaydediliyor…' : 'Değişiklikleri Kaydet'}
                </button>
            </div>
        </div>
    );
}
