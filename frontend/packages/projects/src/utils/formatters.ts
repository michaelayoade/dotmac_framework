import { format, formatDistanceToNow, isToday, isYesterday, isTomorrow } from 'date-fns';

export const dateFormatters = {
  formatDate(date: string | Date, formatString: string = 'MMM dd, yyyy'): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return format(dateObj, formatString);
  },

  formatDateTime(date: string | Date, formatString: string = 'MMM dd, yyyy HH:mm'): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return format(dateObj, formatString);
  },

  formatRelativeTime(date: string | Date): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return formatDistanceToNow(dateObj, { addSuffix: true });
  },

  formatSmartDate(date: string | Date): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;

    if (isToday(dateObj)) {
      return `Today ${format(dateObj, 'HH:mm')}`;
    } else if (isYesterday(dateObj)) {
      return `Yesterday ${format(dateObj, 'HH:mm')}`;
    } else if (isTomorrow(dateObj)) {
      return `Tomorrow ${format(dateObj, 'HH:mm')}`;
    } else {
      return format(dateObj, 'MMM dd, HH:mm');
    }
  },

  formatDateRange(startDate: string | Date, endDate: string | Date): string {
    const start = typeof startDate === 'string' ? new Date(startDate) : startDate;
    const end = typeof endDate === 'string' ? new Date(endDate) : endDate;

    const startYear = start.getFullYear();
    const endYear = end.getFullYear();
    const startMonth = start.getMonth();
    const endMonth = end.getMonth();

    if (startYear !== endYear) {
      return `${format(start, 'MMM dd, yyyy')} - ${format(end, 'MMM dd, yyyy')}`;
    } else if (startMonth !== endMonth) {
      return `${format(start, 'MMM dd')} - ${format(end, 'MMM dd, yyyy')}`;
    } else {
      return `${format(start, 'MMM dd')} - ${format(end, 'dd, yyyy')}`;
    }
  },

  formatDuration(minutes: number): string {
    if (minutes < 60) {
      return `${minutes}m`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    if (remainingMinutes === 0) {
      return `${hours}h`;
    }

    return `${hours}h ${remainingMinutes}m`;
  },

  formatLongDuration(minutes: number): string {
    const days = Math.floor(minutes / (24 * 60));
    const hours = Math.floor((minutes % (24 * 60)) / 60);
    const mins = minutes % 60;

    const parts: string[] = [];

    if (days > 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`);
    if (hours > 0) parts.push(`${hours} hour${hours !== 1 ? 's' : ''}`);
    if (mins > 0 && days === 0) parts.push(`${mins} minute${mins !== 1 ? 's' : ''}`);

    if (parts.length === 0) return '0 minutes';
    if (parts.length === 1) return parts[0];
    if (parts.length === 2) return parts.join(' and ');

    return parts.slice(0, -1).join(', ') + ', and ' + parts[parts.length - 1];
  }
};

export const statusFormatters = {
  formatProjectStatus(status: string): string {
    return status
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  },

  formatTaskStatus(status: string): string {
    const statusMap: Record<string, string> = {
      'todo': 'To Do',
      'in_progress': 'In Progress',
      'review': 'In Review',
      'done': 'Done',
      'blocked': 'Blocked',
      'cancelled': 'Cancelled'
    };

    return statusMap[status] || status;
  },

  formatPriority(priority: string): string {
    return priority.charAt(0).toUpperCase() + priority.slice(1);
  },

  getStatusColor(status: string, type: 'project' | 'task' | 'milestone' = 'project'): string {
    const colors: Record<string, Record<string, string>> = {
      project: {
        'planning': 'gray',
        'approved': 'blue',
        'scheduled': 'purple',
        'in_progress': 'yellow',
        'on_hold': 'orange',
        'testing': 'blue',
        'completed': 'green',
        'cancelled': 'red',
        'failed': 'red'
      },
      task: {
        'todo': 'gray',
        'in_progress': 'yellow',
        'review': 'blue',
        'done': 'green',
        'blocked': 'red',
        'cancelled': 'gray'
      },
      milestone: {
        'not_started': 'gray',
        'in_progress': 'yellow',
        'completed': 'green',
        'overdue': 'red'
      }
    };

    return colors[type]?.[status] || 'gray';
  },

  getPriorityColor(priority: string): string {
    const colors: Record<string, string> = {
      'low': 'gray',
      'medium': 'blue',
      'high': 'yellow',
      'urgent': 'orange',
      'critical': 'red'
    };

    return colors[priority] || 'gray';
  }
};

export const numberFormatters = {
  formatCurrency(amount: number, currency: string = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  },

  formatNumber(value: number, decimals: number = 0): string {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value);
  },

  formatPercentage(value: number, decimals: number = 0): string {
    return `${this.formatNumber(value, decimals)}%`;
  },

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  },

  formatCompactNumber(value: number): string {
    if (value < 1000) return value.toString();
    if (value < 1000000) return `${Math.round(value / 100) / 10}K`;
    if (value < 1000000000) return `${Math.round(value / 100000) / 10}M`;
    return `${Math.round(value / 100000000) / 10}B`;
  }
};

export const textFormatters = {
  truncate(text: string, maxLength: number = 100, suffix: string = '...'): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - suffix.length) + suffix;
  },

  initials(name: string): string {
    return name
      .split(' ')
      .map(word => word.charAt(0).toUpperCase())
      .join('')
      .substring(0, 2);
  },

  slug(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
  },

  capitalize(text: string): string {
    return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
  },

  title(text: string): string {
    return text
      .split(' ')
      .map(word => this.capitalize(word))
      .join(' ');
  },

  camelToTitle(camelCase: string): string {
    return camelCase
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, str => str.toUpperCase())
      .trim();
  }
};

export const projectFormatters = {
  formatProjectNumber(projectNumber: string): string {
    return projectNumber.toUpperCase();
  },

  formatProjectHealth(score: number): {
    label: string;
    color: string;
    description: string;
  } {
    if (score >= 90) {
      return {
        label: 'Excellent',
        color: 'green',
        description: 'Project is on track and performing well'
      };
    } else if (score >= 70) {
      return {
        label: 'Good',
        color: 'blue',
        description: 'Project is performing adequately with minor issues'
      };
    } else if (score >= 50) {
      return {
        label: 'Warning',
        color: 'yellow',
        description: 'Project has some issues that need attention'
      };
    } else {
      return {
        label: 'Critical',
        color: 'red',
        description: 'Project has significant issues requiring immediate action'
      };
    }
  },

  formatTaskComplexity(level: string): {
    label: string;
    color: string;
    icon: string;
  } {
    const complexityMap: Record<string, { label: string; color: string; icon: string }> = {
      'simple': {
        label: 'Simple',
        color: 'green',
        icon: '●'
      },
      'moderate': {
        label: 'Moderate',
        color: 'blue',
        icon: '●●'
      },
      'complex': {
        label: 'Complex',
        color: 'yellow',
        icon: '●●●'
      },
      'very_complex': {
        label: 'Very Complex',
        color: 'red',
        icon: '●●●●'
      }
    };

    return complexityMap[level] || complexityMap['simple'];
  }
};

export const chartFormatters = {
  formatChartData(data: Record<string, number>, labelFormatter?: (key: string) => string): Array<{
    name: string;
    value: number;
    percentage: number;
  }> {
    const total = Object.values(data).reduce((sum, value) => sum + value, 0);

    return Object.entries(data).map(([key, value]) => ({
      name: labelFormatter ? labelFormatter(key) : textFormatters.title(key.replace(/_/g, ' ')),
      value,
      percentage: total > 0 ? Math.round((value / total) * 100) : 0
    }));
  },

  formatTimeSeriesData(entries: Array<{ date: string; value: number }>): Array<{
    date: string;
    value: number;
    formattedDate: string;
  }> {
    return entries.map(entry => ({
      ...entry,
      formattedDate: dateFormatters.formatDate(entry.date, 'MMM dd')
    }));
  }
};

export default {
  date: dateFormatters,
  status: statusFormatters,
  number: numberFormatters,
  text: textFormatters,
  project: projectFormatters,
  chart: chartFormatters
};
