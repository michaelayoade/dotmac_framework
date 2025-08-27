/**
 * UI Components Index
 * Re-export all reusable UI components
 */

// Basic UI Components
export { Button, buttonVariants } from './Button';
export type { ButtonProps } from './Button';

export { Input } from './Input';
export type { InputProps } from './Input';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent } from './Card';
export type { CardProps } from './Card';

export { Alert, AlertDescription, AlertTitle } from './Alert';
export type { AlertProps } from './Alert';

export { Badge, badgeVariants } from './Badge';
export type { BadgeProps } from './Badge';

export { Tabs, TabsList, TabsTrigger, TabsContent } from './Tabs';

export { LoadingSpinner } from './LoadingSpinner';
export type { LoadingSpinnerProps } from './LoadingSpinner';

export { DataTable } from './DataTable';
export type { 
  DataTableProps, 
  TableColumn, 
  TableData,
  SortDirection 
} from './DataTable';

export { 
  Modal, 
  ConfirmModal, 
  AlertModal, 
  FormModal,
  useModal 
} from './Modal';
export type { ModalSize, ModalVariant } from './Modal';

export {
  Skeleton,
  TextSkeleton,
  AvatarSkeleton,
  CardSkeleton,
  TableSkeleton,
  ListSkeleton,
  StatsSkeleton,
  FormSkeleton,
  ChartSkeleton,
  PageSkeleton
} from './LoadingSkeletons';

// Re-export layout components
export {
  useBreakpoint,
  Container,
  Grid,
  GridItem,
  Flex,
  Stack,
  MobileNav,
  MobileHeader,
  ShowOnMobile,
  HideOnMobile,
  ShowOnTablet,
  ShowOnDesktop,
  ResponsiveText,
  ResponsiveCard,
  AppShell
} from '../layout/ResponsiveLayout';

// Re-export feedback components
export {
  ToastProvider,
  useToast,
  useToastActions
} from './Toast';
export type { Toast, ToastType, ToastPosition } from './Toast';

export {
  NotificationProvider,
  NotificationDropdown,
  NotificationPanel,
  useNotifications
} from './Notifications';
export type { 
  Notification, 
  NotificationType, 
  NotificationPriority 
} from './Notifications';

// Re-export keyboard navigation
export {
  KeyboardNavigationProvider,
  KeyboardShortcutDisplay,
  KeyboardShortcutsHelp,
  FocusTrap,
  useKeyboardNavigationContext
} from './KeyboardNavigationProvider';

// Re-export keyboard navigation hooks
export {
  useFocusManagement,
  useKeyboardShortcuts,
  useEscapeKey,
  useEnterKey,
  useGridNavigation,
  useRovingTabIndex,
  useMenuNavigation
} from '../hooks/useKeyboardNavigation';
export type { 
  KeyboardNavigationOptions,
  KeyboardShortcut
} from '../hooks/useKeyboardNavigation';

// Re-export accessibility components
export {
  AccessibilityProvider,
  AccessibilityPanel,
  AccessibilityChecker,
  useAccessibility
} from '../accessibility';
export type {
  AccessibilitySettings,
  AccessibilityContextValue,
  AccessibilityViolation,
  AccessibilityReport
} from '../accessibility';