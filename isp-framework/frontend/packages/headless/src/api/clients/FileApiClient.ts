/**
 * File Upload/Download API Client
 * Handles all file operations including upload, download, management, and processing
 * with support for multipart uploads, resumable uploads, and various file types
 */

import { BaseApiClient } from './BaseApiClient';
import type { ApiResponse, PaginatedResponse } from '../types/api';

// File interfaces
export interface FileData {
  id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  size: number;
  checksum: string;
  purpose: FilePurpose;
  status: FileStatus;
  url?: string;
  thumbnail_url?: string;
  metadata?: Record<string, any>;
  expiry_date?: string;
  owner_id: string;
  owner_type: 'user' | 'customer' | 'system';
  visibility: 'private' | 'public' | 'tenant';
  created_at: string;
  updated_at: string;
}

export type FilePurpose =
  | 'avatar'
  | 'document'
  | 'invoice'
  | 'contract'
  | 'network_diagram'
  | 'support_attachment'
  | 'backup'
  | 'import'
  | 'export'
  | 'report'
  | 'certificate'
  | 'configuration'
  | 'temporary';

export type FileStatus =
  | 'uploading'
  | 'processing'
  | 'ready'
  | 'failed'
  | 'expired'
  | 'deleted';

export interface UploadRequest {
  file: File;
  purpose: FilePurpose;
  visibility?: FileData['visibility'];
  metadata?: Record<string, any>;
  expiry_hours?: number;
  generate_thumbnail?: boolean;
}

export interface MultipartUploadInitRequest {
  filename: string;
  size: number;
  mime_type: string;
  purpose: FilePurpose;
  chunk_size?: number;
  visibility?: FileData['visibility'];
  metadata?: Record<string, any>;
}

export interface MultipartUploadResponse {
  upload_id: string;
  chunk_size: number;
  total_chunks: number;
  urls: string[];
}

export interface UploadChunkRequest {
  upload_id: string;
  chunk_index: number;
  chunk: Blob;
  checksum?: string;
}

export interface CompleteMultipartUploadRequest {
  upload_id: string;
  chunks: Array<{
    index: number;
    checksum: string;
  }>;
}

export interface BulkUploadRequest {
  files: Array<{
    file: File;
    purpose: FilePurpose;
    metadata?: Record<string, any>;
  }>;
  visibility?: FileData['visibility'];
}

export interface DownloadRequest {
  file_id: string;
  inline?: boolean;
  version?: string;
}

export interface GenerateLinkRequest {
  file_id: string;
  expires_in_hours?: number;
  download_limit?: number;
  password?: string;
}

export interface ShareLinkData {
  id: string;
  url: string;
  expires_at: string;
  download_limit?: number;
  download_count: number;
  password_protected: boolean;
  created_at: string;
}

export interface FileSearchParams {
  query?: string;
  purpose?: FilePurpose[];
  status?: FileStatus[];
  owner_id?: string;
  owner_type?: FileData['owner_type'];
  mime_type?: string[];
  size_min?: number;
  size_max?: number;
  created_after?: string;
  created_before?: string;
  page?: number;
  limit?: number;
  sort?: 'filename' | 'size' | 'created_at' | 'updated_at';
  order?: 'asc' | 'desc';
}

export interface FileProcessingJob {
  id: string;
  file_id: string;
  job_type: 'thumbnail' | 'compress' | 'convert' | 'extract' | 'scan';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: any;
  error?: string;
  created_at: string;
  completed_at?: string;
}

export class FileApiClient extends BaseApiClient {
  constructor(baseURL: string, defaultHeaders: Record<string, string> = {}) {
    super(baseURL, defaultHeaders, 'FileAPI');
  }

  /**
   * Upload a single file
   */
  async uploadFile(request: UploadRequest, onProgress?: (progress: number) => void): Promise<ApiResponse<FileData>> {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('purpose', request.purpose);
    
    if (request.visibility) {
      formData.append('visibility', request.visibility);
    }
    if (request.metadata) {
      formData.append('metadata', JSON.stringify(request.metadata));
    }
    if (request.expiry_hours) {
      formData.append('expiry_hours', request.expiry_hours.toString());
    }
    if (request.generate_thumbnail !== undefined) {
      formData.append('generate_thumbnail', request.generate_thumbnail.toString());
    }

    // For progress tracking, we need to use XMLHttpRequest
    if (onProgress) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded / event.total) * 100);
            onProgress(progress);
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              resolve({
                data: response.data,
                status: xhr.status,
                statusText: xhr.statusText,
                headers: new Headers()
              });
            } catch (error) {
              reject(new Error('Invalid JSON response'));
            }
          } else {
            reject(new Error(`Upload failed: ${xhr.statusText}`));
          }
        });

        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'));
        });

        xhr.open('POST', `${this.baseURL}/files/upload`);
        
        // Add headers
        Object.entries(this.defaultHeaders).forEach(([key, value]) => {
          xhr.setRequestHeader(key, value);
        });

        xhr.send(formData);
      });
    }

    // Standard fetch for non-progress uploads
    return this.request<FileData>('POST', '/files/upload', formData, {
      headers: {} // Let browser set Content-Type for FormData
    });
  }

  /**
   * Initialize multipart upload for large files
   */
  async initMultipartUpload(request: MultipartUploadInitRequest): Promise<ApiResponse<MultipartUploadResponse>> {
    return this.request<MultipartUploadResponse>('POST', '/files/multipart/init', request);
  }

  /**
   * Upload a chunk of a multipart upload
   */
  async uploadChunk(request: UploadChunkRequest): Promise<ApiResponse<{ success: boolean; checksum: string }>> {
    const formData = new FormData();
    formData.append('upload_id', request.upload_id);
    formData.append('chunk_index', request.chunk_index.toString());
    formData.append('chunk', request.chunk);
    if (request.checksum) {
      formData.append('checksum', request.checksum);
    }

    return this.request<{ success: boolean; checksum: string }>('POST', '/files/multipart/chunk', formData, {
      headers: {} // Let browser set Content-Type for FormData
    });
  }

  /**
   * Complete multipart upload
   */
  async completeMultipartUpload(request: CompleteMultipartUploadRequest): Promise<ApiResponse<FileData>> {
    return this.request<FileData>('POST', '/files/multipart/complete', request);
  }

  /**
   * Abort multipart upload
   */
  async abortMultipartUpload(uploadId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('DELETE', `/files/multipart/${uploadId}`);
  }

  /**
   * Upload multiple files at once
   */
  async bulkUpload(request: BulkUploadRequest): Promise<ApiResponse<{
    successful: FileData[];
    failed: Array<{ filename: string; error: string }>;
  }>> {
    const formData = new FormData();
    
    request.files.forEach((fileRequest, index) => {
      formData.append(`files[${index}]`, fileRequest.file);
      formData.append(`purposes[${index}]`, fileRequest.purpose);
      if (fileRequest.metadata) {
        formData.append(`metadata[${index}]`, JSON.stringify(fileRequest.metadata));
      }
    });

    if (request.visibility) {
      formData.append('visibility', request.visibility);
    }

    return this.request<{
      successful: FileData[];
      failed: Array<{ filename: string; error: string }>;
    }>('POST', '/files/bulk-upload', formData, {
      headers: {} // Let browser set Content-Type for FormData
    });
  }

  /**
   * Get file information
   */
  async getFile(fileId: string): Promise<ApiResponse<FileData>> {
    return this.request<FileData>('GET', `/files/${fileId}`);
  }

  /**
   * Search and list files
   */
  async searchFiles(params: FileSearchParams = {}): Promise<PaginatedResponse<FileData>> {
    return this.request<PaginatedResponse<FileData>>('GET', '/files', null, { params });
  }

  /**
   * Download a file
   */
  async downloadFile(request: DownloadRequest): Promise<Blob> {
    const params = new URLSearchParams();
    if (request.inline !== undefined) {
      params.set('inline', request.inline.toString());
    }
    if (request.version) {
      params.set('version', request.version);
    }

    const queryString = params.toString();
    const url = `${this.baseURL}/files/${request.file_id}/download${queryString ? `?${queryString}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: this.defaultHeaders,
      signal: this.createTimeoutSignal(30000) // 30 second timeout for downloads
    });

    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }

    return response.blob();
  }

  /**
   * Generate a shareable download link
   */
  async generateShareLink(request: GenerateLinkRequest): Promise<ApiResponse<ShareLinkData>> {
    return this.request<ShareLinkData>('POST', `/files/${request.file_id}/share`, {
      expires_in_hours: request.expires_in_hours,
      download_limit: request.download_limit,
      password: request.password
    });
  }

  /**
   * Get share link information
   */
  async getShareLink(linkId: string): Promise<ApiResponse<ShareLinkData>> {
    return this.request<ShareLinkData>('GET', `/files/share/${linkId}`);
  }

  /**
   * Revoke a share link
   */
  async revokeShareLink(linkId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('DELETE', `/files/share/${linkId}`);
  }

  /**
   * Update file metadata
   */
  async updateFile(fileId: string, updates: {
    filename?: string;
    metadata?: Record<string, any>;
    visibility?: FileData['visibility'];
    expiry_date?: string;
  }): Promise<ApiResponse<FileData>> {
    return this.request<FileData>('PATCH', `/files/${fileId}`, updates);
  }

  /**
   * Delete a file
   */
  async deleteFile(fileId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('DELETE', `/files/${fileId}`);
  }

  /**
   * Bulk delete files
   */
  async bulkDeleteFiles(fileIds: string[]): Promise<ApiResponse<{
    deleted: string[];
    failed: Array<{ file_id: string; error: string }>;
  }>> {
    return this.request<{
      deleted: string[];
      failed: Array<{ file_id: string; error: string }>;
    }>('DELETE', '/files/bulk', { file_ids: fileIds });
  }

  /**
   * Get file processing jobs
   */
  async getProcessingJobs(fileId?: string): Promise<ApiResponse<FileProcessingJob[]>> {
    const endpoint = fileId ? `/files/${fileId}/jobs` : '/files/jobs';
    return this.request<FileProcessingJob[]>('GET', endpoint);
  }

  /**
   * Start file processing job
   */
  async startProcessingJob(fileId: string, jobType: FileProcessingJob['job_type'], options?: Record<string, any>): Promise<ApiResponse<FileProcessingJob>> {
    return this.request<FileProcessingJob>('POST', `/files/${fileId}/process`, {
      job_type: jobType,
      options
    });
  }

  /**
   * Get processing job status
   */
  async getProcessingJobStatus(jobId: string): Promise<ApiResponse<FileProcessingJob>> {
    return this.request<FileProcessingJob>('GET', `/files/jobs/${jobId}`);
  }

  /**
   * Cancel processing job
   */
  async cancelProcessingJob(jobId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request<{ message: string }>('DELETE', `/files/jobs/${jobId}`);
  }

  /**
   * Get storage usage statistics
   */
  async getStorageStats(): Promise<ApiResponse<{
    total_files: number;
    total_size: number;
    used_space: number;
    available_space?: number;
    files_by_purpose: Record<FilePurpose, { count: number; size: number }>;
    files_by_status: Record<FileStatus, number>;
  }>> {
    return this.request<any>('GET', '/files/stats');
  }

  /**
   * Clean up expired files
   */
  async cleanupExpiredFiles(): Promise<ApiResponse<{
    cleaned_count: number;
    freed_space: number;
  }>> {
    return this.request<any>('POST', '/files/cleanup');
  }

  /**
   * Private method to create timeout signal (inherited from BaseApiClient)
   */
  private createTimeoutSignal(timeout: number): AbortSignal {
    if (typeof AbortSignal.timeout === 'function') {
      return AbortSignal.timeout(timeout);
    }
    
    const controller = new AbortController();
    setTimeout(() => controller.abort(), timeout);
    return controller.signal;
  }
}