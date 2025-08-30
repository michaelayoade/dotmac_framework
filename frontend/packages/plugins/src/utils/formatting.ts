import { formatDistanceToNow, format } from 'date-fns';
import type { PluginStatus, Plugin, PluginMarketplaceItem } from '../types';

export function formatPluginStatus(status: PluginStatus): string {
  const statusLabels: Record<PluginStatus, string> = {
    [PluginStatus.UNINITIALIZED]: 'Uninitialized',
    [PluginStatus.INITIALIZING]: 'Initializing...',
    [PluginStatus.ACTIVE]: 'Active',
    [PluginStatus.INACTIVE]: 'Inactive',
    [PluginStatus.ERROR]: 'Error',
    [PluginStatus.DISABLED]: 'Disabled',
    [PluginStatus.UPDATING]: 'Updating...'
  };

  return statusLabels[status] || status;
}

export function formatPluginKey(domain: string, name: string): string {
  return `${domain}.${name}`;
}

export function parsePluginKey(pluginKey: string): { domain: string; name: string } {
  const parts = pluginKey.split('.');
  if (parts.length < 2) {
    throw new Error(`Invalid plugin key format: ${pluginKey}`);
  }

  const name = parts.pop()!;
  const domain = parts.join('.');

  return { domain, name };
}

export function formatPluginVersion(version: string, includePrefix = true): string {
  const prefix = includePrefix ? 'v' : '';
  return `${prefix}${version}`;
}

export function formatPluginUptime(uptimeSeconds?: number): string {
  if (!uptimeSeconds || uptimeSeconds <= 0) {
    return 'N/A';
  }

  const hours = Math.floor(uptimeSeconds / 3600);
  const minutes = Math.floor((uptimeSeconds % 3600) / 60);
  const seconds = Math.floor(uptimeSeconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
}

export function formatPluginSize(sizeInBytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = sizeInBytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

export function formatDownloadCount(count: number): string {
  if (count >= 1000000) {
    return `${(count / 1000000).toFixed(1)}M`;
  } else if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
}

export function formatPluginRating(rating: number, showStars = false): string {
  const roundedRating = Math.round(rating * 10) / 10;

  if (showStars) {
    const fullStars = Math.floor(roundedRating);
    const hasHalfStar = roundedRating - fullStars >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    return '★'.repeat(fullStars) +
           (hasHalfStar ? '½' : '') +
           '☆'.repeat(emptyStars) +
           ` (${roundedRating})`;
  }

  return roundedRating.toFixed(1);
}

export function formatLastActivity(lastActivity?: string): string {
  if (!lastActivity) {
    return 'Never';
  }

  try {
    return formatDistanceToNow(new Date(lastActivity), { addSuffix: true });
  } catch {
    return 'Unknown';
  }
}

export function formatPluginDescription(description?: string, maxLength = 100): string {
  if (!description) {
    return 'No description provided';
  }

  if (description.length <= maxLength) {
    return description;
  }

  return description.substring(0, maxLength - 3) + '...';
}

export function formatPluginTags(tags: string[], maxTags = 3, showCount = true): string {
  if (tags.length === 0) {
    return 'No tags';
  }

  const displayTags = tags.slice(0, maxTags);
  const remainingCount = tags.length - maxTags;

  let result = displayTags.join(', ');

  if (remainingCount > 0 && showCount) {
    result += ` (+${remainingCount} more)`;
  }

  return result;
}

export function formatPluginCategories(categories: string[], maxCategories = 2): string {
  if (categories.length === 0) {
    return 'Uncategorized';
  }

  const displayCategories = categories.slice(0, maxCategories);
  const remainingCount = categories.length - maxCategories;

  let result = displayCategories
    .map(cat => cat.charAt(0).toUpperCase() + cat.slice(1))
    .join(', ');

  if (remainingCount > 0) {
    result += ` (+${remainingCount})`;
  }

  return result;
}

export function formatDependencies(dependencies: string[], maxDeps = 3): string {
  if (dependencies.length === 0) {
    return 'No dependencies';
  }

  const displayDeps = dependencies.slice(0, maxDeps);
  const remainingCount = dependencies.length - maxDeps;

  let result = displayDeps.join(', ');

  if (remainingCount > 0) {
    result += ` (+${remainingCount} more)`;
  }

  return result;
}

export function formatPluginError(error: Error | string): string {
  if (typeof error === 'string') {
    return error;
  }

  return error.message || 'Unknown error occurred';
}

export function formatInstallationDate(dateString: string): string {
  try {
    return format(new Date(dateString), 'MMM dd, yyyy');
  } catch {
    return 'Unknown date';
  }
}

export function formatPluginPrice(price?: number, currency = 'USD'): string {
  if (!price || price === 0) {
    return 'Free';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2
  }).format(price);
}

export function formatMarketplaceItemSummary(item: PluginMarketplaceItem): string {
  const parts = [
    item.display_name,
    `v${item.version}`,
    `by ${item.author}`,
    formatPluginRating(item.rating) + ' stars'
  ];

  if (item.pricing_model !== 'free') {
    parts.push(formatPluginPrice(item.price));
  }

  return parts.join(' • ');
}

export function formatPluginSummary(plugin: Plugin): string {
  const parts = [
    plugin.metadata.name,
    formatPluginVersion(plugin.metadata.version),
    formatPluginStatus(plugin.status)
  ];

  if (plugin.uptime) {
    parts.push(`uptime: ${formatPluginUptime(plugin.uptime)}`);
  }

  return parts.join(' • ');
}

export function formatHealthScore(healthy: number, total: number): string {
  if (total === 0) {
    return 'N/A';
  }

  const percentage = Math.round((healthy / total) * 100);
  return `${percentage}% (${healthy}/${total})`;
}

export function formatConfigValue(value: any): string {
  if (value === null || value === undefined) {
    return 'Not set';
  }

  if (typeof value === 'boolean') {
    return value ? 'Enabled' : 'Disabled';
  }

  if (typeof value === 'string') {
    // Mask potential sensitive values
    if (value.toLowerCase().includes('password') ||
        value.toLowerCase().includes('secret') ||
        value.toLowerCase().includes('key')) {
      return '***hidden***';
    }

    if (value.length > 50) {
      return value.substring(0, 47) + '...';
    }

    return value;
  }

  if (typeof value === 'number') {
    return value.toLocaleString();
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return 'Empty array';
    }
    return `Array (${value.length} items)`;
  }

  if (typeof value === 'object') {
    const keys = Object.keys(value);
    if (keys.length === 0) {
      return 'Empty object';
    }
    return `Object (${keys.length} properties)`;
  }

  return String(value);
}

export function formatValidationErrors(errors: string[]): string {
  if (errors.length === 0) {
    return 'No errors';
  }

  if (errors.length === 1) {
    return errors[0];
  }

  return `${errors.length} errors: ${errors.join('; ')}`;
}

export function formatValidationWarnings(warnings: string[]): string {
  if (warnings.length === 0) {
    return 'No warnings';
  }

  if (warnings.length === 1) {
    return warnings[0];
  }

  return `${warnings.length} warnings: ${warnings.join('; ')}`;
}

// Utility function to create CSS classes for plugin status
export function getPluginStatusClasses(status: PluginStatus): string {
  const baseClasses = 'px-2 py-1 text-xs font-medium rounded-full';

  const statusClasses: Record<PluginStatus, string> = {
    [PluginStatus.ACTIVE]: 'bg-green-100 text-green-800',
    [PluginStatus.INACTIVE]: 'bg-gray-100 text-gray-800',
    [PluginStatus.ERROR]: 'bg-red-100 text-red-800',
    [PluginStatus.INITIALIZING]: 'bg-yellow-100 text-yellow-800',
    [PluginStatus.UPDATING]: 'bg-blue-100 text-blue-800',
    [PluginStatus.DISABLED]: 'bg-gray-100 text-gray-600',
    [PluginStatus.UNINITIALIZED]: 'bg-gray-100 text-gray-500'
  };

  return `${baseClasses} ${statusClasses[status] || statusClasses[PluginStatus.UNINITIALIZED]}`;
}
