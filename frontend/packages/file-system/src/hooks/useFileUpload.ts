'use client';

import { useState, useCallback, useRef, useMemo } from 'react';
import type { FileItem, FileUploadOptions, RejectedFile, UploadProgress } from '../types';
import { validateFiles, generateFileId, isImageFile, createThumbnail } from '../utils/fileUtils';

interface UseFileUploadOptions extends FileUploadOptions {
  onUploadStart?: (files: FileItem[]) => void;
  onUploadProgress?: (fileId: string, progress: UploadProgress) => void;
  onUploadComplete?: (fileId: string, result: any) => void;
  onUploadError?: (fileId: string, error: string) => void;
  uploadFunction?: (file: File, onProgress: (progress: UploadProgress) => void) => Promise<any>;
}

export function useFileUpload(options: UseFileUploadOptions = {}) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rejectedFiles, setRejectedFiles] = useState<RejectedFile[]>([]);

  const uploadPromisesRef = useRef<Map<string, AbortController>>(new Map());

  const {
    multiple = true,
    maxSize = 10 * 1024 * 1024, // 10MB
    maxFiles = 10,
    accept = [],
    generateThumbnails = false,
    onUploadStart,
    onUploadProgress,
    onUploadComplete,
    onUploadError,
    uploadFunction
  } = options;

  const addFiles = useCallback(async (newFiles: File[]) => {
    if (newFiles.length === 0) return;

    setError(null);

    try {
      // Validate files
      const validationRules = [
        {
          maxSize,
          allowedTypes: accept,
        }
      ];

      const { accepted, rejected } = await validateFiles(newFiles, validationRules);

      // Update rejected files
      if (rejected.length > 0) {
        setRejectedFiles(prev => [...prev, ...rejected]);
      }

      // Check max files limit
      const currentFileCount = files.length;

      if (currentFileCount + accepted.length > maxFiles) {
        const allowedCount = Math.max(0, maxFiles - currentFileCount);
        const excess = accepted.splice(allowedCount);
        const excessRejected = excess.map(file => ({
          file,
          reason: 'too-many-files' as const
        }));

        setRejectedFiles(prev => [...prev, ...excessRejected]);
      }

      if (accepted.length === 0) return;

      // Create file items
      const fileItems: FileItem[] = await Promise.all(
        accepted.map(async (file) => {
          const fileItem: FileItem = {
            id: generateFileId(file),
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified,
            status: 'pending',
            uploadProgress: 0,
            error: undefined
          };

          // Generate thumbnail for images if required
          if (generateThumbnails && isImageFile(file)) {
            try {
              fileItem.thumbnailUrl = await createThumbnail(file, {
                width: 150,
                height: 150,
                fit: 'cover',
                quality: 80
              });
            } catch (error) {
              console.warn('Failed to generate thumbnail:', error);
            }
          }

          return fileItem;
        })
      );

      // Add files to state
      setFiles(prev => [...prev, ...fileItems]);

      // Start upload if upload function is provided
      if (uploadFunction) {
        uploadFiles(fileItems);
      }

    } catch (error) {
      console.error('Error adding files:', error);
      setError('Failed to process files');
    }
  }, [files, maxSize, maxFiles, accept, generateThumbnails, uploadFunction]);

  const uploadFiles = useCallback(async (fileItems?: FileItem[]) => {
    const filesToUpload = fileItems || files.filter(f => f.status === 'pending');

    if (filesToUpload.length === 0 || !uploadFunction) return;

    setIsUploading(true);
    setError(null);

    onUploadStart?.(filesToUpload);

    // Update file statuses to uploading
    setFiles(prev => prev.map(file =>
      filesToUpload.find(f => f.id === file.id)
        ? { ...file, status: 'uploading', uploadProgress: 0 }
        : file
    ));

    // Upload files concurrently
    const uploadPromises = filesToUpload.map(async (fileItem) => {
      const abortController = new AbortController();
      uploadPromisesRef.current.set(fileItem.id, abortController);

      try {
        // Find original file (this is a simplified approach)
        const originalFile = new File([''], fileItem.name, { type: fileItem.type });

        const result = await uploadFunction(originalFile, (progress) => {
          onUploadProgress?.(fileItem.id, progress);

          setFiles(prev => prev.map(file =>
            file.id === fileItem.id
              ? { ...file, uploadProgress: progress.percentage }
              : file
          ));
        });

        // Update file status to completed
        setFiles(prev => prev.map(file =>
          file.id === fileItem.id
            ? { ...file, status: 'completed', uploadProgress: 100, url: result.url }
            : file
        ));

        onUploadComplete?.(fileItem.id, result);

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';

        // Update file status to error
        setFiles(prev => prev.map(file =>
          file.id === fileItem.id
            ? { ...file, status: 'error', error: errorMessage }
            : file
        ));

        onUploadError?.(fileItem.id, errorMessage);

      } finally {
        uploadPromisesRef.current.delete(fileItem.id);
      }
    });

    try {
      await Promise.allSettled(uploadPromises);
    } catch (error) {
      console.error('Upload error:', error);
      setError('Some files failed to upload');
    } finally {
      setIsUploading(false);
    }
  }, [files, uploadFunction, onUploadStart, onUploadProgress, onUploadComplete, onUploadError]);

  const removeFile = useCallback((fileId: string) => {
    // Cancel upload if in progress
    const abortController = uploadPromisesRef.current.get(fileId);
    if (abortController) {
      abortController.abort();
      uploadPromisesRef.current.delete(fileId);
    }

    setFiles(prev => {
      const updatedFiles = prev.filter(f => f.id !== fileId);
      const removedFile = prev.find(f => f.id === fileId);

      // Cleanup thumbnail URL
      if (removedFile?.thumbnailUrl) {
        URL.revokeObjectURL(removedFile.thumbnailUrl);
      }

      return updatedFiles;
    });
  }, []);

  const retryUpload = useCallback((fileId: string) => {
    const file = files.find(f => f.id === fileId);
    if (file && file.status === 'error') {
      const updatedFile = { ...file, status: 'pending' as const, error: undefined as string | undefined };
      setFiles(prev => prev.map(f => f.id === fileId ? updatedFile : f));
      uploadFiles([updatedFile]);
    }
  }, [files, uploadFiles]);

  const clearFiles = useCallback(() => {
    // Cancel all ongoing uploads
    uploadPromisesRef.current.forEach(controller => {
      controller.abort();
    });
    uploadPromisesRef.current.clear();

    // Cleanup thumbnail URLs
    files.forEach(file => {
      if (file.thumbnailUrl) {
        URL.revokeObjectURL(file.thumbnailUrl);
      }
    });

    setFiles([]);
    setRejectedFiles([]);
    setError(null);
    setIsUploading(false);
  }, [files]);

  const clearRejectedFiles = useCallback(() => {
    setRejectedFiles([]);
  }, []);

  // Calculate total progress
  const totalProgress = useMemo(() => {
    if (files.length === 0) return 0;

    const totalProgressSum = files.reduce((sum, file) => {
      return sum + (file.uploadProgress || 0);
    }, 0);

    return Math.round(totalProgressSum / files.length);
  }, [files]);

  // Get files by status
  const pendingFiles = useMemo(() => files.filter(f => f.status === 'pending'), [files]);
  const uploadingFiles = useMemo(() => files.filter(f => f.status === 'uploading'), [files]);
  const completedFiles = useMemo(() => files.filter(f => f.status === 'completed'), [files]);
  const errorFiles = useMemo(() => files.filter(f => f.status === 'error'), [files]);

  return {
    // State
    files,
    isUploading,
    error,
    rejectedFiles,
    totalProgress,

    // Filtered files
    pendingFiles,
    uploadingFiles,
    completedFiles,
    errorFiles,

    // Actions
    addFiles,
    uploadFiles,
    removeFile,
    retryUpload,
    clearFiles,
    clearRejectedFiles,

    // Utils
    canAddMoreFiles: files.length < maxFiles,
    hasFiles: files.length > 0,
    hasCompletedFiles: completedFiles.length > 0,
    hasErrorFiles: errorFiles.length > 0,
    hasRejectedFiles: rejectedFiles.length > 0
  };
}

// Utility hook for simple file upload without state management
export function useSimpleFileUpload(uploadFunction: (file: File) => Promise<any>) {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(async (file: File) => {
    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadFunction(file);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setError(errorMessage);
      throw error;
    } finally {
      setIsUploading(false);
    }
  }, [uploadFunction]);

  return {
    upload,
    isUploading,
    error,
    clearError: () => setError(null)
  };
}
