import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
    LayoutDashboard, Radio, TrendingUp, Settings,
    Zap, Activity, CircleDot
} from 'lucide-react';
import { API } from '../../services/api';

const NAV = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/signals', icon: Radio, label: 'Sinyaller' },
    { to: '/positions', icon: TrendingUp, label: 'Pozisyonlar' },
    { to: '/settings', icon: Settings, label: 'Ayarlar' },
];

export default function Sidebar({ status }) {
    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">
                    <Zap size={16} />
                </div>
                <div className="sidebar-logo-text">
                    Crypto<span>Bot</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                <div className="sidebar-section">Navigasyon</div>
                {NAV.map(({ to, icon: Icon, label }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
                    >
                        <Icon size={16} />
                        {label}
                    </NavLink>
                ))}
            </nav>

            <div className="sidebar-footer">
                <div className="bot-status">
                    <span
                        className={`status-dot ${status?.running
                                ? status?.paper_trading ? 'demo' : 'running'
                                : 'stopped'
                            }`}
                    />
                    <div>
                        <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-main)' }}>
                            {status?.running ? (status?.paper_trading ? 'Demo Modu' : 'Canlı') : 'Durduruldu'}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                            {status?.open_positions ?? 0} açık pozisyon
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}
