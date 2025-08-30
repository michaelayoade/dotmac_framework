/**
 * Universal Dashboard Types
 * Portal-agnostic type definitions for DRY dashboard architecture
 */

export type PortalVariant = 'admin' | 'customer' | 'reseller' | 'technician' | 'management';

export interface Activity {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  description: string;
  timestamp: Date;
  userId?: string;
  userName?: string | undefined;
  metadata?: Record<string, any>;
}

export interface ResourceMetrics {
  cpu: {
    current: number;
    history: Array<{ timestamp: Date; value: number }>;
  };
  memory: {
    current: number;
    history: Array<{ timestamp: Date; value: number }>;
  };
  storage: {
    current: number;
    history: Array<{ timestamp: Date; value: number }>;
  };
  bandwidth: {
    current: number;
    history: Array<{ timestamp: Date; value: number }>;
  };
}

export interface TableColumn {
  key: string;
  title: string;
  width?: string;
  sortable?: boolean | undefined;
  filterable?: boolean | undefined;
  render?: ((value: any, record: any) => React.ReactNode) | undefined;
}

export interface EntityAction {
  key: string;
  label: string;
  icon?: React.ComponentType;
  variant?: 'primary' | 'secondary' | 'danger' | undefined;
  onClick: (entity: any) => void;
  isVisible?: (entity: any) => boolean;
  isDisabled?: (entity: any) => boolean;
}

export interface MetricsCardData {
  title: string;
  value: string | number;
  change?: string | undefined;
  trend?: 'up' | 'down' | 'stable' | undefined;
  icon?: React.ComponentType;
  description?: string | undefined;
  actionLabel?: string;
  onAction?: () => void;
}

export interface ActivityFeedConfig {
  showFilters: boolean;
  showUserAvatars: boolean;
  maxItems: number;
  refreshInterval?: number;
}

export interface ChartTimeframe {
  label: string;
  value: string;
  hours: number;
}

export interface DashboardTheme {
  colors: {
    primary: string;
    secondary: string;
    success: string;
    warning: string;
    error: string;
    background: string;
    surface: string;
    text: {
      primary: string;
      secondary: string;
      muted: string;
    };
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
}
