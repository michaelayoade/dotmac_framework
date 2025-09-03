'use client';

import React, { useState, useRef } from 'react';
import {
  Download,
  Eye,
  X,
  File,
  Image as ImageIcon,
  FileText,
  Video,
  Music,
  Archive,
  Code,
  Calendar,
  HardDrive,
  ExternalLink,
  MoreHorizontal,
  Edit,
  Trash2,
  Share,
  Copy,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { FilePreviewProps, FileItem } from '../../types';
import {
  formatFileSize,
  getFileIcon,
  isImageFile,
  isVideoFile,
  isAudioFile,
  isDocumentFile,
} from '../../utils/fileUtils';

const iconMap = {
  image: ImageIcon,
  file: File,
  'file-text': FileText,
  video: Video,
  music: Music,
  archive: Archive,
  code: Code,
  table: FileText,
  presentation: FileText,
};

export function FilePreview({
  file,
  showActions = true,
  showMetadata = true,
  onRemove,
  onDownload,
  onClick,
  variant = 'card',
  size = 'md',
}: FilePreviewProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Normalize file object
  const fileData =
    'id' in file
      ? file
      : {
          id: `${file.name}-${file.size}`,
          name: file.name,
          size: file.size,
          type: file.type,
          lastModified: file.lastModified,
          status: 'completed' as const,
          url: file instanceof File ? URL.createObjectURL(file) : undefined,
          uploadProgress: undefined,
        };

  const iconType = getFileIcon(fileData.type);
  const IconComponent = iconMap[iconType as keyof typeof iconMap] || File;

  const formatDate = (timestamp?: number) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleClick = () => {
    onClick?.();
  };

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDownload?.();
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove?.();
  };

  const handleMenuToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowMenu(!showMenu);
  };

  const sizeClasses = {
    sm: 'p-2',
    md: 'p-3',
    lg: 'p-4',
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  if (variant === 'list') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className={`
          flex items-center justify-between ${sizeClasses[size]} border-b border-gray-200
          hover:bg-gray-50 transition-colors cursor-pointer
        `}
        onClick={handleClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className='flex items-center space-x-3 min-w-0 flex-1'>
          <div className='flex-shrink-0'>
            {fileData.url && isImageFile({ type: fileData.type } as File) ? (
              <img
                src={fileData.url}
                alt={fileData.name}
                className={`${iconSizes[size]} object-cover rounded`}
              />
            ) : (
              <IconComponent className={`${iconSizes[size]} text-gray-500`} />
            )}
          </div>

          <div className='min-w-0 flex-1'>
            <p className='text-sm font-medium text-gray-900 truncate'>{fileData.name}</p>
            {showMetadata && (
              <p className='text-xs text-gray-500'>
                {formatFileSize(fileData.size)} • {formatDate(fileData.lastModified)}
              </p>
            )}
          </div>
        </div>

        {showActions && (isHovered || showMenu) && (
          <div className='flex items-center space-x-1'>
            {onDownload && (
              <button
                onClick={handleDownload}
                className='p-1 text-gray-400 hover:text-blue-600 rounded transition-colors'
                title='Download'
              >
                <Download className='w-4 h-4' />
              </button>
            )}

            <button
              onClick={handleClick}
              className='p-1 text-gray-400 hover:text-blue-600 rounded transition-colors'
              title='Preview'
            >
              <Eye className='w-4 h-4' />
            </button>

            {onRemove && (
              <button
                onClick={handleRemove}
                className='p-1 text-gray-400 hover:text-red-600 rounded transition-colors'
                title='Remove'
              >
                <X className='w-4 h-4' />
              </button>
            )}
          </div>
        )}
      </motion.div>
    );
  }

  if (variant === 'grid') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={`
          relative bg-white rounded-lg border border-gray-200 ${sizeClasses[size]}
          hover:shadow-md transition-shadow cursor-pointer group
        `}
        onClick={handleClick}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* File Preview */}
        <div className='aspect-square mb-3 bg-gray-50 rounded-lg flex items-center justify-center overflow-hidden'>
          {fileData.url && isImageFile({ type: fileData.type } as File) ? (
            <img src={fileData.url} alt={fileData.name} className='w-full h-full object-cover' />
          ) : (
            <IconComponent className='w-8 h-8 text-gray-400' />
          )}
        </div>

        {/* File Info */}
        <div className='space-y-1'>
          <p className='text-sm font-medium text-gray-900 truncate'>{fileData.name}</p>
          {showMetadata && <p className='text-xs text-gray-500'>{formatFileSize(fileData.size)}</p>}
        </div>

        {/* Actions Overlay */}
        {showActions && (
          <AnimatePresence>
            {isHovered && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className='absolute top-2 right-2 flex space-x-1'
              >
                {onDownload && (
                  <button
                    onClick={handleDownload}
                    className='p-1.5 bg-white shadow-sm border border-gray-200 rounded hover:bg-gray-50 transition-colors'
                    title='Download'
                  >
                    <Download className='w-3 h-3 text-gray-600' />
                  </button>
                )}

                {onRemove && (
                  <button
                    onClick={handleRemove}
                    className='p-1.5 bg-white shadow-sm border border-gray-200 rounded hover:bg-red-50 hover:text-red-600 transition-colors'
                    title='Remove'
                  >
                    <X className='w-3 h-3' />
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        )}

        {/* Status Indicator */}
        {fileData.status && fileData.status !== 'completed' && (
          <div className='absolute top-2 left-2'>
            <div
              className={`
              w-2 h-2 rounded-full
              ${fileData.status === 'uploading' ? 'bg-blue-500 animate-pulse' : ''}
              ${fileData.status === 'error' ? 'bg-red-500' : ''}
              ${fileData.status === 'pending' ? 'bg-yellow-500' : ''}
            `}
            />
          </div>
        )}
      </motion.div>
    );
  }

  // Card variant (default)
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className={`
        bg-white rounded-lg border border-gray-200 ${sizeClasses[size]}
        hover:shadow-md transition-shadow cursor-pointer
      `}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-3 min-w-0 flex-1'>
          {/* File Icon/Thumbnail */}
          <div className='flex-shrink-0'>
            {fileData.url && isImageFile({ type: fileData.type } as File) ? (
              <img
                src={fileData.url}
                alt={fileData.name}
                className={`${size === 'sm' ? 'w-8 h-8' : size === 'lg' ? 'w-12 h-12' : 'w-10 h-10'} object-cover rounded`}
              />
            ) : (
              <div
                className={`
                ${size === 'sm' ? 'w-8 h-8' : size === 'lg' ? 'w-12 h-12' : 'w-10 h-10'}
                bg-gray-100 rounded flex items-center justify-center
              `}
              >
                <IconComponent className={`${iconSizes[size]} text-gray-500`} />
              </div>
            )}
          </div>

          {/* File Details */}
          <div className='min-w-0 flex-1'>
            <div className='flex items-center space-x-2 mb-1'>
              <p
                className={`${size === 'sm' ? 'text-xs' : 'text-sm'} font-medium text-gray-900 truncate`}
              >
                {fileData.name}
              </p>

              {fileData.status && fileData.status !== 'completed' && (
                <span
                  className={`
                  inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                  ${fileData.status === 'uploading' ? 'bg-blue-100 text-blue-800' : ''}
                  ${fileData.status === 'error' ? 'bg-red-100 text-red-800' : ''}
                  ${fileData.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : ''}
                `}
                >
                  {fileData.status}
                </span>
              )}
            </div>

            {showMetadata && (
              <div className='flex items-center space-x-3 text-xs text-gray-500'>
                <span className='flex items-center'>
                  <HardDrive className='w-3 h-3 mr-1' />
                  {formatFileSize(fileData.size)}
                </span>
                {fileData.lastModified && (
                  <span className='flex items-center'>
                    <Calendar className='w-3 h-3 mr-1' />
                    {formatDate(fileData.lastModified)}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        {showActions && (
          <div className='flex items-center space-x-1 relative'>
            {/* Quick Actions */}
            <AnimatePresence>
              {isHovered && (
                <motion.div
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className='flex items-center space-x-1'
                >
                  {onDownload && (
                    <button
                      onClick={handleDownload}
                      className='p-1 text-gray-400 hover:text-blue-600 rounded transition-colors'
                      title='Download'
                    >
                      <Download className='w-4 h-4' />
                    </button>
                  )}

                  <button
                    onClick={handleClick}
                    className='p-1 text-gray-400 hover:text-blue-600 rounded transition-colors'
                    title='Preview'
                  >
                    <Eye className='w-4 h-4' />
                  </button>

                  {onRemove && (
                    <button
                      onClick={handleRemove}
                      className='p-1 text-gray-400 hover:text-red-600 rounded transition-colors'
                      title='Remove'
                    >
                      <X className='w-4 h-4' />
                    </button>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* More Actions Menu */}
            <div className='relative' ref={menuRef}>
              <button
                onClick={handleMenuToggle}
                className={`
                  p-1 text-gray-400 hover:text-gray-600 rounded transition-colors
                  ${showMenu ? 'text-gray-600' : ''}
                `}
                title='More actions'
              >
                <MoreHorizontal className='w-4 h-4' />
              </button>

              <AnimatePresence>
                {showMenu && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: -10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -10 }}
                    className='absolute right-0 top-full mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-10'
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle share
                        setShowMenu(false);
                      }}
                      className='w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center'
                    >
                      <Share className='w-4 h-4 mr-2' />
                      Share
                    </button>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle copy link
                        setShowMenu(false);
                      }}
                      className='w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center'
                    >
                      <Copy className='w-4 h-4 mr-2' />
                      Copy Link
                    </button>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle rename
                        setShowMenu(false);
                      }}
                      className='w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center'
                    >
                      <Edit className='w-4 h-4 mr-2' />
                      Rename
                    </button>

                    <div className='border-t border-gray-100 my-1' />

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemove?.();
                        setShowMenu(false);
                      }}
                      className='w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center'
                    >
                      <Trash2 className='w-4 h-4 mr-2' />
                      Delete
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {fileData.uploadProgress !== undefined && fileData.uploadProgress < 100 && (
        <div className='mt-3'>
          <div className='flex items-center justify-between text-xs text-gray-500 mb-1'>
            <span>Uploading...</span>
            <span>{Math.round(fileData.uploadProgress)}%</span>
          </div>
          <div className='w-full bg-gray-200 rounded-full h-1'>
            <div
              className='bg-blue-500 h-1 rounded-full transition-all duration-300'
              style={{ width: `${fileData.uploadProgress}%` }}
            />
          </div>
        </div>
      )}
    </motion.div>
  );
}
