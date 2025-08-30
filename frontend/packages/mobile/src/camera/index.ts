// Core classes
export { CameraManager } from './CameraManager';
export { BarcodeScanner } from './BarcodeScanner';

// React components
export { CameraView } from './components/CameraView';
export { BarcodeScanner as BarcodeScannerComponent } from './components/BarcodeScanner';
export { TechnicianScanner } from './components/TechnicianScanner';

// React hooks
export { useCamera } from './hooks/useCamera';
export { useBarcodeScanner } from './hooks/useBarcodeScanner';

// Workflow utilities
export {
  TechnicianWorkflowScanner,
  type WorkflowType,
  type WorkflowScanResult
} from './utils/TechnicianWorkflowScanner';

// Types
export type {
  CameraCapabilities,
  CameraConfig,
  CameraCaptureResult,
  CameraError,
  CameraPermissionStatus,
  BarcodeResult,
  BarcodeFormat,
  ScannerConfig,
  MediaTrackConstraints
} from './types';
