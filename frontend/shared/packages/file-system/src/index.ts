// Types
export type * from './types';

// Components
export { FileUpload } from './components/FileUpload/FileUpload';
export { FilePreview } from './components/FilePreview/FilePreview';
export { DocumentManager } from './components/DocumentManager/DocumentManager';
export { ImageProcessor } from './components/ImageProcessor/ImageProcessor';

// Hooks
export { useFileUpload, useSimpleFileUpload } from './hooks/useFileUpload';

// Utils
export {
  formatFileSize,
  getFileExtension,
  getMimeType,
  isImageFile,
  isDocumentFile,
  isVideoFile,
  isAudioFile,
  validateFiles,
  fileToDataURL,
  dataURLToBlob,
  generateFileId,
  calculateUploadSpeed,
  estimateTimeRemaining,
  createThumbnail,
  processImage,
  getFileIcon,
} from './utils/fileUtils';
