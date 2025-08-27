/**
 * Skeleton Component - Temporary fallback
 */

import React from 'react';

interface SkeletonProps {
  className?: string;
  height?: string;
  width?: string;
}

export function Skeleton({ className = '', height = '20px', width = '100%' }: SkeletonProps) {
  return (
    <div 
      className={`animate-pulse bg-gray-200 rounded ${className}`}
      style={{ height, width }}
    />
  );
}