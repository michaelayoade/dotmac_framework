import { ReactNode } from 'react';

export interface MobileLayoutProps {
  children: ReactNode;
  /** Show header */
  showHeader?: boolean;
  /** Show navigation */
  showNavigation?: boolean;
  /** Navigation position */
  navigationPosition?: 'top' | 'bottom';
  /** Safe area handling */
  safeArea?: boolean;
  /** Full screen mode */
  fullScreen?: boolean;
  /** Background color */
  backgroundColor?: string;
  /** Custom header component */
  header?: ReactNode;
  /** Custom navigation component */
  navigation?: ReactNode;
  /** Custom CSS classes */
  className?: string;
}

export interface MobileNavigationProps {
  /** Navigation items */
  items: NavigationItem[];
  /** Current active item */
  activeItem?: string;
  /** Position of navigation */
  position?: 'top' | 'bottom';
  /** Show labels */
  showLabels?: boolean;
  /** Badge counts for items */
  badges?: Record<string, number>;
  /** Custom CSS classes */
  className?: string;
  /** Item click handler */
  onItemClick?: (item: NavigationItem) => void;
}

export interface NavigationItem {
  id: string;
  label: string;
  icon?: ReactNode;
  path?: string;
  badge?: number;
  disabled?: boolean;
}

export interface MobileHeaderProps {
  /** Header title */
  title?: string;
  /** Show back button */
  showBack?: boolean;
  /** Back button handler */
  onBack?: () => void;
  /** Left side content */
  leftContent?: ReactNode;
  /** Right side content */
  rightContent?: ReactNode;
  /** Custom CSS classes */
  className?: string;
  /** Header background color */
  backgroundColor?: string;
  /** Text color */
  textColor?: string;
}

export interface TouchOptimizedButtonProps {
  children: ReactNode;
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  /** Button size optimized for touch */
  size?: 'small' | 'medium' | 'large';
  /** Disabled state */
  disabled?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Full width */
  fullWidth?: boolean;
  /** Touch ripple effect */
  ripple?: boolean;
  /** Haptic feedback */
  haptic?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Custom CSS classes */
  className?: string;
}

export interface SwipeGestureProps {
  children: ReactNode;
  /** Enable left swipe */
  enableLeft?: boolean;
  /** Enable right swipe */
  enableRight?: boolean;
  /** Enable up swipe */
  enableUp?: boolean;
  /** Enable down swipe */
  enableDown?: boolean;
  /** Minimum swipe distance */
  threshold?: number;
  /** Velocity threshold */
  velocity?: number;
  /** Swipe handlers */
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  /** Custom CSS classes */
  className?: string;
}

export interface PullToRefreshProps {
  children: ReactNode;
  /** Refresh handler */
  onRefresh: () => Promise<void>;
  /** Pull threshold */
  threshold?: number;
  /** Custom loading indicator */
  loadingIndicator?: ReactNode;
  /** Custom CSS classes */
  className?: string;
  /** Disabled state */
  disabled?: boolean;
}
