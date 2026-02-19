import React, { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { API } from '../../services/api';

export default function Layout() {
    const [status, setStatus] = useState(null);
    const [tick, setTick] = useState(0);

    const fetchStatus = useCallback(async () => {
        try {
            const s = await API.getStatus();
            setStatus(s);
        } catch (e) {
            console.error('Status fetch error:', e.message);
        }
    }, []);

    useEffect(() => {
        fetchStatus();
        const id = setInterval(fetchStatus, 5000);
        return () => clearInterval(id);
    }, [fetchStatus]);

    const handleRefresh = () => {
        fetchStatus();
        setTick(t => t + 1);
    };

    return (
        <div className="app-layout">
            <Sidebar status={status} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Topbar status={status} onRefresh={handleRefresh} />
                <main className="main-content">
                    <Outlet context={{ status, refresh: handleRefresh, tick }} />
                </main>
            </div>
        </div>
    );
}
