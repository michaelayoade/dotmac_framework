import { useRef, useState, useCallback, useEffect } from 'react';
import { CameraManager } from '../CameraManager';
import { CameraCapabilities, CameraConfig, CameraCaptureResult, CameraError } from '../types';

interface UseCameraOptions {
  config?: Partial<CameraConfig>;
  autoStart?: boolean;
  onCapture?: (result: CameraCaptureResult) => void;
  onError?: (error: CameraError) => void;
}

export function useCamera({
  config = {},
  autoStart = false,
  onCapture,
  onError,
}: UseCameraOptions = {}) {
  const cameraManagerRef = useRef<CameraManager | null>(null);
  const videoElementRef = useRef<HTMLVideoElement | null>(null);

  const [isInitialized, setIsInitialized] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [capabilities, setCapabilities] = useState<CameraCapabilities | null>(null);
  const [error, setError] = useState<CameraError | null>(null);
  const [isFlashOn, setIsFlashOn] = useState(false);
  const [currentZoom, setCurrentZoom] = useState(1);

  // Initialize camera manager
  useEffect(() => {
    const initializeCamera = async () => {
      try {
        const manager = new CameraManager(config);
        cameraManagerRef.current = manager;

        const caps = await manager.initialize();
        setCapabilities(caps);
        setIsInitialized(true);
        setError(null);

        if (autoStart && videoElementRef.current) {
          await startCamera(videoElementRef.current);
        }
      } catch (err) {
        const cameraError = err as CameraError;
        setError(cameraError);
        onError?.(cameraError);
      }
    };

    initializeCamera();

    return () => {
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
        setIsActive(true);
        setError(null);
      } catch (err) {
        const cameraError = err as CameraError;
        setError(cameraError);
        onError?.(cameraError);
        setIsActive(false);
      }
    },
    [onError]
  );

  const stopCamera = useCallback(async () => {
    try {
      if (cameraManagerRef.current) {
        await cameraManagerRef.current.stopCamera();
      }
      setIsActive(false);
      videoElementRef.current = null;
    } catch (err) {
      console.warn('Failed to stop camera:', err);
    }
  }, []);

  const capturePhoto = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      const result = await cameraManagerRef.current.capturePhoto();
      onCapture?.(result);
      return result;
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
      throw cameraError;
    }
  }, [onCapture, onError]);

  const switchCamera = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      await cameraManagerRef.current.switchCamera();
      setError(null);
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
    }
  }, [onError]);

  const toggleFlash = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      const newFlashState = !isFlashOn;
      await cameraManagerRef.current.setFlash(newFlashState);
      setIsFlashOn(newFlashState);
    } catch (err) {
      console.warn('Failed to toggle flash:', err);
    }
  }, [isFlashOn]);

  const setZoom = useCallback(async (zoom: number) => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      await cameraManagerRef.current.setZoom(zoom);
      setCurrentZoom(zoom);
    } catch (err) {
      console.warn('Failed to set zoom:', err);
    }
  }, []);

  const updateConfig = useCallback((updates: Partial<CameraConfig>) => {
    if (cameraManagerRef.current) {
      cameraManagerRef.current.updateConfig(updates);
    }
  }, []);

  const requestPermissions = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) {
        throw new Error('Camera not initialized');
      }

      return await cameraManagerRef.current.requestPermissions();
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
      throw cameraError;
    }
  }, [onError]);

  return {
    // State
    isInitialized,
    isActive,
    capabilities,
    error,
    isFlashOn,
    currentZoom,

    // Actions
    startCamera,
    stopCamera,
    capturePhoto,
    switchCamera,
    toggleFlash,
    setZoom,
    updateConfig,
    requestPermissions,

    // Computed
    canSwitchCamera: capabilities?.hasFrontCamera && capabilities?.hasBackCamera,
    canUseFlash: capabilities?.supportsFlash,
    canZoom: capabilities?.supportsZoom,
    hasCamera: capabilities?.hasCamera ?? false,
  };
}
