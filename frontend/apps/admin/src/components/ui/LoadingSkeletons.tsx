/**
 * Loading Skeletons
 * Reusable skeleton components for improved loading UX
 */

'use client';

import React from 'react';
import { cn } from '../../design-system/utils';

// Base Skeleton Component
interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  rounded?: boolean | 'sm' | 'md' | 'lg' | 'full';
  animate?: boolean;
}

export function Skeleton({ 
  className = '', 
  width, 
  height, 
  rounded = true, 
  animate = true 
}: SkeletonProps) {
  const roundedClass = typeof rounded === 'boolean' 
    ? rounded ? 'rounded' : ''
    : {
        sm: 'rounded-sm',
        md: 'rounded-md', 
        lg: 'rounded-lg',
        full: 'rounded-full'
      }[rounded];

  return (
    <div
      className={cn(
        'bg-gray-200',
        animate && 'animate-pulse',
        roundedClass,
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
}

// Text Skeleton
interface TextSkeletonProps {
  lines?: number;
  className?: string;
  animate?: boolean;
}

export function TextSkeleton({ lines = 1, className = '', animate = true }: TextSkeletonProps) {
  return (
    <div className={cn('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          className="h-4"
          width={index === lines - 1 ? '75%' : '100%'}
          animate={animate}
        />
      ))}
    </div>
  );
}

// Avatar Skeleton
interface AvatarSkeletonProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  animate?: boolean;
}

export function AvatarSkeleton({ size = 'md', className = '', animate = true }: AvatarSkeletonProps) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };

  return (
    <Skeleton
      className={cn(sizeClasses[size], className)}
      rounded="full"
      animate={animate}
    />
  );
}

// Card Skeleton
interface CardSkeletonProps {
  className?: string;
  showImage?: boolean;
  imageHeight?: number;
  titleLines?: number;
  bodyLines?: number;
  showFooter?: boolean;
  animate?: boolean;
}

export function CardSkeleton({
  className = '',
  showImage = false,
  imageHeight = 160,
  titleLines = 1,
  bodyLines = 3,
  showFooter = false,
  animate = true
}: CardSkeletonProps) {
  return (
    <div className={cn('bg-white rounded-lg border p-6', className)}>
      {showImage && (
        <Skeleton 
          className="w-full mb-4" 
          height={imageHeight}
          animate={animate}
        />
      )}
      
      <div className="space-y-4">
        <TextSkeleton lines={titleLines} className="space-y-2" animate={animate} />
        <TextSkeleton lines={bodyLines} animate={animate} />
        
        {showFooter && (
          <div className="flex items-center justify-between pt-4">
            <Skeleton className="h-4 w-20" animate={animate} />
            <Skeleton className="h-8 w-16" animate={animate} />
          </div>
        )}
      </div>
    </div>
  );
}

// Table Skeleton
interface TableSkeletonProps {
  rows?: number;
  columns?: number;
  className?: string;
  showHeader?: boolean;
  animate?: boolean;
}

export function TableSkeleton({
  rows = 5,
  columns = 4,
  className = '',
  showHeader = true,
  animate = true
}: TableSkeletonProps) {
  return (
    <div className={cn('bg-white rounded-lg border overflow-hidden', className)}>
      <table className="min-w-full divide-y divide-gray-200">
        {showHeader && (
          <thead className="bg-gray-50">
            <tr>
              {Array.from({ length: columns }).map((_, index) => (
                <th key={index} className="px-6 py-3">
                  <Skeleton className="h-4" animate={animate} />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="divide-y divide-gray-200">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-6 py-4">
                  <Skeleton className="h-4" animate={animate} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// List Skeleton
interface ListSkeletonProps {
  items?: number;
  className?: string;
  showAvatar?: boolean;
  showActions?: boolean;
  animate?: boolean;
}

export function ListSkeleton({
  items = 5,
  className = '',
  showAvatar = false,
  showActions = false,
  animate = true
}: ListSkeletonProps) {
  return (
    <div className={cn('bg-white rounded-lg border divide-y divide-gray-200', className)}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} className="flex items-center justify-between p-4">
          <div className="flex items-center space-x-3">
            {showAvatar && <AvatarSkeleton animate={animate} />}
            <div className="space-y-2">
              <Skeleton className="h-4 w-32" animate={animate} />
              <Skeleton className="h-3 w-24" animate={animate} />
            </div>
          </div>
          
          {showActions && (
            <div className="flex space-x-2">
              <Skeleton className="h-8 w-8" rounded="md" animate={animate} />
              <Skeleton className="h-8 w-8" rounded="md" animate={animate} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Stats Skeleton
interface StatsSkeletonProps {
  stats?: number;
  className?: string;
  layout?: 'grid' | 'row';
  animate?: boolean;
}

export function StatsSkeleton({
  stats = 4,
  className = '',
  layout = 'grid',
  animate = true
}: StatsSkeletonProps) {
  const containerClass = layout === 'grid' 
    ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'
    : 'flex space-x-6 overflow-x-auto';

  return (
    <div className={cn(containerClass, className)}>
      {Array.from({ length: stats }).map((_, index) => (
        <div key={index} className="bg-white rounded-lg border p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" animate={animate} />
              <Skeleton className="h-8 w-16" animate={animate} />
            </div>
            <Skeleton className="h-12 w-12" rounded="full" animate={animate} />
          </div>
          <div className="mt-4">
            <Skeleton className="h-3 w-full" animate={animate} />
          </div>
        </div>
      ))}
    </div>
  );
}

// Form Skeleton
interface FormSkeletonProps {
  fields?: number;
  className?: string;
  showButtons?: boolean;
  animate?: boolean;
}

export function FormSkeleton({
  fields = 4,
  className = '',
  showButtons = true,
  animate = true
}: FormSkeletonProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {Array.from({ length: fields }).map((_, index) => (
        <div key={index} className="space-y-2">
          <Skeleton className="h-4 w-24" animate={animate} />
          <Skeleton className="h-10 w-full" rounded="md" animate={animate} />
        </div>
      ))}
      
      {showButtons && (
        <div className="flex justify-end space-x-3 pt-6">
          <Skeleton className="h-10 w-20" rounded="md" animate={animate} />
          <Skeleton className="h-10 w-16" rounded="md" animate={animate} />
        </div>
      )}
    </div>
  );
}

// Chart Skeleton
interface ChartSkeletonProps {
  className?: string;
  type?: 'bar' | 'line' | 'pie' | 'area';
  showLegend?: boolean;
  animate?: boolean;
}

export function ChartSkeleton({
  className = '',
  type = 'bar',
  showLegend = false,
  animate = true
}: ChartSkeletonProps) {
  return (
    <div className={cn('bg-white rounded-lg border p-6', className)}>
      <div className="mb-6">
        <Skeleton className="h-6 w-32 mb-2" animate={animate} />
        <Skeleton className="h-4 w-48" animate={animate} />
      </div>
      
      <div className="relative h-64">
        {type === 'bar' && (
          <div className="flex items-end justify-between h-full space-x-2">
            {Array.from({ length: 12 }).map((_, index) => (
              <Skeleton
                key={index}
                className="flex-1"
                height={Math.random() * 200 + 40}
                animate={animate}
              />
            ))}
          </div>
        )}
        
        {type === 'line' && (
          <div className="h-full">
            <Skeleton className="h-full w-full" animate={animate} />
            <div className="absolute inset-0 flex items-center">
              <svg className="w-full h-full opacity-20" viewBox="0 0 400 200">
                <path 
                  d="M10,150 Q50,100 100,120 T200,80 T300,100 T390,60" 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  fill="none"
                />
              </svg>
            </div>
          </div>
        )}
        
        {type === 'pie' && (
          <div className="flex items-center justify-center h-full">
            <Skeleton className="w-40 h-40" rounded="full" animate={animate} />
          </div>
        )}
        
        {type === 'area' && (
          <div className="h-full">
            <Skeleton className="h-full w-full" animate={animate} />
          </div>
        )}
      </div>
      
      {showLegend && (
        <div className="flex items-center justify-center mt-4 space-x-6">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="flex items-center space-x-2">
              <Skeleton className="w-3 h-3" rounded="full" animate={animate} />
              <Skeleton className="h-4 w-16" animate={animate} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Page Skeleton (complete page layout)
interface PageSkeletonProps {
  className?: string;
  showHeader?: boolean;
  showSidebar?: boolean;
  contentType?: 'dashboard' | 'table' | 'form' | 'details';
  animate?: boolean;
}

export function PageSkeleton({
  className = '',
  showHeader = true,
  showSidebar = false,
  contentType = 'dashboard',
  animate = true
}: PageSkeletonProps) {
  return (
    <div className={cn('min-h-screen bg-gray-50', className)}>
      {showHeader && (
        <div className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Skeleton className="h-8 w-32" animate={animate} />
            </div>
            <div className="flex items-center space-x-2">
              <Skeleton className="h-10 w-10" rounded="full" animate={animate} />
              <Skeleton className="h-10 w-24" animate={animate} />
            </div>
          </div>
        </div>
      )}
      
      <div className="flex">
        {showSidebar && (
          <div className="w-64 bg-white border-r border-gray-200 min-h-screen p-4">
            <div className="space-y-4">
              {Array.from({ length: 8 }).map((_, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <Skeleton className="h-5 w-5" animate={animate} />
                  <Skeleton className="h-4 w-24" animate={animate} />
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="flex-1 p-6">
          {contentType === 'dashboard' && (
            <div className="space-y-6">
              <StatsSkeleton animate={animate} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ChartSkeleton animate={animate} />
                <ChartSkeleton animate={animate} />
              </div>
              <ListSkeleton showAvatar showActions animate={animate} />
            </div>
          )}
          
          {contentType === 'table' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <Skeleton className="h-8 w-48" animate={animate} />
                <Skeleton className="h-10 w-32" animate={animate} />
              </div>
              <TableSkeleton animate={animate} />
            </div>
          )}
          
          {contentType === 'form' && (
            <div className="max-w-2xl">
              <div className="mb-6">
                <Skeleton className="h-8 w-48 mb-2" animate={animate} />
                <Skeleton className="h-4 w-96" animate={animate} />
              </div>
              <FormSkeleton animate={animate} />
            </div>
          )}
          
          {contentType === 'details' && (
            <div className="space-y-6">
              <div className="bg-white rounded-lg border p-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-8 w-64" animate={animate} />
                    <Skeleton className="h-4 w-48" animate={animate} />
                  </div>
                  <Skeleton className="h-10 w-24" animate={animate} />
                </div>
                <div className="mt-6 grid grid-cols-2 gap-6">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <div key={index} className="space-y-1">
                      <Skeleton className="h-4 w-20" animate={animate} />
                      <Skeleton className="h-6 w-32" animate={animate} />
                    </div>
                  ))}
                </div>
              </div>
              <CardSkeleton showFooter animate={animate} />
              <CardSkeleton animate={animate} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}