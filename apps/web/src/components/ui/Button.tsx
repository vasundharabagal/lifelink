import React from 'react';
import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

type ButtonVariant = 'primary' | 'emergency' | 'secondary' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  children: React.ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-slate-900 text-white hover:bg-slate-800 active:bg-slate-950 border border-transparent',
  emergency:
    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 border border-transparent shadow-lg',
  secondary:
    'bg-white text-slate-900 hover:bg-slate-50 active:bg-slate-100 border border-slate-300',
  ghost:
    'bg-transparent text-slate-700 hover:bg-slate-100 active:bg-slate-200 border border-transparent',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'min-h-[48px] min-w-[48px] px-3 py-2 text-sm',
  md: 'min-h-[48px] min-w-[48px] px-4 py-2.5 text-base',
  lg: 'min-h-[56px] min-w-[56px] px-6 py-3 text-lg',
};

/**
 * Accessible button component for LIFELINK.
 * Enforces minimum 48×48px touch targets (WCAG 2.5.5 Target Size).
 * All interactive targets must use this component.
 */
export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || isLoading}
      className={clsx(
        // Base
        'inline-flex items-center justify-center gap-2 rounded-xl font-semibold',
        'transition-colors duration-150 select-none cursor-pointer',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2',
        // Disabled
        (disabled || isLoading) && 'opacity-50 cursor-not-allowed',
        // Variant
        variantClasses[variant],
        // Size
        sizeClasses[size],
        className
      )}
    >
      {isLoading && <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
