/**
 * Reseller Portal Styled Components
 *
 * Professional, brandable components optimized for partner/reseller
 * interfaces. Balances business aesthetics with customization flexibility.
 */

// Re-export primitives with reseller theme context
export {
  Alert,
  AlertDescription,
  AlertTitle,
  ARIA_ROLES,
  AreaChart,
  BarChart,
  BottomSheet,
  Breadcrumb,
  BreadcrumbEllipsis,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  Center,
  ChartContainer,
  Checkbox,
  ConfirmationModal,
  // Layout Components
  Container,
  chartUtils,
  createValidationRules,
  Dashboard,
  // Table Components
  DataTable,
  Divider,
  Drawer,
  // Form Components
  Form,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormModal,
  Grid,
  GridItem,
  HStack,
  // Utility Functions
  isBrowser,
  isServer,
  KEYS,
  // Chart Components
  LineChart,
  Loading,
  LoadingSkeleton,
  MetricCard,
  // Modal Components
  Modal,
  ModalBody,
  ModalClose,
  ModalContent,
  ModalDescription,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  ModalPortal,
  ModalProvider,
  ModalTitle,
  ModalTrigger,
  Navbar,
  NavigationItem,
  NavigationLink,
  NavigationMenu,
  // Navigation Components
  NavigationProvider,
  PieChart,
  Progress,
  Radio,
  RadioGroup,
  Section,
  Select,
  Sidebar,
  Spacer,
  Stack,
  StatusIndicator,
  TabItem,
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
  TabNavigation,
  Textarea,
  Toast,
  ToastAction,
  ToastClose,
  ToastContent,
  ToastDescription,
  // Feedback Components
  ToastProvider,
  ToastTitle,
  ToastViewport,
  useAriaExpanded,
  useAriaSelection,
  useClientEffect,
  useFocusTrap,
  useFormContext,
  useId,
  useIsHydrated,
  useKeyboardNavigation,
  useLocalStorage,
  useMediaQuery,
  useModal,
  useModalContext,
  useNavigation,
  usePrefersReducedMotion,
  useScreenReaderAnnouncement,
  useSessionStorage,
  useToast,
  useUserPreferences,
  VStack,
  validationPatterns,
} from '@dotmac/primitives';
// Theme utilities
export { cn, createPortalTheme } from '../lib/utils';
export type { ResellerButtonProps } from './Button';
// Button Components
export { ResellerButton, resellerButtonVariants } from './Button';
export type {
  ResellerCardContentProps,
  ResellerCardFooterProps,
  ResellerCardHeaderProps,
  ResellerCardProps,
} from './Card';
// Card Components
export {
  ResellerCard,
  ResellerCardContent,
  ResellerCardDescription,
  ResellerCardFooter,
  ResellerCardHeader,
  ResellerCardTitle,
} from './Card';
export type { ResellerInputProps } from './Input';
// Input Components
export { ResellerInput, resellerInputVariants } from './Input';

// Import the function explicitly for use
import { createPortalTheme } from '../lib/utils';

// Reseller theme instance
export const resellerTheme = createPortalTheme('reseller');
