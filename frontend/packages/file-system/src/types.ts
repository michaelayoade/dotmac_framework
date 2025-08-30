export interface FileItem {
  id: string;
  name: string;
  size: number;
  type: string;
  lastModified?: number;
  url?: string;
  thumbnailUrl?: string;
  uploadProgress?: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string | undefined;
}

export interface FileUploadOptions {
  accept?: string[];
  multiple?: boolean;
  maxSize?: number;
  maxFiles?: number;
  directory?: boolean;
  compress?: boolean;
  generateThumbnails?: boolean;
}

export interface DropzoneOptions extends FileUploadOptions {
  disabled?: boolean;
  onDrop?: (files: File[]) => void;
  onReject?: (rejectedFiles: RejectedFile[]) => void;
  onError?: (error: string) => void;
}

export interface RejectedFile {
  file: File;
  reason: 'file-too-large' | 'file-invalid-type' | 'too-many-files' | 'file-too-small';
}

export interface FilePreviewProps {
  file: FileItem | File;
  showActions?: boolean;
  showMetadata?: boolean;
  onRemove?: () => void;
  onDownload?: () => void;
  onClick?: () => void;
  variant?: 'card' | 'list' | 'grid';
  size?: 'sm' | 'md' | 'lg';
}

export interface DocumentCategory {
  id: string;
  name: string;
  count?: number;
  icon?: React.ReactNode;
  description?: string;
}

export interface DocumentFilters {
  category?: string | undefined;
  type?: string[];
  dateRange?: {
    start?: Date | undefined;
    end?: Date | undefined;
  };
  search?: string;
  tags?: string[];
}

export interface DocumentSortOptions {
  field: 'name' | 'date' | 'size' | 'type';
  direction: 'asc' | 'desc';
}

export interface Document extends FileItem {
  category?: string;
  description?: string;
  tags?: string[];
  createdAt: Date;
  updatedAt: Date;
  downloadUrl?: string;
  viewUrl?: string;
  permissions?: {
    read: boolean;
    write: boolean;
    delete: boolean;
    share: boolean;
  };
}

export interface ImageProcessingOptions {
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
  format?: 'jpeg' | 'png' | 'webp';
  maintainAspectRatio?: boolean;
  backgroundColor?: string;
}

export interface ThumbnailOptions {
  width: number;
  height: number;
  fit: 'cover' | 'contain' | 'fill';
  quality?: number;
  format?: 'jpeg' | 'png' | 'webp';
}

export interface FileValidationRule {
  maxSize?: number | undefined;
  minSize?: number | undefined;
  allowedTypes?: string[] | undefined;
  customValidator?: (file: File) => Promise<boolean> | boolean;
  errorMessage?: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
  speed?: number;
  timeRemaining?: number;
}

export interface FileSystemContextValue {
  files: FileItem[];
  uploadFiles: (files: File[], options?: FileUploadOptions) => Promise<void>;
  removeFile: (fileId: string) => void;
  clearFiles: () => void;
  isUploading: boolean;
  totalProgress: number;
  error: string | null;
}

export type FileSystemEventType =
  | 'fileAdded'
  | 'fileRemoved'
  | 'uploadStarted'
  | 'uploadProgress'
  | 'uploadCompleted'
  | 'uploadError'
  | 'filesCleared';

export interface FileSystemEvent {
  type: FileSystemEventType;
  payload?: any;
  timestamp: Date;
}
