export interface CameraCapabilities {
  hasCamera: boolean;
  hasFrontCamera: boolean;
  hasBackCamera: boolean;
  supportsFlash: boolean;
  supportsZoom: boolean;
  supportedFormats: string[];
  maxResolution?: { width: number; height: number };
}

export interface CameraConfig {
  facingMode: 'user' | 'environment' | 'left' | 'right';
  resolution: 'low' | 'medium' | 'high' | 'ultra';
  enableFlash: boolean;
  enableZoom: boolean;
  captureFormat: 'image/jpeg' | 'image/png' | 'image/webp';
  quality: number; // 0-1
}

export interface CameraCaptureResult {
  blob: Blob;
  dataUrl: string;
  width: number;
  height: number;
  timestamp: number;
  metadata?: {
    device: string;
    location?: GeolocationPosition;
    orientation: number;
  };
}

export interface BarcodeResult {
  data: string;
  format: BarcodeFormat;
  quality: number;
  corners?: Array<{ x: number; y: number }>;
  timestamp: number;
}

export type BarcodeFormat =
  | 'QR_CODE'
  | 'DATA_MATRIX'
  | 'CODE_128'
  | 'CODE_39'
  | 'CODE_93'
  | 'CODEBAR'
  | 'EAN_13'
  | 'EAN_8'
  | 'ITF'
  | 'UPC_A'
  | 'UPC_E'
  | 'PDF_417'
  | 'AZTEC'
  | 'UNKNOWN';

export interface ScannerConfig {
  formats: BarcodeFormat[];
  continuous: boolean;
  beep: boolean;
  vibrate: boolean;
  torch: boolean;
  overlay: boolean;
  cropRect?: { x: number; y: number; width: number; height: number };
  timeout?: number; // ms
}

export interface CameraError {
  type:
    | 'PERMISSION_DENIED'
    | 'DEVICE_NOT_FOUND'
    | 'STREAM_ERROR'
    | 'CAPTURE_ERROR'
    | 'SCANNER_ERROR';
  message: string;
  code?: number;
  details?: any;
}

export interface CameraPermissionStatus {
  camera: PermissionState;
  microphone?: PermissionState;
  geolocation?: PermissionState;
}

export interface MediaTrackConstraints extends MediaStreamConstraints {
  video: {
    facingMode?: string;
    width?: { min?: number; ideal?: number; max?: number };
    height?: { min?: number; ideal?: number; max?: number };
    frameRate?: { min?: number; ideal?: number; max?: number };
    aspectRatio?: number;
    torch?: boolean;
    zoom?: number;
  };
}
