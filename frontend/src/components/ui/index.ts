import React from 'react';
import clsx from 'clsx';

/**
 * UI Components
 * Reusable UI components for the application
 */

// Button Component
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
    children: React.ReactNode;
}

export function Button({
    variant = 'primary', 
    size = 'md', 
    loading = false, 
    disabled = false, 
    className, 
    children, 
    ...props
}: ButtonProps) {
    const baseClasses = 'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black disabled:opacity-50 disabled:cursor-not-allowed';

    const variants = {
        primary: 'bg-white text-black hover:bg-gray-200 focus:ring-white',
        secondary: 'bg-gray-800 text-white hover:bg-gray-700 focus:ring-gray-400',
        ghost: 'bg-transparent text-white hover:bg-gray-900 focus:ring-gray-400',
        danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-400'
    } as const;

    const sizes = {
        sm: 'px-3 py-1.5 text-sm',
        md: 'px-4 py-2 text-sm',
        lg: 'px-6 py-3 text-base'
    } as const;

    return (
        <button
            className={clsx(
                baseClasses,
                variants[variant],
                sizes[size],
                className
            )}
            disabled={disabled || loading}
            {...props}
        >
            {loading && (
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
            )}
            {children}
        </button>
    );
}

// Input Component
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
}

export const Input: React.FC<InputProps> = ({
    label,
    error,
    className,
    ...props
}) => {
    return (
        <div className="w-full">
            {label && (
                <label className="block text-sm font-medium text-gray-300 mb-1">
                    {label}
                </label>
            )}
            <input
                className={clsx(
                    'w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-white focus:border-transparent',
                    error && 'border-red-500',
                    className
                )}
                {...props}
            />
            {error && (
                <p className="mt-1 text-sm text-red-400">{error}</p>
            )}
        </div>
    );
};

// Card Component
interface CardProps {
    children: React.ReactNode;
    className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className }) => {
    return (
        <div className={clsx('bg-gray-900 border border-gray-800 rounded-lg p-4', className)}>
            {children}
        </div>
    );
};

// Loading Spinner Component
export const LoadingSpinner: React.FC<{ className?: string }> = ({ className }) => {
    return (
        <div className={clsx('animate-spin rounded-full border-2 border-gray-300 border-t-white', className)}>
            <span className="sr-only">Loading...</span>
        </div>
    );
};

// Alert Component
interface AlertProps {
    variant?: 'info' | 'success' | 'warning' | 'error';
    children: React.ReactNode;
    className?: string;
}

export const Alert: React.FC<AlertProps> = ({ 
    variant = 'info', 
    children, 
    className 
}) => {
    const variants = {
        info: 'bg-blue-900/50 border-blue-600 text-blue-200',
        success: 'bg-green-900/50 border-green-600 text-green-200',
        warning: 'bg-yellow-900/50 border-yellow-600 text-yellow-200',
        error: 'bg-red-900/50 border-red-600 text-red-200'
    };

    return (
        <div className={clsx(
            'p-4 rounded-lg border',
            variants[variant],
            className
        )}>
            {children}
        </div>
    );
};

// Badge Component
interface BadgeProps {
    variant?: 'default' | 'success' | 'warning' | 'danger';
    children: React.ReactNode;
    className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ 
    variant = 'default', 
    children, 
    className 
}) => {
    const variants = {
        default: 'bg-gray-700 text-gray-200',
        success: 'bg-green-600 text-white',
        warning: 'bg-yellow-600 text-white',
        danger: 'bg-red-600 text-white'
    };

    return (
        <span className={clsx(
            'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
            variants[variant],
            className
        )}>
            {children}
        </span>
    );
};