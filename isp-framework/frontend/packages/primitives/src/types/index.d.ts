import React from 'react';
/**
 * Type declarations for @dotmac/primitives package
 */

declare module '@dotmac/primitives' {
  // Core primitive types
  export interface ButtonProps {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
    size?: 'sm' | 'md' | 'lg';
    disabled?: boolean;
    children: React.ReactNode;
    onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  }

  export interface InputProps {
    type?: 'text' | 'email' | 'password' | 'number';
    placeholder?: string;
    value?: string;
    onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
    disabled?: boolean;
    required?: boolean;
  }

  export interface CardProps {
    children: React.ReactNode;
    className?: string;
    variant?: 'default' | 'elevated' | 'outlined';
  }

  // Export components
  export const Button: React.FC<ButtonProps>;
  export const Input: React.FC<InputProps>;
  export const Card: React.FC<CardProps>;

  // Re-export all from primitives
  export * from './components';
  export * from './types';
}
