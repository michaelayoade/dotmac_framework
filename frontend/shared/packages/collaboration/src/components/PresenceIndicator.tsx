import React from 'react';
import { User, Clock, Circle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import type { PresenceIndicatorProps, UserStatus } from '../types';

export const PresenceIndicator: React.FC<PresenceIndicatorProps> = ({
  users,
  current_user,
  max_avatars = 5,
  show_names = true,
  show_status = true,
  on_user_click,
}) => {
  const otherUsers = users.filter((u) => u.id !== current_user.id);
  const visibleUsers = otherUsers.slice(0, max_avatars);
  const hiddenCount = Math.max(0, otherUsers.length - max_avatars);

  const getStatusColor = (status: UserStatus): string => {
    const statusColors = {
      online: 'bg-green-500',
      away: 'bg-yellow-500',
      typing: 'bg-blue-500',
      idle: 'bg-gray-400',
      offline: 'bg-gray-300',
    };
    return statusColors[status] || statusColors.offline;
  };

  const getStatusText = (status: UserStatus): string => {
    const statusTexts = {
      online: 'Online',
      away: 'Away',
      typing: 'Typing...',
      idle: 'Idle',
      offline: 'Offline',
    };
    return statusTexts[status] || 'Unknown';
  };

  const getUserInitials = (name: string): string => {
    return name
      .split(' ')
      .map((word) => word.charAt(0).toUpperCase())
      .join('')
      .substring(0, 2);
  };

  if (otherUsers.length === 0) {
    return (
      <div className='presence-indicator flex items-center text-sm text-gray-500'>
        <User className='h-4 w-4 mr-1' />
        <span>Only you</span>
      </div>
    );
  }

  return (
    <div className='presence-indicator flex items-center gap-2'>
      {/* User avatars */}
      <div className='flex items-center -space-x-2'>
        {visibleUsers.map((user, index) => (
          <div
            key={user.id}
            className='relative group cursor-pointer'
            onClick={() => on_user_click?.(user)}
            style={{ zIndex: visibleUsers.length - index }}
          >
            {/* Avatar */}
            <div
              className='w-8 h-8 rounded-full border-2 border-white flex items-center justify-center text-xs font-medium text-white shadow-sm'
              style={{
                backgroundColor: user.color || '#3B82F6',
                borderColor: user.status === 'typing' ? '#EF4444' : '#ffffff',
              }}
            >
              {user.avatar ? (
                <img
                  src={user.avatar}
                  alt={user.name}
                  className='w-full h-full rounded-full object-cover'
                />
              ) : (
                getUserInitials(user.name)
              )}
            </div>

            {/* Status indicator */}
            {show_status && (
              <div
                className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white ${getStatusColor(user.status)}`}
              >
                {user.status === 'typing' && (
                  <div className='absolute inset-0 rounded-full bg-blue-500 animate-pulse' />
                )}
              </div>
            )}

            {/* Tooltip */}
            <div className='absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50'>
              <div className='bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-lg'>
                <div className='font-medium'>{user.name}</div>
                {show_status && (
                  <div className='text-gray-300 flex items-center gap-1'>
                    <Circle
                      className={`h-2 w-2 ${getStatusColor(user.status).replace('bg-', 'fill-')}`}
                    />
                    <span>{getStatusText(user.status)}</span>
                  </div>
                )}
                <div className='text-gray-400'>
                  Last seen {formatDistanceToNow(new Date(user.last_seen), { addSuffix: true })}
                </div>
                {/* Arrow */}
                <div className='absolute top-full left-1/2 transform -translate-x-1/2 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900' />
              </div>
            </div>
          </div>
        ))}

        {/* Additional users count */}
        {hiddenCount > 0 && (
          <div className='w-8 h-8 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center text-xs font-medium text-gray-600 shadow-sm'>
            +{hiddenCount}
          </div>
        )}
      </div>

      {/* Names and status text */}
      {show_names && (
        <div className='flex flex-col'>
          <div className='text-sm font-medium text-gray-900'>
            {otherUsers.length === 1 ? otherUsers[0].name : `${otherUsers.length} collaborators`}
          </div>

          {show_status && otherUsers.length === 1 && (
            <div className='flex items-center gap-1 text-xs text-gray-500'>
              <Circle
                className={`h-2 w-2 ${getStatusColor(otherUsers[0].status).replace('bg-', 'fill-')}`}
              />
              <span>{getStatusText(otherUsers[0].status)}</span>
            </div>
          )}
        </div>
      )}

      {/* Live activity indicators */}
      <div className='flex items-center gap-1'>
        {/* Typing indicators */}
        {otherUsers.some((u) => u.status === 'typing') && (
          <div className='flex items-center gap-1 text-xs text-blue-600'>
            <div className='flex gap-0.5'>
              <div
                className='w-1 h-1 bg-blue-600 rounded-full animate-bounce'
                style={{ animationDelay: '0ms' }}
              />
              <div
                className='w-1 h-1 bg-blue-600 rounded-full animate-bounce'
                style={{ animationDelay: '150ms' }}
              />
              <div
                className='w-1 h-1 bg-blue-600 rounded-full animate-bounce'
                style={{ animationDelay: '300ms' }}
              />
            </div>
            <span>typing...</span>
          </div>
        )}

        {/* Recent activity */}
        {otherUsers.some((u) => u.status === 'online') && (
          <div className='w-2 h-2 bg-green-500 rounded-full animate-pulse' />
        )}
      </div>
    </div>
  );
};
