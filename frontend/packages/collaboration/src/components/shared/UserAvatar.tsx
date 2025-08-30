import React from 'react';
import { UserStatus } from '../../types';

interface UserAvatarProps {
  user: {
    name: string;
    avatar?: string;
    id?: string;
  };
  size?: 'sm' | 'md' | 'lg';
  showStatus?: boolean;
  status?: UserStatus;
  className?: string;
}

const sizeClasses = {
  sm: 'h-6 w-6 text-xs',
  md: 'h-8 w-8 text-sm',
  lg: 'h-10 w-10 text-base'
};

const statusColors = {
  online: 'bg-green-500',
  away: 'bg-yellow-500',
  busy: 'bg-red-500',
  offline: 'bg-gray-400'
};

export const UserAvatar: React.FC<UserAvatarProps> = ({
  user,
  size = 'md',
  showStatus = false,
  status,
  className = ''
}) => {
  const initials = user.name
    .split(' ')
    .map(word => word.charAt(0).toUpperCase())
    .join('')
    .substring(0, 2);

  const sizeClass = sizeClasses[size];
  const statusColorClass = status ? statusColors[status] : '';

  return (
    <div className={`relative ${className}`}>
      {user.avatar ? (
        <img
          src={user.avatar}
          alt={user.name}
          className={`${sizeClass} rounded-full object-cover`}
        />
      ) : (
        <div className={`${sizeClass} rounded-full bg-gray-300 flex items-center justify-center text-gray-600 font-medium`}>
          {initials}
        </div>
      )}

      {showStatus && status && (
        <div className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white ${statusColorClass}`} />
      )}
    </div>
  );
};
