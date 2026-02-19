import React from 'react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export function Card({ children, className }) {
    return (
        <div className={cn("bg-card border border-border rounded-lg p-5", className)}>
            {children}
        </div>
    );
}

export function CardHeader({ title, children, className }) {
    return (
        <div className={cn("flex items-center justify-between mb-4", className)}>
            {title && <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">{title}</h3>}
            {children}
        </div>
    );
}

export function Badge({ children, variant = 'default', className }) {
    const variants = {
        default: 'bg-bg-hover text-text-muted',
        success: 'bg-success/10 text-success',
        danger: 'bg-danger/10 text-danger',
        warning: 'bg-warning/10 text-warning',
        info: 'bg-info/10 text-info',
        primary: 'bg-primary/10 text-primary',
    };

    return (
        <span className={cn("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium", variants[variant], className)}>
            {children}
        </span>
    );
}
