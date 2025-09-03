/**
 * Device Hardware Integration Manager
 * Provides unified access to device hardware features
 */

export interface LocationPosition {
  latitude: number;
  longitude: number;
  accuracy: number;
  altitude?: number;
  altitudeAccuracy?: number;
  heading?: number;
  speed?: number;
  timestamp: number;
}

export interface CameraOptions {
  facingMode?: 'user' | 'environment';
  width?: number;
  height?: number;
  aspectRatio?: number;
  frameRate?: number;
}

export interface BiometricOptions {
  reason?: string;
  fallbackLabel?: string;
  disableDeviceFallback?: boolean;
}

export interface DeviceCapabilities {
  geolocation: boolean;
  camera: boolean;
  microphone: boolean;
  accelerometer: boolean;
  gyroscope: boolean;
  magnetometer: boolean;
  vibration: boolean;
  biometrics: boolean;
  nfc: boolean;
  bluetooth: boolean;
}

export class DeviceManager {
  private capabilities: DeviceCapabilities | null = null;
  private watchPositionId: number | null = null;
  private mediaStream: MediaStream | null = null;

  constructor() {
    this.initialize();
  }

  private async initialize(): Promise<void> {
    this.capabilities = await this.detectCapabilities();
  }

  private async detectCapabilities(): Promise<DeviceCapabilities> {
    const capabilities: DeviceCapabilities = {
      geolocation: 'geolocation' in navigator,
      camera: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
      microphone: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
      accelerometer: 'DeviceMotionEvent' in window,
      gyroscope: 'DeviceOrientationEvent' in window,
      magnetometer: 'DeviceOrientationEvent' in window,
      vibration: 'vibrate' in navigator,
      biometrics: 'credentials' in navigator && 'create' in navigator.credentials,
      nfc: 'NDEFReader' in window,
      bluetooth: 'bluetooth' in navigator,
    };

    return capabilities;
  }

  // Geolocation API
  public async getCurrentLocation(options: PositionOptions = {}): Promise<LocationPosition> {
    if (!this.capabilities?.geolocation) {
      throw new Error('Geolocation not supported');
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude ?? undefined,
            altitudeAccuracy: position.coords.altitudeAccuracy ?? undefined,
            heading: position.coords.heading ?? undefined,
            speed: position.coords.speed ?? undefined,
            timestamp: position.timestamp,
          });
        },
        reject,
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000,
          ...options,
        }
      );
    });
  }

  public watchLocation(
    onLocationUpdate: (position: LocationPosition) => void,
    onError: (error: GeolocationPositionError) => void,
    options: PositionOptions = {}
  ): () => void {
    if (!this.capabilities?.geolocation) {
      throw new Error('Geolocation not supported');
    }

    this.watchPositionId = navigator.geolocation.watchPosition(
      (position) => {
        onLocationUpdate({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          altitude: position.coords.altitude ?? undefined,
          altitudeAccuracy: position.coords.altitudeAccuracy ?? undefined,
          heading: position.coords.heading ?? undefined,
          speed: position.coords.speed ?? undefined,
          timestamp: position.timestamp,
        });
      },
      onError,
      {
        enableHighAccuracy: true,
        timeout: 30000,
        maximumAge: 60000,
        ...options,
      }
    );

    return () => {
      if (this.watchPositionId !== null) {
        navigator.geolocation.clearWatch(this.watchPositionId);
        this.watchPositionId = null;
      }
    };
  }

  // Camera API
  public async initializeCamera(options: CameraOptions = {}): Promise<MediaStream> {
    if (!this.capabilities?.camera) {
      throw new Error('Camera not supported');
    }

    const constraints: MediaStreamConstraints = {
      video: {
        facingMode: options.facingMode || 'environment',
        width: options.width ? { ideal: options.width } : undefined,
        height: options.height ? { ideal: options.height } : undefined,
        aspectRatio: options.aspectRatio ? { ideal: options.aspectRatio } : undefined,
        frameRate: options.frameRate ? { ideal: options.frameRate } : undefined,
      },
    };

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      return this.mediaStream;
    } catch (error) {
      throw new Error(`Camera initialization failed: ${error}`);
    }
  }

  public stopCamera(): void {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }
  }

  public async switchCamera(): Promise<MediaStream> {
    const currentFacingMode = this.getCurrentFacingMode();
    const newFacingMode = currentFacingMode === 'user' ? 'environment' : 'user';

    this.stopCamera();
    return this.initializeCamera({ facingMode: newFacingMode });
  }

  private getCurrentFacingMode(): 'user' | 'environment' {
    if (this.mediaStream) {
      const videoTrack = this.mediaStream.getVideoTracks()[0];
      const settings = videoTrack.getSettings();
      return (settings.facingMode as 'user' | 'environment') || 'environment';
    }
    return 'environment';
  }

  // Device Orientation API
  public watchOrientation(
    onOrientationChange: (orientation: DeviceOrientationEvent) => void
  ): () => void {
    if (!this.capabilities?.gyroscope) {
      throw new Error('Device orientation not supported');
    }

    const handleOrientation = (event: DeviceOrientationEvent) => {
      onOrientationChange(event);
    };

    window.addEventListener('deviceorientation', handleOrientation);

    return () => {
      window.removeEventListener('deviceorientation', handleOrientation);
    };
  }

  public async requestOrientationPermission(): Promise<boolean> {
    if ('DeviceOrientationEvent' in window && 'requestPermission' in DeviceOrientationEvent) {
      try {
        const permission = await (DeviceOrientationEvent as any).requestPermission();
        return permission === 'granted';
      } catch (error) {
        console.error('Orientation permission request failed:', error);
        return false;
      }
    }
    return this.capabilities?.gyroscope || false;
  }

  // Motion API
  public watchMotion(onMotionChange: (motion: DeviceMotionEvent) => void): () => void {
    if (!this.capabilities?.accelerometer) {
      throw new Error('Device motion not supported');
    }

    const handleMotion = (event: DeviceMotionEvent) => {
      onMotionChange(event);
    };

    window.addEventListener('devicemotion', handleMotion);

    return () => {
      window.removeEventListener('devicemotion', handleMotion);
    };
  }

  // Vibration API
  public vibrate(pattern: number | number[]): boolean {
    if (!this.capabilities?.vibration) {
      return false;
    }

    try {
      return navigator.vibrate(pattern);
    } catch (error) {
      console.error('Vibration failed:', error);
      return false;
    }
  }

  // Biometric Authentication (WebAuthn)
  public async authenticateWithBiometrics(options: BiometricOptions = {}): Promise<boolean> {
    if (!this.capabilities?.biometrics) {
      throw new Error('Biometric authentication not supported');
    }

    try {
      const credential = await navigator.credentials.create({
        publicKey: {
          challenge: crypto.getRandomValues(new Uint8Array(32)),
          rp: {
            name: 'DotMac ISP Platform',
          },
          user: {
            id: crypto.getRandomValues(new Uint8Array(64)),
            name: 'user@dotmac.com',
            displayName: 'DotMac User',
          },
          pubKeyCredParams: [
            { type: 'public-key', alg: -7 },
            { type: 'public-key', alg: -257 },
          ],
          authenticatorSelection: {
            authenticatorAttachment: 'platform',
            userVerification: 'required',
          },
          timeout: 30000,
        },
      });

      return credential !== null;
    } catch (error) {
      console.error('Biometric authentication failed:', error);
      return false;
    }
  }

  // NFC API (experimental)
  public async readNFC(): Promise<string | null> {
    if (!this.capabilities?.nfc) {
      throw new Error('NFC not supported');
    }

    try {
      const ndef = new (window as any).NDEFReader();
      await ndef.scan();

      return new Promise((resolve, reject) => {
        ndef.addEventListener('reading', (event: any) => {
          const message = event.message;
          if (message.records.length > 0) {
            const textDecoder = new TextDecoder();
            const data = textDecoder.decode(message.records[0].data);
            resolve(data);
          } else {
            resolve(null);
          }
        });

        ndef.addEventListener('error', reject);

        // Timeout after 10 seconds
        setTimeout(() => {
          reject(new Error('NFC read timeout'));
        }, 10000);
      });
    } catch (error) {
      console.error('NFC read failed:', error);
      return null;
    }
  }

  // Bluetooth API (experimental)
  public async scanBluetooth(serviceUUID?: string): Promise<BluetoothDevice | null> {
    if (!this.capabilities?.bluetooth) {
      throw new Error('Bluetooth not supported');
    }

    try {
      const device = await (navigator as any).bluetooth.requestDevice({
        filters: serviceUUID ? [{ services: [serviceUUID] }] : undefined,
        acceptAllDevices: !serviceUUID,
      });

      return device;
    } catch (error) {
      console.error('Bluetooth scan failed:', error);
      return null;
    }
  }

  // Utility methods
  public getCapabilities(): DeviceCapabilities | null {
    return this.capabilities;
  }

  public isCapabilitySupported(capability: keyof DeviceCapabilities): boolean {
    return this.capabilities?.[capability] || false;
  }

  public destroy(): void {
    this.stopCamera();

    if (this.watchPositionId !== null) {
      navigator.geolocation.clearWatch(this.watchPositionId);
      this.watchPositionId = null;
    }
  }
}
