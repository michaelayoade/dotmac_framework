import { CameraCapabilities, CameraConfig, CameraCaptureResult, CameraError, CameraPermissionStatus, MediaTrackConstraints } from './types';

export class CameraManager {
  private stream: MediaStream | null = null;
  private videoElement: HTMLVideoElement | null = null;
  private canvas: HTMLCanvasElement;
  private context: CanvasRenderingContext2D;
  private config: Required<CameraConfig>;
  private capabilities: CameraCapabilities | null = null;

  constructor(config: Partial<CameraConfig> = {}) {
    this.config = {
      facingMode: 'environment',
      resolution: 'high',
      enableFlash: false,
      enableZoom: false,
      captureFormat: 'image/jpeg',
      quality: 0.8,
      ...config
    };

    // Create canvas for image processing
    this.canvas = document.createElement('canvas');
    const context = this.canvas.getContext('2d');
    if (!context) {
      throw new Error('Canvas 2D context not available');
    }
    this.context = context;
  }

  async initialize(): Promise<CameraCapabilities> {
    try {
      // Check for camera support
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API not supported');
      }

      // Detect capabilities
      this.capabilities = await this.detectCapabilities();
      return this.capabilities;
    } catch (error) {
      throw this.createError('DEVICE_NOT_FOUND', 'Failed to initialize camera', error);
    }
  }

  async requestPermissions(): Promise<CameraPermissionStatus> {
    try {
      // Request camera permission
      const cameraPermission = await navigator.permissions.query({ name: 'camera' as PermissionName });

      let microphonePermission: PermissionStatus | undefined;
      let geolocationPermission: PermissionStatus | undefined;

      try {
        microphonePermission = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      } catch (e) {
        // Microphone permission not available
      }

      try {
        geolocationPermission = await navigator.permissions.query({ name: 'geolocation' as PermissionName });
      } catch (e) {
        // Geolocation permission not available
      }

      return {
        camera: cameraPermission.state,
        microphone: microphonePermission?.state,
        geolocation: geolocationPermission?.state
      };
    } catch (error) {
      throw this.createError('PERMISSION_DENIED', 'Failed to check permissions', error);
    }
  }

  async startCamera(videoElement: HTMLVideoElement): Promise<void> {
    try {
      if (this.stream) {
        await this.stopCamera();
      }

      const constraints = this.buildConstraints();
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);

      this.videoElement = videoElement;
      videoElement.srcObject = this.stream;

      // Wait for video to load
      await new Promise<void>((resolve, reject) => {
        const handleLoad = () => {
          videoElement.removeEventListener('loadedmetadata', handleLoad);
          videoElement.removeEventListener('error', handleError);
          resolve();
        };

        const handleError = () => {
          videoElement.removeEventListener('loadedmetadata', handleLoad);
          videoElement.removeEventListener('error', handleError);
          reject(new Error('Failed to load video'));
        };

        videoElement.addEventListener('loadedmetadata', handleLoad);
        videoElement.addEventListener('error', handleError);
      });

      // Start playing
      await videoElement.play();

    } catch (error) {
      throw this.createError('STREAM_ERROR', 'Failed to start camera', error);
    }
  }

  async stopCamera(): Promise<void> {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    if (this.videoElement) {
      this.videoElement.srcObject = null;
      this.videoElement = null;
    }
  }

  async capturePhoto(): Promise<CameraCaptureResult> {
    try {
      if (!this.videoElement || !this.stream) {
        throw new Error('Camera not started');
      }

      const video = this.videoElement;
      const { videoWidth: width, videoHeight: height } = video;

      // Set canvas size
      this.canvas.width = width;
      this.canvas.height = height;

      // Draw video frame to canvas
      this.context.drawImage(video, 0, 0, width, height);

      // Convert to blob
      const blob = await new Promise<Blob>((resolve, reject) => {
        this.canvas.toBlob((blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('Failed to create blob'));
          }
        }, this.config.captureFormat, this.config.quality);
      });

      // Create data URL
      const dataUrl = this.canvas.toDataURL(this.config.captureFormat, this.config.quality);

      // Get metadata
      const metadata = await this.getCaptureMetadata();

      return {
        blob,
        dataUrl,
        width,
        height,
        timestamp: Date.now(),
        metadata
      };

    } catch (error) {
      throw this.createError('CAPTURE_ERROR', 'Failed to capture photo', error);
    }
  }

  async switchCamera(): Promise<void> {
    if (!this.capabilities) {
      throw new Error('Camera not initialized');
    }

    // Toggle between front and back camera
    this.config.facingMode = this.config.facingMode === 'environment' ? 'user' : 'environment';

    if (this.videoElement) {
      await this.startCamera(this.videoElement);
    }
  }

  async setFlash(enabled: boolean): Promise<void> {
    try {
      if (!this.stream || !this.capabilities?.supportsFlash) {
        return;
      }

      const videoTrack = this.stream.getVideoTracks()[0];
      const capabilities = videoTrack.getCapabilities();

      if ('torch' in capabilities) {
        await videoTrack.applyConstraints({
          advanced: [{ torch: enabled } as any]
        });
        this.config.enableFlash = enabled;
      }
    } catch (error) {
      console.warn('Failed to set flash:', error);
    }
  }

  async setZoom(level: number): Promise<void> {
    try {
      if (!this.stream || !this.capabilities?.supportsZoom) {
        return;
      }

      const videoTrack = this.stream.getVideoTracks()[0];
      const capabilities = videoTrack.getCapabilities();

      if ('zoom' in capabilities) {
        const zoomRange = capabilities.zoom as { min: number; max: number; step: number };
        const clampedZoom = Math.max(zoomRange.min, Math.min(zoomRange.max, level));

        await videoTrack.applyConstraints({
          advanced: [{ zoom: clampedZoom } as any]
        });
      }
    } catch (error) {
      console.warn('Failed to set zoom:', error);
    }
  }

  getCapabilities(): CameraCapabilities | null {
    return this.capabilities;
  }

  getConfig(): CameraConfig {
    return { ...this.config };
  }

  updateConfig(updates: Partial<CameraConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  private async detectCapabilities(): Promise<CameraCapabilities> {
    const capabilities: CameraCapabilities = {
      hasCamera: false,
      hasFrontCamera: false,
      hasBackCamera: false,
      supportsFlash: false,
      supportsZoom: false,
      supportedFormats: ['image/jpeg', 'image/png']
    };

    try {
      // Try to enumerate devices
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');

      capabilities.hasCamera = videoDevices.length > 0;

      // Try to determine camera positions
      for (const device of videoDevices) {
        if (device.label.toLowerCase().includes('front') || device.label.toLowerCase().includes('user')) {
          capabilities.hasFrontCamera = true;
        } else if (device.label.toLowerCase().includes('back') || device.label.toLowerCase().includes('environment')) {
          capabilities.hasBackCamera = true;
        }
      }

      // If we can't determine from labels, assume both if multiple cameras
      if (videoDevices.length > 1 && !capabilities.hasFrontCamera && !capabilities.hasBackCamera) {
        capabilities.hasFrontCamera = true;
        capabilities.hasBackCamera = true;
      } else if (videoDevices.length === 1) {
        capabilities.hasBackCamera = true; // Default assumption
      }

      // Test stream capabilities
      try {
        const testStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' }
        });

        const videoTrack = testStream.getVideoTracks()[0];
        const trackCapabilities = videoTrack.getCapabilities();

        capabilities.supportsFlash = 'torch' in trackCapabilities;
        capabilities.supportsZoom = 'zoom' in trackCapabilities;

        if ('width' in trackCapabilities && 'height' in trackCapabilities) {
          const width = trackCapabilities.width as { max?: number };
          const height = trackCapabilities.height as { max?: number };

          if (width.max && height.max) {
            capabilities.maxResolution = { width: width.max, height: height.max };
          }
        }

        // WebP support detection
        if (this.canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0) {
          capabilities.supportedFormats.push('image/webp');
        }

        testStream.getTracks().forEach(track => track.stop());
      } catch (error) {
        // Ignore test stream errors
      }

    } catch (error) {
      console.warn('Failed to detect camera capabilities:', error);
    }

    return capabilities;
  }

  private buildConstraints(): MediaTrackConstraints {
    const resolutionMap = {
      low: { width: 640, height: 480 },
      medium: { width: 1280, height: 720 },
      high: { width: 1920, height: 1080 },
      ultra: { width: 3840, height: 2160 }
    };

    const resolution = resolutionMap[this.config.resolution];

    return {
      video: {
        facingMode: this.config.facingMode,
        width: { ideal: resolution.width },
        height: { ideal: resolution.height },
        frameRate: { ideal: 30 }
      },
      audio: false
    };
  }

  private async getCaptureMetadata() {
    const metadata: any = {
      device: navigator.userAgent,
      orientation: screen.orientation?.angle || 0
    };

    // Get location if available
    if (navigator.geolocation) {
      try {
        metadata.location = await new Promise<GeolocationPosition>((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, {
            timeout: 5000,
            enableHighAccuracy: false
          });
        });
      } catch (error) {
        // Location not available
      }
    }

    return metadata;
  }

  private createError(type: CameraError['type'], message: string, originalError?: any): CameraError {
    return {
      type,
      message,
      details: originalError
    };
  }

  dispose(): void {
    this.stopCamera();
    this.canvas.remove();
  }
}
