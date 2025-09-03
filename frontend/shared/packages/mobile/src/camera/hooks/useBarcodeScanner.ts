import { useRef, useState, useCallback, useEffect } from 'react';
import { BarcodeScanner } from '../BarcodeScanner';
import { CameraManager } from '../CameraManager';
import { BarcodeResult, ScannerConfig, CameraError, BarcodeFormat } from '../types';

interface UseBarcodeScannerOptions {
  config?: Partial<ScannerConfig>;
  autoStart?: boolean;
  onResult?: (result: BarcodeResult) => void;
  onError?: (error: CameraError) => void;
}

export function useBarcodeScanner({
  config = {},
  autoStart = false,
  onResult,
  onError,
}: UseBarcodeScannerOptions = {}) {
  const scannerRef = useRef<BarcodeScanner | null>(null);
  const cameraManagerRef = useRef<CameraManager | null>(null);
  const videoElementRef = useRef<HTMLVideoElement | null>(null);

  const [isInitialized, setIsInitialized] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [error, setError] = useState<CameraError | null>(null);
  const [lastResult, setLastResult] = useState<BarcodeResult | null>(null);
  const [scanHistory, setScanHistory] = useState<BarcodeResult[]>([]);
  const [detectedFormats, setDetectedFormats] = useState<Set<BarcodeFormat>>(new Set());

  // Initialize scanner and camera
  useEffect(() => {
    const initialize = async () => {
      try {
        // Initialize camera manager
        const camera = new CameraManager({
          facingMode: 'environment',
          resolution: 'high',
        });
        cameraManagerRef.current = camera;
        await camera.initialize();

        // Initialize barcode scanner
        const scanner = new BarcodeScanner(config);
        scannerRef.current = scanner;

        setIsInitialized(true);
        setError(null);

        if (autoStart && videoElementRef.current) {
          await startScanning(videoElementRef.current);
        }
      } catch (err) {
        const cameraError = err as CameraError;
        setError(cameraError);
        onError?.(cameraError);
      }
    };

    initialize();

    return () => {
      stopScanning();
      if (scannerRef.current) {
        scannerRef.current.dispose();
      }
      if (cameraManagerRef.current) {
        cameraManagerRef.current.dispose();
      }
    };
  }, [config, autoStart, onError]);

  const startCamera = useCallback(
    async (videoElement: HTMLVideoElement) => {
      try {
        if (!cameraManagerRef.current) {
          throw new Error('Camera not initialized');
        }

        videoElementRef.current = videoElement;
        await cameraManagerRef.current.startCamera(videoElement);
        setIsCameraActive(true);
        setError(null);
      } catch (err) {
        const cameraError = err as CameraError;
        setError(cameraError);
        onError?.(cameraError);
      }
    },
    [onError]
  );

  const stopCamera = useCallback(async () => {
    try {
      if (cameraManagerRef.current) {
        await cameraManagerRef.current.stopCamera();
      }
      setIsCameraActive(false);
      videoElementRef.current = null;
    } catch (err) {
      console.warn('Failed to stop camera:', err);
    }
  }, []);

  const startScanning = useCallback(
    async (videoElement?: HTMLVideoElement) => {
      try {
        if (!scannerRef.current || !cameraManagerRef.current) {
          throw new Error('Scanner not initialized');
        }

        // Start camera if not already active
        if (videoElement && !isCameraActive) {
          await startCamera(videoElement);
        }

        if (!videoElementRef.current) {
          throw new Error('Video element not available');
        }

        // Start barcode scanning
        await scannerRef.current.startScanning(
          videoElementRef.current,
          (result: BarcodeResult) => {
            setLastResult(result);
            setScanHistory((prev) => [result, ...prev.slice(0, 19)]); // Keep last 20 results
            setDetectedFormats((prev) => new Set([...prev, result.format]));
            onResult?.(result);
          },
          (error: CameraError) => {
            setError(error);
            onError?.(error);
          }
        );

        setIsScanning(true);
        setError(null);
      } catch (err) {
        const cameraError = err as CameraError;
        setError(cameraError);
        onError?.(cameraError);
      }
    },
    [isCameraActive, startCamera, onResult, onError]
  );

  const stopScanning = useCallback(() => {
    if (scannerRef.current) {
      scannerRef.current.stopScanning();
      setIsScanning(false);
    }
  }, []);

  const switchCamera = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      const wasScanning = isScanning;

      // Stop scanning temporarily
      if (wasScanning) {
        stopScanning();
      }

      // Switch camera
      await cameraManagerRef.current.switchCamera();

      // Resume scanning if it was active
      if (wasScanning && videoElementRef.current) {
        await startScanning();
      }

      setError(null);
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
    }
  }, [isScanning, stopScanning, startScanning, onError]);

  const toggleFlash = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      const currentConfig = cameraManagerRef.current.getConfig();
      await cameraManagerRef.current.setFlash(!currentConfig.enableFlash);
    } catch (err) {
      console.warn('Failed to toggle flash:', err);
    }
  }, []);

  const updateScannerConfig = useCallback((updates: Partial<ScannerConfig>) => {
    if (scannerRef.current) {
      scannerRef.current.updateConfig(updates);
    }
  }, []);

  const clearHistory = useCallback(() => {
    setScanHistory([]);
    setLastResult(null);
    setDetectedFormats(new Set());
  }, []);

  const rescanLastResult = useCallback(async () => {
    if (!lastResult || !videoElementRef.current) {
      return;
    }

    // Temporarily stop and restart scanning to get a fresh scan
    stopScanning();
    await new Promise((resolve) => setTimeout(resolve, 100));
    await startScanning();
  }, [lastResult, stopScanning, startScanning]);

  // Static utility methods
  const detectBarcodesInImage = useCallback(
    async (imageData: ImageData, formats?: BarcodeFormat[]) => {
      return await BarcodeScanner.detectBarcodes(imageData, formats);
    },
    []
  );

  const getCapabilities = useCallback(() => {
    return cameraManagerRef.current?.getCapabilities() || null;
  }, []);

  return {
    // State
    isInitialized,
    isScanning,
    isCameraActive,
    error,
    lastResult,
    scanHistory,
    detectedFormats: Array.from(detectedFormats),

    // Camera controls
    startCamera,
    stopCamera,
    switchCamera,
    toggleFlash,

    // Scanner controls
    startScanning,
    stopScanning,
    updateScannerConfig,

    // Utilities
    clearHistory,
    rescanLastResult,
    detectBarcodesInImage,
    getCapabilities,

    // Computed values
    hasResults: scanHistory.length > 0,
    scanCount: scanHistory.length,
    uniqueFormats: detectedFormats.size,
    isReady: isInitialized && !error,
  };
}
