/**
 * React Hook for Device Hardware Integration
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  DeviceManager,
  LocationPosition,
  CameraOptions,
  BiometricOptions,
  DeviceCapabilities,
} from './DeviceManager';

export function useDevice() {
  const [deviceManager] = useState(() => new DeviceManager());
  const [capabilities, setCapabilities] = useState<DeviceCapabilities | null>(null);

  useEffect(() => {
    const loadCapabilities = async () => {
      // Wait for initialization
      await new Promise((resolve) => setTimeout(resolve, 100));
      setCapabilities(deviceManager.getCapabilities());
    };

    loadCapabilities();

    return () => {
      deviceManager.destroy();
    };
  }, [deviceManager]);

  return {
    deviceManager,
    capabilities,
    isSupported: (capability: keyof DeviceCapabilities) =>
      deviceManager.isCapabilitySupported(capability),
  };
}

export function useGeolocation() {
  const { deviceManager, isSupported } = useDevice();
  const [position, setPosition] = useState<LocationPosition | null>(null);
  const [error, setError] = useState<GeolocationPositionError | null>(null);
  const [loading, setLoading] = useState(false);
  const watchStopRef = useRef<(() => void) | null>(null);

  const getCurrentLocation = useCallback(
    async (options?: PositionOptions) => {
      if (!isSupported('geolocation')) {
        setError(new Error('Geolocation not supported') as GeolocationPositionError);
        return null;
      }

      setLoading(true);
      setError(null);

      try {
        const pos = await deviceManager.getCurrentLocation(options);
        setPosition(pos);
        return pos;
      } catch (err) {
        setError(err as GeolocationPositionError);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [deviceManager, isSupported]
  );

  const watchPosition = useCallback(
    (options?: PositionOptions) => {
      if (!isSupported('geolocation')) {
        setError(new Error('Geolocation not supported') as GeolocationPositionError);
        return () => {};
      }

      stopWatching();

      const stopWatching = deviceManager.watchLocation(
        (pos) => {
          setPosition(pos);
          setError(null);
        },
        (err) => setError(err),
        options
      );

      watchStopRef.current = stopWatching;
      return stopWatching;
    },
    [deviceManager, isSupported]
  );

  const stopWatching = useCallback(() => {
    if (watchStopRef.current) {
      watchStopRef.current();
      watchStopRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopWatching();
    };
  }, [stopWatching]);

  return {
    position,
    error,
    loading,
    supported: isSupported('geolocation'),
    getCurrentLocation,
    watchPosition,
    stopWatching,
  };
}

export function useCamera() {
  const { deviceManager, isSupported } = useDevice();
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');

  const initializeCamera = useCallback(
    async (options: CameraOptions = {}) => {
      if (!isSupported('camera')) {
        setError('Camera not supported');
        return null;
      }

      setLoading(true);
      setError(null);

      try {
        const mediaStream = await deviceManager.initializeCamera({
          facingMode,
          ...options,
        });
        setStream(mediaStream);
        return mediaStream;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Camera initialization failed');
        return null;
      } finally {
        setLoading(false);
      }
    },
    [deviceManager, isSupported, facingMode]
  );

  const switchCamera = useCallback(async () => {
    if (!isSupported('camera') || loading) return null;

    setLoading(true);
    setError(null);

    try {
      const mediaStream = await deviceManager.switchCamera();
      setStream(mediaStream);
      setFacingMode(facingMode === 'user' ? 'environment' : 'user');
      return mediaStream;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Camera switch failed');
      return null;
    } finally {
      setLoading(false);
    }
  }, [deviceManager, isSupported, loading, facingMode]);

  const stopCamera = useCallback(() => {
    deviceManager.stopCamera();
    setStream(null);
    setError(null);
  }, [deviceManager]);

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    stream,
    error,
    loading,
    facingMode,
    supported: isSupported('camera'),
    initializeCamera,
    switchCamera,
    stopCamera,
  };
}

export function useDeviceOrientation() {
  const { deviceManager, isSupported } = useDevice();
  const [orientation, setOrientation] = useState<DeviceOrientationEvent | null>(null);
  const [permission, setPermission] = useState<boolean | null>(null);
  const watchStopRef = useRef<(() => void) | null>(null);

  const requestPermission = useCallback(async () => {
    if (!isSupported('gyroscope')) {
      setPermission(false);
      return false;
    }

    try {
      const granted = await deviceManager.requestOrientationPermission();
      setPermission(granted);
      return granted;
    } catch (error) {
      setPermission(false);
      return false;
    }
  }, [deviceManager, isSupported]);

  const startWatching = useCallback(() => {
    if (!isSupported('gyroscope') || !permission) {
      return () => {};
    }

    stopWatching();

    const stopFn = deviceManager.watchOrientation((orientationEvent) => {
      setOrientation(orientationEvent);
    });

    watchStopRef.current = stopFn;
    return stopFn;
  }, [deviceManager, isSupported, permission]);

  const stopWatching = useCallback(() => {
    if (watchStopRef.current) {
      watchStopRef.current();
      watchStopRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopWatching();
    };
  }, [stopWatching]);

  return {
    orientation,
    permission,
    supported: isSupported('gyroscope'),
    requestPermission,
    startWatching,
    stopWatching,
  };
}

export function useDeviceMotion() {
  const { deviceManager, isSupported } = useDevice();
  const [motion, setMotion] = useState<DeviceMotionEvent | null>(null);
  const watchStopRef = useRef<(() => void) | null>(null);

  const startWatching = useCallback(() => {
    if (!isSupported('accelerometer')) {
      return () => {};
    }

    stopWatching();

    const stopFn = deviceManager.watchMotion((motionEvent) => {
      setMotion(motionEvent);
    });

    watchStopRef.current = stopFn;
    return stopFn;
  }, [deviceManager, isSupported]);

  const stopWatching = useCallback(() => {
    if (watchStopRef.current) {
      watchStopRef.current();
      watchStopRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopWatching();
    };
  }, [stopWatching]);

  return {
    motion,
    supported: isSupported('accelerometer'),
    startWatching,
    stopWatching,
  };
}

export function useVibration() {
  const { deviceManager, isSupported } = useDevice();

  const vibrate = useCallback(
    (pattern: number | number[]) => {
      if (!isSupported('vibration')) {
        return false;
      }

      return deviceManager.vibrate(pattern);
    },
    [deviceManager, isSupported]
  );

  const vibratePattern = useCallback(
    (type: 'success' | 'error' | 'warning' | 'info') => {
      const patterns = {
        success: [100, 50, 100],
        error: [200, 100, 200, 100, 200],
        warning: [150, 75, 150],
        info: [100],
      };

      return vibrate(patterns[type]);
    },
    [vibrate]
  );

  return {
    vibrate,
    vibratePattern,
    supported: isSupported('vibration'),
  };
}

export function useBiometrics() {
  const { deviceManager, isSupported } = useDevice();
  const [loading, setLoading] = useState(false);

  const authenticate = useCallback(
    async (options: BiometricOptions = {}) => {
      if (!isSupported('biometrics')) {
        throw new Error('Biometric authentication not supported');
      }

      setLoading(true);
      try {
        return await deviceManager.authenticateWithBiometrics(options);
      } finally {
        setLoading(false);
      }
    },
    [deviceManager, isSupported]
  );

  return {
    authenticate,
    loading,
    supported: isSupported('biometrics'),
  };
}
