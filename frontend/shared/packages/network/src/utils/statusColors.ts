import { NodeStatus } from '../types';

// Hex color mappings for status
export const STATUS_COLORS: Record<NodeStatus, string> = {
  [NodeStatus.ACTIVE]: '#28a745',
  [NodeStatus.INACTIVE]: '#dc3545',
  [NodeStatus.MAINTENANCE]: '#ffc107',
  [NodeStatus.FAILED]: '#dc3545',
  [NodeStatus.UNKNOWN]: '#6c757d',
};

// CSS class mappings for status
export const STATUS_CSS_CLASSES: Record<NodeStatus, string> = {
  [NodeStatus.ACTIVE]: 'text-green-600 bg-green-100',
  [NodeStatus.INACTIVE]: 'text-red-600 bg-red-100',
  [NodeStatus.MAINTENANCE]: 'text-yellow-600 bg-yellow-100',
  [NodeStatus.FAILED]: 'text-red-600 bg-red-100',
  [NodeStatus.UNKNOWN]: 'text-gray-600 bg-gray-100',
};

// Tailwind color classes for borders/backgrounds
export const STATUS_BORDER_CLASSES: Record<NodeStatus, string> = {
  [NodeStatus.ACTIVE]: 'border-green-500',
  [NodeStatus.INACTIVE]: 'border-red-500',
  [NodeStatus.MAINTENANCE]: 'border-yellow-500',
  [NodeStatus.FAILED]: 'border-red-500',
  [NodeStatus.UNKNOWN]: 'border-gray-500',
};

export const getStatusColor = (status: NodeStatus): string => {
  return STATUS_COLORS[status] || STATUS_COLORS[NodeStatus.UNKNOWN];
};

export const getStatusCssClass = (status: NodeStatus): string => {
  return STATUS_CSS_CLASSES[status] || STATUS_CSS_CLASSES[NodeStatus.UNKNOWN];
};

export const getStatusBorderClass = (status: NodeStatus): string => {
  return STATUS_BORDER_CLASSES[status] || STATUS_BORDER_CLASSES[NodeStatus.UNKNOWN];
};
