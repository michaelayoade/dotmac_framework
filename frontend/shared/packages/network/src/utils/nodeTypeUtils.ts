import { NodeType } from '../types';

// Color mappings for node types
export const NODE_TYPE_COLORS: Record<NodeType, string> = {
  [NodeType.CORE_ROUTER]: '#1f77b4',
  [NodeType.DISTRIBUTION_ROUTER]: '#ff7f0e',
  [NodeType.ACCESS_SWITCH]: '#2ca02c',
  [NodeType.WIFI_AP]: '#d62728',
  [NodeType.CELL_TOWER]: '#9467bd',
  [NodeType.FIBER_SPLICE]: '#8c564b',
  [NodeType.POP]: '#e377c2',
  [NodeType.CUSTOMER_PREMISES]: '#7f7f7f',
  [NodeType.DATA_CENTER]: '#bcbd22',
};

// Size mappings for different node types
export const NODE_TYPE_SIZES: Record<NodeType, number> = {
  [NodeType.CORE_ROUTER]: 40,
  [NodeType.DISTRIBUTION_ROUTER]: 35,
  [NodeType.ACCESS_SWITCH]: 30,
  [NodeType.WIFI_AP]: 25,
  [NodeType.CELL_TOWER]: 35,
  [NodeType.FIBER_SPLICE]: 20,
  [NodeType.POP]: 45,
  [NodeType.CUSTOMER_PREMISES]: 25,
  [NodeType.DATA_CENTER]: 50,
};

// Icon mappings for node types (using unicode symbols for now)
export const NODE_TYPE_ICONS: Record<NodeType, string> = {
  [NodeType.CORE_ROUTER]: '⚡',
  [NodeType.DISTRIBUTION_ROUTER]: '🔗',
  [NodeType.ACCESS_SWITCH]: '⚪',
  [NodeType.WIFI_AP]: '📶',
  [NodeType.CELL_TOWER]: '📡',
  [NodeType.FIBER_SPLICE]: '🔌',
  [NodeType.POP]: '🏢',
  [NodeType.CUSTOMER_PREMISES]: '🏠',
  [NodeType.DATA_CENTER]: '🏛️',
};

// CSS class mappings for styling
export const NODE_TYPE_CSS_CLASSES: Record<NodeType, string> = {
  [NodeType.CORE_ROUTER]: 'border-blue-600 bg-blue-50',
  [NodeType.DISTRIBUTION_ROUTER]: 'border-orange-600 bg-orange-50',
  [NodeType.ACCESS_SWITCH]: 'border-green-600 bg-green-50',
  [NodeType.WIFI_AP]: 'border-red-600 bg-red-50',
  [NodeType.CELL_TOWER]: 'border-purple-600 bg-purple-50',
  [NodeType.FIBER_SPLICE]: 'border-amber-600 bg-amber-50',
  [NodeType.POP]: 'border-pink-600 bg-pink-50',
  [NodeType.CUSTOMER_PREMISES]: 'border-gray-600 bg-gray-50',
  [NodeType.DATA_CENTER]: 'border-teal-600 bg-teal-50',
};

export const getNodeTypeColor = (type: NodeType): string => {
  return NODE_TYPE_COLORS[type] || NODE_TYPE_COLORS[NodeType.ACCESS_SWITCH];
};

export const getNodeTypeSize = (type: NodeType): number => {
  return NODE_TYPE_SIZES[type] || NODE_TYPE_SIZES[NodeType.ACCESS_SWITCH];
};

export const getNodeTypeIcon = (type: NodeType): string => {
  return NODE_TYPE_ICONS[type] || NODE_TYPE_ICONS[NodeType.ACCESS_SWITCH];
};

export const getNodeTypeCssClass = (type: NodeType): string => {
  return NODE_TYPE_CSS_CLASSES[type] || NODE_TYPE_CSS_CLASSES[NodeType.ACCESS_SWITCH];
};

export const getNodeDisplayName = (type: NodeType): string => {
  const displayNames: Record<NodeType, string> = {
    [NodeType.CORE_ROUTER]: 'Core Router',
    [NodeType.DISTRIBUTION_ROUTER]: 'Distribution Router',
    [NodeType.ACCESS_SWITCH]: 'Access Switch',
    [NodeType.WIFI_AP]: 'WiFi Access Point',
    [NodeType.CELL_TOWER]: 'Cell Tower',
    [NodeType.FIBER_SPLICE]: 'Fiber Splice',
    [NodeType.POP]: 'Point of Presence',
    [NodeType.CUSTOMER_PREMISES]: 'Customer Premises',
    [NodeType.DATA_CENTER]: 'Data Center',
  };

  return displayNames[type] || type.replace(/_/g, ' ');
};
