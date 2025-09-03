import React from 'react';

interface FilterTab {
  key: string;
  label: string;
  count?: number;
}

interface PanelHeaderProps {
  title: string;
  icon: React.ReactNode;
  count?: number;
  filters?: FilterTab[];
  activeFilter?: string;
  onFilterChange?: (filter: string) => void;
  actions?: React.ReactNode;
  className?: string;
}

export const PanelHeader: React.FC<PanelHeaderProps> = ({
  title,
  icon,
  count,
  filters,
  activeFilter,
  onFilterChange,
  actions,
  className = '',
}) => {
  return (
    <div className={`border-b border-gray-200 pb-4 ${className}`}>
      {/* Header row */}
      <div className='flex items-center justify-between mb-3'>
        <div className='flex items-center space-x-2'>
          {icon}
          <h3 className='text-lg font-semibold text-gray-900'>{title}</h3>
          {typeof count === 'number' && (
            <span className='inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800'>
              {count}
            </span>
          )}
        </div>
        {actions && <div className='flex items-center space-x-2'>{actions}</div>}
      </div>

      {/* Filter tabs */}
      {filters && filters.length > 0 && (
        <div className='flex space-x-1'>
          {filters.map((filter) => (
            <button
              key={filter.key}
              onClick={() => onFilterChange?.(filter.key)}
              className={`px-3 py-1 text-sm font-medium rounded-md transition-colors ${
                activeFilter === filter.key
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {filter.label}
              {typeof filter.count === 'number' && (
                <span className='ml-1 text-xs'>({filter.count})</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
