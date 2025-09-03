/**
 * Universal File Upload Component
 * Production-ready file upload that works across all portal types with chunked uploads
 */

import React, { useState, useRef, useCallback, useMemo } from 'react';
import {
  Upload,
  File,
  Image,
  FileText,
  Video,
  Music,
  Archive,
  X,
  Check,
  AlertCircle,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  Eye,
  Download,
  Trash2,
  Plus,
  Cloud,
  HardDrive,
} from 'lucide-react';
import { useSupportFileUpload, useSupport } from '../providers/SupportProvider';
import type { FileUploadItem, FileUploadConfig, UploadStatus } from '../types';

// ===== INTERFACES =====

export interface UniversalFileUploadProps {
  // Upload configuration
  multiple?: boolean;
  accept?: string[];
  maxFileSize?: number;
  maxFiles?: number;
  chunkSize?: number;

  // Display options
  variant?: 'dropzone' | 'button' | 'inline' | 'modal';
  showPreview?: boolean;
  showProgress?: boolean;
  showFileList?: boolean;
  showUploadQueue?: boolean;
  compact?: boolean;

  // Behavior
  autoUpload?: boolean;
  allowPause?: boolean;
  allowCancel?: boolean;
  allowRetry?: boolean;
  allowRemove?: boolean;
  uploadOnDrop?: boolean;

  // Portal-specific
  category?: string;
  tags?: string[];
  visibility?: 'public' | 'private' | 'internal';

  // Customization
  placeholder?: string;
  uploadButtonText?: string;
  browseText?: string;
  dropzoneText?: string;

  // Callbacks
  onFilesSelected?: (files: File[]) => void;
  onUploadStart?: (file: FileUploadItem) => void;
  onUploadProgress?: (file: FileUploadItem, progress: number) => void;
  onUploadComplete?: (file: FileUploadItem) => void;
  onUploadError?: (file: FileUploadItem, error: string) => void;
  onAllComplete?: (files: FileUploadItem[]) => void;
  onRemove?: (fileId: string) => void;
}

interface FileItemProps {
  file: FileUploadItem;
  showPreview?: boolean;
  showProgress?: boolean;
  allowPause?: boolean;
  allowCancel?: boolean;
  allowRetry?: boolean;
  allowRemove?: boolean;
  compact?: boolean;
  onPause?: (fileId: string) => void;
  onResume?: (fileId: string) => void;
  onCancel?: (fileId: string) => void;
  onRetry?: (fileId: string) => void;
  onRemove?: (fileId: string) => void;
  onPreview?: (file: FileUploadItem) => void;
}

interface DropzoneProps {
  onDrop: (files: File[]) => void;
  accept?: string[];
  multiple?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
  className?: string;
}

// ===== UTILITY FUNCTIONS =====

function getFileIcon(fileName: string, size = 'w-4 h-4') {
  const extension = fileName.split('.').pop()?.toLowerCase();

  switch (extension) {
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'bmp':
    case 'svg':
    case 'webp':
      return <Image className={size} />;

    case 'mp4':
    case 'avi':
    case 'mov':
    case 'wmv':
    case 'flv':
    case 'webm':
      return <Video className={size} />;

    case 'mp3':
    case 'wav':
    case 'ogg':
    case 'flac':
    case 'aac':
      return <Music className={size} />;

    case 'zip':
    case 'rar':
    case '7z':
    case 'tar':
    case 'gz':
      return <Archive className={size} />;

    case 'pdf':
    case 'doc':
    case 'docx':
    case 'txt':
    case 'rtf':
      return <FileText className={size} />;

    default:
      return <File className={size} />;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getStatusColor(status: UploadStatus): string {
  switch (status) {
    case 'completed':
      return 'text-green-600';
    case 'uploading':
      return 'text-blue-600';
    case 'paused':
      return 'text-yellow-600';
    case 'failed':
      return 'text-red-600';
    case 'cancelled':
      return 'text-gray-500';
    default:
      return 'text-gray-600';
  }
}

function getStatusIcon(status: UploadStatus, size = 'w-4 h-4') {
  switch (status) {
    case 'completed':
      return <Check className={`${size} text-green-600`} />;
    case 'uploading':
      return <Loader2 className={`${size} text-blue-600 animate-spin`} />;
    case 'paused':
      return <Pause className={`${size} text-yellow-600`} />;
    case 'failed':
      return <AlertCircle className={`${size} text-red-600`} />;
    case 'cancelled':
      return <X className={`${size} text-gray-500`} />;
    default:
      return <Upload className={`${size} text-gray-600`} />;
  }
}

// ===== SUB-COMPONENTS =====

function Dropzone({
  onDrop,
  accept,
  multiple = true,
  disabled,
  children,
  className = '',
}: DropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [dragCounter, setDragCounter] = useState(0);

  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (!disabled) {
        setDragCounter((prev) => prev + 1);
        if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
          setIsDragOver(true);
        }
      }
    },
    [disabled]
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (!disabled) {
        setDragCounter((prev) => {
          const newCount = prev - 1;
          if (newCount === 0) {
            setIsDragOver(false);
          }
          return newCount;
        });
      }
    },
    [disabled]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (!disabled) {
        setIsDragOver(false);
        setDragCounter(0);

        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
          onDrop(files);
        }
      }
    },
    [disabled, onDrop]
  );

  return (
    <div
      className={`${className} ${isDragOver ? 'ring-2 ring-blue-500 ring-offset-2' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {children}
    </div>
  );
}

function FileItem({
  file,
  showPreview = true,
  showProgress = true,
  allowPause = true,
  allowCancel = true,
  allowRetry = true,
  allowRemove = true,
  compact = false,
  onPause,
  onResume,
  onCancel,
  onRetry,
  onRemove,
  onPreview,
}: FileItemProps) {
  const isImage = file.type.startsWith('image/');
  const canPreview = isImage && showPreview && file.url;

  const handlePreview = useCallback(() => {
    if (canPreview && onPreview) {
      onPreview(file);
    }
  }, [canPreview, file, onPreview]);

  if (compact) {
    return (
      <div className='flex items-center space-x-2 p-2 border rounded'>
        <div className='flex-shrink-0'>{getFileIcon(file.name, 'w-4 h-4')}</div>

        <div className='flex-1 min-w-0'>
          <div className='text-sm font-medium text-gray-900 truncate'>{file.name}</div>
          <div className='text-xs text-gray-500'>{formatFileSize(file.size)}</div>
        </div>

        <div className='flex items-center space-x-1'>
          {getStatusIcon(file.status, 'w-3 h-3')}

          {file.status === 'failed' && allowRetry && onRetry && (
            <button
              onClick={() => onRetry(file.id)}
              className='p-1 text-gray-400 hover:text-blue-600'
              title='Retry upload'
            >
              <RotateCcw className='w-3 h-3' />
            </button>
          )}

          {allowRemove && onRemove && (
            <button
              onClick={() => onRemove(file.id)}
              className='p-1 text-gray-400 hover:text-red-600'
              title='Remove file'
            >
              <X className='w-3 h-3' />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className='bg-white border rounded-lg p-4 space-y-3'>
      {/* Header */}
      <div className='flex items-start justify-between'>
        <div className='flex items-center space-x-3'>
          <div className='flex-shrink-0'>
            {canPreview ? (
              <button onClick={handlePreview} className='group'>
                <img
                  src={file.url}
                  alt={file.name}
                  className='w-10 h-10 object-cover rounded group-hover:opacity-80'
                />
              </button>
            ) : (
              <div className='w-10 h-10 bg-gray-100 rounded flex items-center justify-center'>
                {getFileIcon(file.name, 'w-5 h-5')}
              </div>
            )}
          </div>

          <div className='flex-1 min-w-0'>
            <div className='font-medium text-gray-900 truncate'>{file.name}</div>
            <div className='text-sm text-gray-500'>{formatFileSize(file.size)}</div>
          </div>
        </div>

        <div className='flex items-center space-x-1'>
          {getStatusIcon(file.status)}

          {file.status === 'uploading' && allowPause && onPause && (
            <button
              onClick={() => onPause(file.id)}
              className='p-1 text-gray-400 hover:text-yellow-600'
              title='Pause upload'
            >
              <Pause className='w-4 h-4' />
            </button>
          )}

          {file.status === 'paused' && onResume && (
            <button
              onClick={() => onResume(file.id)}
              className='p-1 text-gray-400 hover:text-blue-600'
              title='Resume upload'
            >
              <Play className='w-4 h-4' />
            </button>
          )}

          {(file.status === 'uploading' || file.status === 'paused') && allowCancel && onCancel && (
            <button
              onClick={() => onCancel(file.id)}
              className='p-1 text-gray-400 hover:text-red-600'
              title='Cancel upload'
            >
              <X className='w-4 h-4' />
            </button>
          )}

          {file.status === 'failed' && allowRetry && onRetry && (
            <button
              onClick={() => onRetry(file.id)}
              className='p-1 text-gray-400 hover:text-blue-600'
              title='Retry upload'
            >
              <RotateCcw className='w-4 h-4' />
            </button>
          )}

          {file.status === 'completed' && canPreview && (
            <button
              onClick={handlePreview}
              className='p-1 text-gray-400 hover:text-blue-600'
              title='Preview file'
            >
              <Eye className='w-4 h-4' />
            </button>
          )}

          {file.status === 'completed' && file.url && (
            <a
              href={file.url}
              download={file.name}
              className='p-1 text-gray-400 hover:text-green-600'
              title='Download file'
            >
              <Download className='w-4 h-4' />
            </a>
          )}

          {allowRemove && onRemove && (
            <button
              onClick={() => onRemove(file.id)}
              className='p-1 text-gray-400 hover:text-red-600'
              title='Remove file'
            >
              <Trash2 className='w-4 h-4' />
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      {showProgress && file.status === 'uploading' && (
        <div className='space-y-1'>
          <div className='flex justify-between text-xs text-gray-600'>
            <span>Uploading...</span>
            <span>{Math.round(file.progress || 0)}%</span>
          </div>
          <div className='w-full bg-gray-200 rounded-full h-1.5'>
            <div
              className='bg-blue-600 h-1.5 rounded-full transition-all duration-300'
              style={{ width: `${file.progress || 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Status Messages */}
      {file.status === 'failed' && file.error && (
        <div className='flex items-center space-x-2 text-sm text-red-600'>
          <AlertCircle className='w-4 h-4' />
          <span>{file.error}</span>
        </div>
      )}

      {file.status === 'completed' && (
        <div className='flex items-center space-x-2 text-sm text-green-600'>
          <CheckCircle className='w-4 h-4' />
          <span>Upload completed</span>
        </div>
      )}

      {file.status === 'cancelled' && (
        <div className='flex items-center space-x-2 text-sm text-gray-500'>
          <X className='w-4 h-4' />
          <span>Upload cancelled</span>
        </div>
      )}
    </div>
  );
}

// ===== MAIN COMPONENT =====

export function UniversalFileUpload({
  multiple = true,
  accept,
  maxFileSize,
  maxFiles = 10,
  chunkSize = 1024 * 1024, // 1MB chunks
  variant = 'dropzone',
  showPreview = true,
  showProgress = true,
  showFileList = true,
  showUploadQueue = true,
  compact = false,
  autoUpload = true,
  allowPause = true,
  allowCancel = true,
  allowRetry = true,
  allowRemove = true,
  uploadOnDrop = true,
  category,
  tags = [],
  visibility = 'public',
  placeholder = 'Select files or drag and drop here',
  uploadButtonText = 'Upload Files',
  browseText = 'Browse Files',
  dropzoneText = 'Drop files here to upload',
  onFilesSelected,
  onUploadStart,
  onUploadProgress,
  onUploadComplete,
  onUploadError,
  onAllComplete,
  onRemove,
}: UniversalFileUploadProps) {
  const { portalConfig, maxFileSize: portalMaxSize, supportedFormats } = useSupportFileUpload();
  const {
    uploads,
    uploadFile,
    pauseUpload,
    resumeUpload,
    cancelUpload,
    retryUpload,
    removeUpload,
    clearCompleted,
    isLoading,
  } = useSupportFileUpload();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  // Use portal-specific limits if not provided
  const effectiveMaxSize = useMemo(
    () => maxFileSize || portalMaxSize || 10 * 1024 * 1024,
    [maxFileSize, portalMaxSize]
  );

  const effectiveAccept = useMemo(
    () => accept || supportedFormats || ['*/*'],
    [accept, supportedFormats]
  );

  const acceptString = useMemo(
    () => (Array.isArray(effectiveAccept) ? effectiveAccept.join(',') : effectiveAccept),
    [effectiveAccept]
  );

  // Filter uploads based on current session
  const currentUploads = useMemo(
    () => uploads.filter((upload) => upload.category === category),
    [uploads, category]
  );

  const uploadStats = useMemo(() => {
    const completed = currentUploads.filter((f) => f.status === 'completed').length;
    const failed = currentUploads.filter((f) => f.status === 'failed').length;
    const uploading = currentUploads.filter((f) => f.status === 'uploading').length;
    const paused = currentUploads.filter((f) => f.status === 'paused').length;

    return { completed, failed, uploading, paused, total: currentUploads.length };
  }, [currentUploads]);

  const validateFile = useCallback(
    (file: File): string | null => {
      if (file.size > effectiveMaxSize) {
        return `File size exceeds limit of ${formatFileSize(effectiveMaxSize)}`;
      }

      if (effectiveAccept.length > 0 && !effectiveAccept.includes('*/*')) {
        const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
        const mimeType = file.type;

        const isAccepted = effectiveAccept.some(
          (accept) =>
            accept === mimeType ||
            accept === extension ||
            (accept.endsWith('/*') && mimeType.startsWith(accept.slice(0, -1)))
        );

        if (!isAccepted) {
          return `File type not supported. Allowed: ${effectiveAccept.join(', ')}`;
        }
      }

      if (maxFiles && currentUploads.length >= maxFiles) {
        return `Maximum number of files (${maxFiles}) exceeded`;
      }

      return null;
    },
    [effectiveMaxSize, effectiveAccept, maxFiles, currentUploads.length]
  );

  const handleFiles = useCallback(
    async (files: File[]) => {
      const validFiles: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        const error = validateFile(file);
        if (error) {
          errors.push(`${file.name}: ${error}`);
        } else {
          validFiles.push(file);
        }
      }

      if (errors.length > 0) {
        console.warn('File validation errors:', errors);
      }

      if (validFiles.length > 0) {
        onFilesSelected?.(validFiles);

        if (autoUpload) {
          for (const file of validFiles) {
            try {
              const uploadConfig: FileUploadConfig = {
                chunkSize,
                category,
                tags,
                visibility,
                metadata: {
                  portal: portalConfig.type,
                  timestamp: new Date().toISOString(),
                },
              };

              const uploadItem = await uploadFile(file, uploadConfig);
              onUploadStart?.(uploadItem);

              // Monitor progress
              const progressInterval = setInterval(() => {
                const current = uploads.find((u) => u.id === uploadItem.id);
                if (current) {
                  onUploadProgress?.(current, current.progress || 0);

                  if (current.status === 'completed') {
                    clearInterval(progressInterval);
                    onUploadComplete?.(current);
                  } else if (current.status === 'failed') {
                    clearInterval(progressInterval);
                    onUploadError?.(current, current.error || 'Upload failed');
                  }
                }
              }, 100);
            } catch (error) {
              console.error('Upload failed:', error);
            }
          }

          // Check if all uploads are complete
          setTimeout(() => {
            const allCompleted = validFiles.every((file) => {
              const upload = uploads.find((u) => u.name === file.name);
              return upload && upload.status === 'completed';
            });

            if (allCompleted) {
              const completedUploads = validFiles
                .map((file) => uploads.find((u) => u.name === file.name)!)
                .filter(Boolean);
              onAllComplete?.(completedUploads);
            }
          }, 1000);
        }
      }
    },
    [
      validateFile,
      onFilesSelected,
      autoUpload,
      uploadFile,
      chunkSize,
      category,
      tags,
      visibility,
      portalConfig.type,
      onUploadStart,
      onUploadProgress,
      onUploadComplete,
      onUploadError,
      onAllComplete,
      uploads,
    ]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        handleFiles(files);
      }
      // Reset input so same file can be selected again
      e.target.value = '';
    },
    [handleFiles]
  );

  const handleDrop = useCallback(
    (files: File[]) => {
      if (uploadOnDrop) {
        handleFiles(files);
      } else {
        onFilesSelected?.(files);
      }
    },
    [uploadOnDrop, handleFiles, onFilesSelected]
  );

  const handleBrowse = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handlePause = useCallback(
    (fileId: string) => {
      pauseUpload(fileId);
    },
    [pauseUpload]
  );

  const handleResume = useCallback(
    (fileId: string) => {
      resumeUpload(fileId);
    },
    [resumeUpload]
  );

  const handleCancel = useCallback(
    (fileId: string) => {
      cancelUpload(fileId);
    },
    [cancelUpload]
  );

  const handleRetry = useCallback(
    (fileId: string) => {
      retryUpload(fileId);
    },
    [retryUpload]
  );

  const handleRemove = useCallback(
    (fileId: string) => {
      removeUpload(fileId);
      onRemove?.(fileId);
    },
    [removeUpload, onRemove]
  );

  if (variant === 'button') {
    return (
      <div className='space-y-4'>
        <div className='flex items-center space-x-2'>
          <input
            ref={fileInputRef}
            type='file'
            multiple={multiple}
            accept={acceptString}
            onChange={handleFileSelect}
            className='hidden'
          />

          <button
            onClick={handleBrowse}
            disabled={isLoading('upload')}
            className='flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
          >
            {isLoading('upload') ? (
              <Loader2 className='w-4 h-4 animate-spin' />
            ) : (
              <Plus className='w-4 h-4' />
            )}
            <span>{browseText}</span>
          </button>

          {uploadStats.total > 0 && (
            <div className='text-sm text-gray-600'>
              {uploadStats.completed} of {uploadStats.total} completed
              {uploadStats.failed > 0 && `, ${uploadStats.failed} failed`}
            </div>
          )}
        </div>

        {showFileList && currentUploads.length > 0 && (
          <div className={compact ? 'space-y-2' : 'space-y-3'}>
            {currentUploads.map((file) => (
              <FileItem
                key={file.id}
                file={file}
                showPreview={showPreview}
                showProgress={showProgress}
                allowPause={allowPause}
                allowCancel={allowCancel}
                allowRetry={allowRetry}
                allowRemove={allowRemove}
                compact={compact}
                onPause={handlePause}
                onResume={handleResume}
                onCancel={handleCancel}
                onRetry={handleRetry}
                onRemove={handleRemove}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <div className='flex items-center space-x-2'>
        <input
          ref={fileInputRef}
          type='file'
          multiple={multiple}
          accept={acceptString}
          onChange={handleFileSelect}
          className='hidden'
        />

        <button
          onClick={handleBrowse}
          disabled={isLoading('upload')}
          className='flex items-center space-x-1 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors disabled:opacity-50'
        >
          <Upload className='w-3 h-3' />
          <span>Attach</span>
        </button>

        {currentUploads.length > 0 && (
          <span className='text-xs text-gray-500'>
            {uploadStats.completed}/{uploadStats.total} files
          </span>
        )}
      </div>
    );
  }

  // Dropzone variant (default)
  return (
    <div className='space-y-4'>
      <input
        ref={fileInputRef}
        type='file'
        multiple={multiple}
        accept={acceptString}
        onChange={handleFileSelect}
        className='hidden'
      />

      <Dropzone
        onDrop={handleDrop}
        accept={effectiveAccept}
        multiple={multiple}
        disabled={isLoading('upload')}
        className='border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors'
      >
        <div className='space-y-4'>
          <div className='flex justify-center'>
            {isLoading('upload') ? (
              <Loader2 className='w-12 h-12 text-blue-600 animate-spin' />
            ) : (
              <Cloud className='w-12 h-12 text-gray-400' />
            )}
          </div>

          <div>
            <p className='text-lg font-medium text-gray-900 mb-1'>{placeholder}</p>
            <p className='text-sm text-gray-500'>
              or{' '}
              <button
                onClick={handleBrowse}
                disabled={isLoading('upload')}
                className='text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50'
              >
                {browseText.toLowerCase()}
              </button>
            </p>
          </div>

          <div className='text-xs text-gray-500'>
            {effectiveAccept.length > 0 && effectiveAccept[0] !== '*/*' && (
              <p>Supported: {effectiveAccept.join(', ')}</p>
            )}
            <p>Maximum file size: {formatFileSize(effectiveMaxSize)}</p>
            {maxFiles && <p>Maximum files: {maxFiles}</p>}
          </div>
        </div>
      </Dropzone>

      {showUploadQueue && uploadStats.total > 0 && (
        <div className='bg-gray-50 rounded-lg p-4'>
          <div className='flex items-center justify-between mb-3'>
            <h4 className='font-medium text-gray-900'>Upload Queue</h4>
            <div className='flex items-center space-x-4 text-sm text-gray-600'>
              <span>{uploadStats.completed} completed</span>
              {uploadStats.uploading > 0 && <span>{uploadStats.uploading} uploading</span>}
              {uploadStats.failed > 0 && (
                <span className='text-red-600'>{uploadStats.failed} failed</span>
              )}

              {uploadStats.completed > 0 && (
                <button
                  onClick={clearCompleted}
                  className='text-blue-600 hover:text-blue-700 text-xs'
                >
                  Clear completed
                </button>
              )}
            </div>
          </div>

          <div className={compact ? 'space-y-2' : 'space-y-3'}>
            {currentUploads.map((file) => (
              <FileItem
                key={file.id}
                file={file}
                showPreview={showPreview}
                showProgress={showProgress}
                allowPause={allowPause}
                allowCancel={allowCancel}
                allowRetry={allowRetry}
                allowRemove={allowRemove}
                compact={compact}
                onPause={handlePause}
                onResume={handleResume}
                onCancel={handleCancel}
                onRetry={handleRetry}
                onRemove={handleRemove}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default UniversalFileUpload;
