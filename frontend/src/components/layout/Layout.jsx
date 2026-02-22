import React, { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { API } from '../../services/api';

export default function Layout() {
    const [status, setStatus] = useState(null);
    const [tick, setTick] = useState(0);
    const [wsData, setWsData] = useState(null); // To pass custom events down

    // Fallback static fetch
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

        // Setup WebSocket connection
        const wsUrl = process.env.NODE_ENV === 'production'
            ? `ws://${window.location.host}/ws`
            : 'ws://localhost:8000/ws';

        let ws;
        let reconnectTimeout;

        const connectWs = () => {
            ws = new WebSocket(wsUrl);

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);

                    if (msg.type === 'system_status') {
                        setStatus(prev => ({ ...prev, ...msg.data }));
                    } else if (msg.type === 'capital_update') {
                        setStatus(prev => prev ? { ...prev, capital: msg.data.capital } : null);
                    } else if (msg.type === 'positions_update' || msg.type === 'trade_executed') {
                        // Pass this down to Outlet context so children can refetch
                        setWsData(msg);
                        // Also trigger a general refresh tick
                        setTick(t => t + 1);
                    }
                } catch (e) {
                    console.error("WS Parse error", e);
                }
            };

            ws.onclose = () => {
                // Try to reconnect in 5 seconds
                reconnectTimeout = setTimeout(connectWs, 5000);
            };

            // Ping every 30s to keep connection alive
            const pingInterval = setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'ping' }));
                }
            }, 30000);

            ws._pingInterval = pingInterval;
        };

        connectWs();

        return () => {
            clearTimeout(reconnectTimeout);
            if (ws) {
                clearInterval(ws._pingInterval);
                ws.close();
            }
        };
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
                    <Outlet context={{ status, refresh: handleRefresh, tick, wsData }} />
                </main>
            </div>
        </div>
    );
}
