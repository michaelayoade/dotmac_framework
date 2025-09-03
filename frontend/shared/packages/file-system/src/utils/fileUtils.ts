import type {
  FileValidationRule,
  RejectedFile,
  ThumbnailOptions,
  ImageProcessingOptions,
} from '../types';

// Re-export file size formatter from utils package
export { formatFileSize } from '@dotmac/utils/formatting';

/**
 * Get file extension from filename
 */
export function getFileExtension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() || '';
}

/**
 * Get MIME type from file extension
 */
export function getMimeType(extension: string): string {
  const mimeTypes: Record<string, string> = {
    // Images
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    gif: 'image/gif',
    webp: 'image/webp',
    svg: 'image/svg+xml',

    // Documents
    pdf: 'application/pdf',
    doc: 'application/msword',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    xls: 'application/vnd.ms-excel',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ppt: 'application/vnd.ms-powerpoint',
    pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    txt: 'text/plain',

    // Archives
    zip: 'application/zip',
    rar: 'application/vnd.rar',
    '7z': 'application/x-7z-compressed',

    // Audio
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    ogg: 'audio/ogg',

    // Video
    mp4: 'video/mp4',
    avi: 'video/x-msvideo',
    mov: 'video/quicktime',
    wmv: 'video/x-ms-wmv',
  };

  return mimeTypes[extension] || 'application/octet-stream';
}

/**
 * Check if file is an image
 */
export function isImageFile(file: File | string): boolean {
  const mimeType = typeof file === 'string' ? file : file.type;
  return mimeType.startsWith('image/');
}

/**
 * Check if file is a document
 */
export function isDocumentFile(file: File | string): boolean {
  const mimeType = typeof file === 'string' ? file : file.type;
  const documentTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/csv',
  ];

  return documentTypes.includes(mimeType);
}

/**
 * Check if file is a video
 */
export function isVideoFile(file: File | string): boolean {
  const mimeType = typeof file === 'string' ? file : file.type;
  return mimeType.startsWith('video/');
}

/**
 * Check if file is an audio file
 */
export function isAudioFile(file: File | string): boolean {
  const mimeType = typeof file === 'string' ? file : file.type;
  return mimeType.startsWith('audio/');
}

/**
 * Validate files against rules
 */
export async function validateFiles(
  files: File[],
  rules: FileValidationRule[]
): Promise<{ accepted: File[]; rejected: RejectedFile[] }> {
  const accepted: File[] = [];
  const rejected: RejectedFile[] = [];

  for (const file of files) {
    let isValid = true;
    let rejectReason: RejectedFile['reason'] = 'file-invalid-type';

    for (const rule of rules) {
      // Check file size
      if (rule.maxSize && file.size > rule.maxSize) {
        isValid = false;
        rejectReason = 'file-too-large';
        break;
      }

      if (rule.minSize && file.size < rule.minSize) {
        isValid = false;
        rejectReason = 'file-too-small';
        break;
      }

      // Check file type
      if (rule.allowedTypes && rule.allowedTypes.length > 0) {
        const isAllowed = rule.allowedTypes.some((type) => {
          if (type.startsWith('.')) {
            return file.name.toLowerCase().endsWith(type.toLowerCase());
          }
          return file.type.includes(type);
        });

        if (!isAllowed) {
          isValid = false;
          rejectReason = 'file-invalid-type';
          break;
        }
      }

      // Custom validation
      if (rule.customValidator) {
        try {
          const customValid = await rule.customValidator(file);
          if (!customValid) {
            isValid = false;
            rejectReason = 'file-invalid-type';
            break;
          }
        } catch (error) {
          isValid = false;
          rejectReason = 'file-invalid-type';
          break;
        }
      }
    }

    if (isValid) {
      accepted.push(file);
    } else {
      rejected.push({ file, reason: rejectReason });
    }
  }

  return { accepted, rejected };
}

/**
 * Convert file to data URL
 */
export function fileToDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Convert data URL to blob
 */
export function dataURLToBlob(dataURL: string): Blob {
  const arr = dataURL.split(',');
  const mimeMatch = arr[0]?.match(/:(.*?);/);
  const mime = mimeMatch?.[1] || 'application/octet-stream';
  if (!arr[1]) {
    throw new Error('Invalid data URL');
  }
  const bstr = atob(arr[1]);
  const n = bstr.length;
  const u8arr = new Uint8Array(n);

  for (let i = 0; i < n; i++) {
    u8arr[i] = bstr.charCodeAt(i);
  }

  return new Blob([u8arr], { type: mime });
}

/**
 * Generate unique file ID
 */
export function generateFileId(file: File): string {
  return `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Calculate upload speed
 */
export function calculateUploadSpeed(loaded: number, timeElapsed: number): number {
  if (timeElapsed === 0) return 0;
  return loaded / (timeElapsed / 1000); // bytes per second
}

/**
 * Estimate remaining time
 */
export function estimateTimeRemaining(loaded: number, total: number, speed: number): number {
  if (speed === 0) return 0;
  const remaining = total - loaded;
  return remaining / speed; // seconds
}

/**
 * Create thumbnail for image file
 */
export function createThumbnail(file: File, options: ThumbnailOptions): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!isImageFile(file)) {
      reject(new Error('File is not an image'));
      return;
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      const { width, height, fit } = options;

      // Calculate dimensions based on fit type
      let targetWidth = width;
      let targetHeight = height;
      let sourceX = 0;
      let sourceY = 0;
      let sourceWidth = img.width;
      let sourceHeight = img.height;

      if (fit === 'cover') {
        const scale = Math.max(width / img.width, height / img.height);
        sourceWidth = width / scale;
        sourceHeight = height / scale;
        sourceX = (img.width - sourceWidth) / 2;
        sourceY = (img.height - sourceHeight) / 2;
      } else if (fit === 'contain') {
        const scale = Math.min(width / img.width, height / img.height);
        targetWidth = img.width * scale;
        targetHeight = img.height * scale;
      }

      canvas.width = targetWidth;
      canvas.height = targetHeight;

      if (!ctx) {
        reject(new Error('Could not get canvas context'));
        return;
      }

      // Fill background for transparent images
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, targetWidth, targetHeight);

      ctx.drawImage(
        img,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        0,
        0,
        targetWidth,
        targetHeight
      );

      const quality = (options.quality || 80) / 100;
      const format = options.format || 'jpeg';
      const dataURL = canvas.toDataURL(`image/${format}`, quality);

      resolve(dataURL);
    };

    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = URL.createObjectURL(file);
  });
}

/**
 * Process image file
 */
export function processImage(file: File, options: ImageProcessingOptions): Promise<Blob> {
  return new Promise((resolve, reject) => {
    if (!isImageFile(file)) {
      reject(new Error('File is not an image'));
      return;
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    img.onload = () => {
      let { width, height } = img;
      const {
        maxWidth,
        maxHeight,
        maintainAspectRatio = true,
        backgroundColor = 'transparent',
        quality = 80,
        format = 'jpeg',
      } = options;

      // Calculate new dimensions
      if (maxWidth || maxHeight) {
        if (maintainAspectRatio) {
          const ratio = Math.min(
            maxWidth ? maxWidth / width : Infinity,
            maxHeight ? maxHeight / height : Infinity
          );
          width *= ratio;
          height *= ratio;
        } else {
          width = maxWidth || width;
          height = maxHeight || height;
        }
      }

      canvas.width = width;
      canvas.height = height;

      if (!ctx) {
        reject(new Error('Could not get canvas context'));
        return;
      }

      // Set background color
      if (backgroundColor !== 'transparent') {
        ctx.fillStyle = backgroundColor;
        ctx.fillRect(0, 0, width, height);
      }

      ctx.drawImage(img, 0, 0, width, height);

      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to process image'));
          }
        },
        `image/${format}`,
        quality / 100
      );
    };

    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = URL.createObjectURL(file);
  });
}

/**
 * Get file icon based on type
 */
export function getFileIcon(file: File | string): string {
  const mimeType = typeof file === 'string' ? file : file.type;
  const extension =
    typeof file === 'string' ? file.split('.').pop()?.toLowerCase() : getFileExtension(file.name);

  // Image files
  if (mimeType.startsWith('image/')) {
    return 'image';
  }

  // Document files
  if (mimeType === 'application/pdf') return 'file-text';
  if (mimeType.includes('word')) return 'file-text';
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'table';
  if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'presentation';

  // Archive files
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(extension || '')) {
    return 'archive';
  }

  // Audio files
  if (mimeType.startsWith('audio/')) {
    return 'music';
  }

  // Video files
  if (mimeType.startsWith('video/')) {
    return 'video';
  }

  // Code files
  if (['js', 'ts', 'jsx', 'tsx', 'html', 'css', 'json', 'xml'].includes(extension || '')) {
    return 'code';
  }

  return 'file';
}
