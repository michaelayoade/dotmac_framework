'use client';

import React, { useCallback, useRef, useState } from 'react';
import { Upload, X, AlertCircle, CheckCircle2, File, Image, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { FileUploadOptions, FileItem, RejectedFile } from '../../types';
import { formatFileSize, validateFiles, generateFileId, isImageFile } from '../../utils/fileUtils';

interface FileUploadProps {
  onFilesAdded?: (files: FileItem[]) => void;
  onFilesRejected?: (rejectedFiles: RejectedFile[]) => void;
  onFilesRemoved?: (fileIds: string[]) => void;
  options?: FileUploadOptions;
  disabled?: boolean;
  className?: string;
  variant?: 'dropzone' | 'button' | 'minimal';
  showPreview?: boolean;
  maxPreviewItems?: number;
}

const defaultOptions: FileUploadOptions = {
  multiple: true,
  maxSize: 10 * 1024 * 1024, // 10MB
  maxFiles: 10,
  accept: []
};

export function FileUpload({
  onFilesAdded,
  onFilesRejected,
  onFilesRemoved,
  options = defaultOptions,
  disabled = false,
  className = '',
  variant = 'dropzone',
  showPreview = true,
  maxPreviewItems = 5
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const mergedOptions = { ...defaultOptions, ...options };

  const processFiles = useCallback(async (selectedFiles: File[]) => {
    if (selectedFiles.length === 0) return;

    setIsProcessing(true);

    try {
      // Validate files
      const validationRules = [
        {
          maxSize: mergedOptions.maxSize || undefined,
          allowedTypes: mergedOptions.accept || undefined,
        }
      ].filter(rule => rule.maxSize !== undefined || rule.allowedTypes !== undefined);

      const { accepted, rejected } = await validateFiles(selectedFiles, validationRules);

      // Check max files limit
      const currentFileCount = files.length;
      const maxFiles = mergedOptions.maxFiles || 10;

      if (currentFileCount + accepted.length > maxFiles) {
        const allowedCount = Math.max(0, maxFiles - currentFileCount);
        const excess = accepted.splice(allowedCount);
        rejected.push(...excess.map(file => ({ file, reason: 'too-many-files' as const })));
      }

      // Create file items from accepted files
      const fileItems: FileItem[] = await Promise.all(
        accepted.map(async (file) => {
          const fileItem: FileItem = {
            id: generateFileId(file),
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified,
            status: 'pending',
            uploadProgress: 0
          };

          // Generate thumbnail for images if required
          if (mergedOptions.generateThumbnails && isImageFile(file)) {
            try {
              fileItem.thumbnailUrl = URL.createObjectURL(file);
            } catch (error) {
              console.warn('Failed to generate thumbnail:', error);
            }
          }

          return fileItem;
        })
      );

      // Update state
      setFiles(prev => [...prev, ...fileItems]);

      // Notify parent components
      onFilesAdded?.(fileItems);

      if (rejected.length > 0) {
        onFilesRejected?.(rejected);
      }

    } catch (error) {
      console.error('Error processing files:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [files, mergedOptions, onFilesAdded, onFilesRejected]);

  const handleFileInput = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    processFiles(selectedFiles);

    // Reset input value
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [processFiles]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;

    if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;

    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    setIsDragOver(false);
    dragCounterRef.current = 0;

    if (disabled) return;

    const droppedFiles = Array.from(e.dataTransfer?.files || []);
    processFiles(droppedFiles);
  }, [disabled, processFiles]);

  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => {
      const updatedFiles = prev.filter(f => f.id !== fileId);
      const removedFile = prev.find(f => f.id === fileId);

      // Cleanup thumbnail URL
      if (removedFile?.thumbnailUrl) {
        URL.revokeObjectURL(removedFile.thumbnailUrl);
      }

      return updatedFiles;
    });

    onFilesRemoved?.([fileId]);
  }, [onFilesRemoved]);

  const openFileDialog = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  }, [disabled]);

  const renderDropzone = () => (
    <div
      className={`
        relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 cursor-pointer
        ${isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
        ${disabled ? 'opacity-50 cursor-not-allowed bg-gray-50' : 'hover:bg-gray-50'}
        ${className}
      `}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={openFileDialog}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple={mergedOptions.multiple}
        accept={mergedOptions.accept?.join(',')}
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        disabled={disabled}
      />

      <div className="space-y-3">
        {isProcessing ? (
          <Loader2 className="w-12 h-12 mx-auto text-blue-500 animate-spin" />
        ) : (
          <Upload className="w-12 h-12 mx-auto text-gray-400" />
        )}

        <div>
          <p className="text-lg font-medium text-gray-900">
            {isProcessing ? 'Processing files...' : 'Drop files here or click to browse'}
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {mergedOptions.accept && mergedOptions.accept.length > 0 && (
              <>Accepted types: {mergedOptions.accept.join(', ')}<br /></>
            )}
            {mergedOptions.maxSize && (
              <>Max size: {formatFileSize(mergedOptions.maxSize)}<br /></>
            )}
            {mergedOptions.maxFiles && (
              <>Max files: {mergedOptions.maxFiles}</>
            )}
          </p>
        </div>
      </div>
    </div>
  );

  const renderButton = () => (
    <button
      type="button"
      onClick={openFileDialog}
      disabled={disabled || isProcessing}
      className={`
        inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg shadow-sm
        bg-white text-sm font-medium text-gray-700 hover:bg-gray-50
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple={mergedOptions.multiple}
        accept={mergedOptions.accept?.join(',')}
        onChange={handleFileInput}
        className="hidden"
        disabled={disabled}
      />

      {isProcessing ? (
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
      ) : (
        <Upload className="w-4 h-4 mr-2" />
      )}
      {isProcessing ? 'Processing...' : 'Upload Files'}
    </button>
  );

  const renderMinimal = () => (
    <button
      type="button"
      onClick={openFileDialog}
      disabled={disabled || isProcessing}
      className={`
        inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-500
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple={mergedOptions.multiple}
        accept={mergedOptions.accept?.join(',')}
        onChange={handleFileInput}
        className="hidden"
        disabled={disabled}
      />

      {isProcessing ? (
        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
      ) : (
        <Upload className="w-4 h-4 mr-1" />
      )}
      {isProcessing ? 'Processing...' : 'Upload'}
    </button>
  );

  const renderFilePreview = () => {
    if (!showPreview || files.length === 0) return null;

    const displayFiles = files.slice(0, maxPreviewItems);
    const remainingCount = files.length - displayFiles.length;

    return (
      <div className="mt-4 space-y-2">
        <h4 className="text-sm font-medium text-gray-900">
          Uploaded Files ({files.length})
        </h4>

        <AnimatePresence>
          {displayFiles.map((file) => (
            <motion.div
              key={file.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  {file.thumbnailUrl ? (
                    <img
                      src={file.thumbnailUrl}
                      alt={file.name}
                      className="w-10 h-10 object-cover rounded"
                    />
                  ) : isImageFile({ type: file.type } as File) ? (
                    <Image className="w-5 h-5 text-blue-500" />
                  ) : (
                    <File className="w-5 h-5 text-gray-500" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)}
                  </p>
                </div>

                <div className="flex-shrink-0">
                  {file.status === 'completed' && (
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                  )}
                  {file.status === 'error' && (
                    <AlertCircle className="w-5 h-5 text-red-500" />
                  )}
                  {file.status === 'uploading' && (
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => removeFile(file.id)}
                className="ml-2 text-gray-400 hover:text-red-500 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>

        {remainingCount > 0 && (
          <p className="text-xs text-gray-500 text-center">
            + {remainingCount} more files
          </p>
        )}
      </div>
    );
  };

  return (
    <div>
      {variant === 'dropzone' && renderDropzone()}
      {variant === 'button' && renderButton()}
      {variant === 'minimal' && renderMinimal()}
      {renderFilePreview()}
    </div>
  );
}
