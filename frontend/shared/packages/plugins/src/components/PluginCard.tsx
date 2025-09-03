import React, { useState } from 'react';
import { Button, Card } from '@dotmac/primitives';
import {
  Power,
  PowerOff,
  RotateCw,
  Settings,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { PluginCardProps, PluginStatus } from '../types';

export const PluginCard: React.FC<PluginCardProps> = ({
  plugin,
  showActions = true,
  showHealth = true,
  selected,
  onSelect,
  onEnable,
  onDisable,
  onRestart,
  onConfigure,
}) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleAction = async (action: string, handler: () => Promise<void>) => {
    try {
      setActionLoading(action);
      await handler();
    } catch (err) {
      console.error(`Action ${action} failed:`, err);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusIcon = (status: PluginStatus) => {
    switch (status) {
      case 'active':
        return <CheckCircle className='h-4 w-4 text-green-600' />;
      case 'error':
        return <AlertTriangle className='h-4 w-4 text-red-600' />;
      case 'initializing':
      case 'updating':
        return <Clock className='h-4 w-4 text-yellow-600 animate-pulse' />;
      default:
        return <Power className='h-4 w-4 text-gray-600' />;
    }
  };

  const getStatusBadgeClass = (status: PluginStatus) => {
    const baseClass = 'px-2 py-1 text-xs font-medium rounded-full';

    switch (status) {
      case 'active':
        return `${baseClass} bg-green-100 text-green-800`;
      case 'inactive':
        return `${baseClass} bg-gray-100 text-gray-800`;
      case 'error':
        return `${baseClass} bg-red-100 text-red-800`;
      case 'initializing':
      case 'updating':
        return `${baseClass} bg-yellow-100 text-yellow-800`;
      case 'disabled':
        return `${baseClass} bg-gray-100 text-gray-600`;
      default:
        return `${baseClass} bg-gray-100 text-gray-800`;
    }
  };

  const pluginKey = `${plugin.metadata.domain}.${plugin.metadata.name}`;

  return (
    <Card className='plugin-card overflow-hidden'>
      {/* Header */}
      <div className='p-4 border-b border-gray-100'>
        <div className='flex items-start justify-between'>
          <div className='flex-1'>
            <div className='flex items-center gap-2'>
              {onSelect && (
                <input
                  type='checkbox'
                  checked={selected || false}
                  onChange={(e) => onSelect(e.target.checked)}
                  className='rounded'
                />
              )}

              <div className='flex items-center gap-2'>
                {getStatusIcon(plugin.status)}
                <h3 className='font-semibold text-gray-900'>{plugin.metadata.name}</h3>
              </div>
            </div>

            <div className='mt-1 flex items-center gap-2'>
              <span className='text-sm text-gray-500'>{plugin.metadata.domain}</span>
              <span className='text-gray-300'>•</span>
              <span className='text-sm text-gray-500'>v{plugin.metadata.version}</span>
            </div>

            {plugin.metadata.description && (
              <p className='mt-2 text-sm text-gray-600 line-clamp-2'>
                {plugin.metadata.description}
              </p>
            )}
          </div>

          <div className={getStatusBadgeClass(plugin.status)}>{plugin.status}</div>
        </div>
      </div>

      {/* Health Information */}
      {showHealth && (
        <div className='px-4 py-3 bg-gray-50'>
          <div className='grid grid-cols-2 gap-4 text-sm'>
            <div className='flex items-center gap-2'>
              <Activity className='h-3 w-3 text-gray-400' />
              <span className='text-gray-600'>Health</span>
              <span className={`font-medium ${plugin.healthy ? 'text-green-600' : 'text-red-600'}`}>
                {plugin.healthy ? 'Healthy' : 'Unhealthy'}
              </span>
            </div>

            <div className='text-right'>
              <span className='text-gray-600'>Errors: </span>
              <span
                className={`font-medium ${plugin.error_count > 0 ? 'text-red-600' : 'text-green-600'}`}
              >
                {plugin.error_count}
              </span>
            </div>

            {plugin.uptime && (
              <div className='col-span-2'>
                <span className='text-gray-600'>Uptime: </span>
                <span className='font-medium text-gray-800'>
                  {Math.round(plugin.uptime / 60)} min
                </span>
              </div>
            )}

            {plugin.last_activity && (
              <div className='col-span-2'>
                <span className='text-gray-600'>Last activity: </span>
                <span className='font-medium text-gray-800'>
                  {formatDistanceToNow(new Date(plugin.last_activity), { addSuffix: true })}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tags and Categories */}
      {(plugin.metadata.tags.length > 0 || plugin.metadata.categories.length > 0) && (
        <div className='px-4 py-3'>
          {plugin.metadata.categories.length > 0 && (
            <div className='mb-2'>
              <span className='text-xs text-gray-500 uppercase tracking-wide'>Categories</span>
              <div className='flex flex-wrap gap-1 mt-1'>
                {plugin.metadata.categories.slice(0, 3).map((category) => (
                  <span
                    key={category}
                    className='px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded'
                  >
                    {category}
                  </span>
                ))}
                {plugin.metadata.categories.length > 3 && (
                  <span className='px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded'>
                    +{plugin.metadata.categories.length - 3}
                  </span>
                )}
              </div>
            </div>
          )}

          {plugin.metadata.tags.length > 0 && (
            <div>
              <span className='text-xs text-gray-500 uppercase tracking-wide'>Tags</span>
              <div className='flex flex-wrap gap-1 mt-1'>
                {plugin.metadata.tags.slice(0, 4).map((tag) => (
                  <span key={tag} className='px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded'>
                    {tag}
                  </span>
                ))}
                {plugin.metadata.tags.length > 4 && (
                  <span className='px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded'>
                    +{plugin.metadata.tags.length - 4}
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {showActions && (
        <div className='p-4 border-t border-gray-100 bg-white'>
          <div className='flex items-center gap-2'>
            {plugin.is_active ? (
              <Button
                variant='outline'
                size='sm'
                onClick={() => onDisable && handleAction('disable', () => onDisable(pluginKey))}
                disabled={actionLoading === 'disable'}
              >
                {actionLoading === 'disable' ? (
                  <Clock className='h-3 w-3 animate-spin' />
                ) : (
                  <PowerOff className='h-3 w-3' />
                )}
                Disable
              </Button>
            ) : (
              <Button
                variant='outline'
                size='sm'
                onClick={() => onEnable && handleAction('enable', () => onEnable(pluginKey))}
                disabled={actionLoading === 'enable'}
              >
                {actionLoading === 'enable' ? (
                  <Clock className='h-3 w-3 animate-spin' />
                ) : (
                  <Power className='h-3 w-3' />
                )}
                Enable
              </Button>
            )}

            <Button
              variant='outline'
              size='sm'
              onClick={() => onRestart && handleAction('restart', () => onRestart(pluginKey))}
              disabled={actionLoading === 'restart'}
            >
              {actionLoading === 'restart' ? (
                <Clock className='h-3 w-3 animate-spin' />
              ) : (
                <RotateCw className='h-3 w-3' />
              )}
              Restart
            </Button>

            <Button
              variant='outline'
              size='sm'
              onClick={() => onConfigure && onConfigure(pluginKey)}
            >
              <Settings className='h-3 w-3' />
              Configure
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
};
