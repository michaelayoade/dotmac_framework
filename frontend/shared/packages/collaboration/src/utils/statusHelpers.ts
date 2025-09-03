import React from 'react';
import { UserStatus, ConflictStatus, SuggestionStatus } from '../types';

export const getUserStatusColor = (status: UserStatus): string => {
  switch (status) {
    case 'online':
      return 'text-green-600 bg-green-100';
    case 'away':
      return 'text-yellow-600 bg-yellow-100';
    case 'busy':
      return 'text-red-600 bg-red-100';
    case 'offline':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getUserStatusText = (status: UserStatus): string => {
  switch (status) {
    case 'online':
      return 'Online';
    case 'away':
      return 'Away';
    case 'busy':
      return 'Busy';
    case 'offline':
      return 'Offline';
    default:
      return 'Unknown';
  }
};

export const getConflictStatusColor = (status: ConflictStatus): string => {
  switch (status) {
    case 'resolved':
      return 'text-green-600 bg-green-100';
    case 'unresolved':
      return 'text-red-600 bg-red-100';
    case 'reviewing':
      return 'text-yellow-600 bg-yellow-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getSuggestionStatusColor = (status: SuggestionStatus): string => {
  switch (status) {
    case 'accepted':
      return 'text-green-600 bg-green-100';
    case 'rejected':
      return 'text-red-600 bg-red-100';
    case 'pending':
      return 'text-yellow-600 bg-yellow-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

export const getSuggestionStatusText = (status: SuggestionStatus): string => {
  switch (status) {
    case 'accepted':
      return 'Accepted';
    case 'rejected':
      return 'Rejected';
    case 'pending':
      return 'Pending Review';
    default:
      return 'Unknown';
  }
};
