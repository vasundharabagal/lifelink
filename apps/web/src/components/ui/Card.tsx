import React from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * Light-theme card container for LIFELINK.
 * Pure white surface card with slate border — strict 60-30-10 color system.
 */
export function Card({ children, className }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-white rounded-2xl border border-slate-200 p-5 shadow-sm',
        className
      )}
    >
      {children}
    </div>
  );
}
