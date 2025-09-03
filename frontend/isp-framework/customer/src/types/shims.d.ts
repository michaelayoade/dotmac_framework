declare module '@dotmac/providers' {
  import type React from 'react';
  export interface ErrorBoundaryProps {
    portal: 'customer' | 'admin' | 'reseller' | 'technician' | 'management';
    fallback?: any;
    onError?: (error: Error, info: any) => void;
    children?: React.ReactNode;
  }
  export const ErrorBoundary: React.ComponentType<ErrorBoundaryProps>;
}

declare module '@dotmac/ui' {
  import type React from 'react';
  export const Button: React.ComponentType<any>;
  export const Input: React.ComponentType<any>;
  export const Card: React.ComponentType<any>;
  export const CardContent: React.ComponentType<any>;
  export const CardHeader: React.ComponentType<any>;
  export const CardTitle: React.ComponentType<any>;
}

declare module '@dotmac/primitives' {
  import type React from 'react';
  export const Alert: React.ComponentType<any>;
  export const Loading: React.ComponentType<any>;
  export const Progress: React.ComponentType<any>;
}

declare module '@dotmac/monitoring' {
  export function audit(...args: any[]): any;
  export function auditContext(...args: any[]): any;
  const defaultExport: any;
  export default defaultExport;
}

declare module '@dotmac/headless/utils/validation' {
  export const validate: any;
  export const validateInput: any;
}

declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}
