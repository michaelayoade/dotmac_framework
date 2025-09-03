import React, { useRef, useEffect, useState, useCallback } from 'react';
import { CameraManager } from '../CameraManager';
import { CameraCapabilities, CameraConfig, CameraCaptureResult, CameraError } from '../types';

interface CameraViewProps {
  config?: Partial<CameraConfig>;
  onCapture?: (result: CameraCaptureResult) => void;
  onError?: (error: CameraError) => void;
  onReady?: (capabilities: CameraCapabilities) => void;
  className?: string;
  showControls?: boolean;
  autoStart?: boolean;
}

export function CameraView({
  config = {},
  onCapture,
  onError,
  onReady,
  className = '',
  showControls = true,
  autoStart = true,
}: CameraViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraManagerRef = useRef<CameraManager | null>(null);

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
        onReady?.(caps);

        if (autoStart) {
          await startCamera();
        }
      } catch (err) {
        const cameraError = err as CameraError;
        setError(cameraError);
        onError?.(cameraError);
      }
    };

    initializeCamera();

    return () => {
      stopCamera();
      cameraManagerRef.current?.dispose();
    };
  }, []);

  const startCamera = useCallback(async () => {
    try {
      if (!cameraManagerRef.current || !videoRef.current) return;

      await cameraManagerRef.current.startCamera(videoRef.current);
      setIsActive(true);
      setError(null);
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
    }
  }, [onError]);

  const stopCamera = useCallback(() => {
    if (cameraManagerRef.current) {
      cameraManagerRef.current.stopCamera();
      setIsActive(false);
    }
  }, []);

  const capturePhoto = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) return;

      const result = await cameraManagerRef.current.capturePhoto();
      onCapture?.(result);
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
    }
  }, [onCapture, onError]);

  const switchCamera = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) return;

      await cameraManagerRef.current.switchCamera();
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
    }
  }, [onError]);

  const toggleFlash = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) return;

      const newFlashState = !isFlashOn;
      await cameraManagerRef.current.setFlash(newFlashState);
      setIsFlashOn(newFlashState);
    } catch (err) {
      console.warn('Failed to toggle flash:', err);
    }
  }, [isFlashOn]);

  const handleZoomChange = useCallback(async (zoom: number) => {
    try {
      if (!cameraManagerRef.current) return;

      await cameraManagerRef.current.setZoom(zoom);
      setCurrentZoom(zoom);
    } catch (err) {
      console.warn('Failed to set zoom:', err);
    }
  }, []);

  if (error) {
    return (
      <div className={`camera-view camera-view--error ${className}`}>
        <div className='camera-error'>
          <div className='camera-error__icon'>📷</div>
          <div className='camera-error__message'>{error.message}</div>
          <button
            className='camera-error__retry'
            onClick={() => {
              setError(null);
              startCamera();
            }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`camera-view ${isActive ? 'camera-view--active' : ''} ${className}`}>
      <div className='camera-preview'>
        <video ref={videoRef} className='camera-video' playsInline muted autoPlay />

        {/* Camera overlay */}
        <div className='camera-overlay'>
          {/* Focus indicator */}
          <div className='camera-focus-indicator' />

          {/* Flash indicator */}
          {isFlashOn && <div className='camera-flash-indicator'>⚡</div>}
        </div>
      </div>

      {showControls && (
        <div className='camera-controls'>
          {/* Primary controls */}
          <div className='camera-controls__primary'>
            <button
              className='camera-control camera-control--secondary'
              onClick={switchCamera}
              disabled={!capabilities?.hasFrontCamera || !capabilities?.hasBackCamera}
              title='Switch Camera'
            >
              🔄
            </button>

            <button
              className='camera-control camera-control--capture'
              onClick={capturePhoto}
              disabled={!isActive}
              title='Capture Photo'
            >
              📷
            </button>

            <button
              className={`camera-control camera-control--flash ${isFlashOn ? 'camera-control--active' : ''}`}
              onClick={toggleFlash}
              disabled={!capabilities?.supportsFlash}
              title='Toggle Flash'
            >
              ⚡
            </button>
          </div>

          {/* Secondary controls */}
          <div className='camera-controls__secondary'>
            {/* Zoom control */}
            {capabilities?.supportsZoom && (
              <div className='camera-zoom-control'>
                <label htmlFor='zoom'>Zoom: {currentZoom.toFixed(1)}x</label>
                <input
                  id='zoom'
                  type='range'
                  min='1'
                  max='10'
                  step='0.1'
                  value={currentZoom}
                  onChange={(e) => handleZoomChange(parseFloat(e.target.value))}
                />
              </div>
            )}

            {/* Start/Stop controls */}
            <div className='camera-state-controls'>
              {isActive ? (
                <button
                  className='camera-control camera-control--stop'
                  onClick={stopCamera}
                  title='Stop Camera'
                >
                  Stop
                </button>
              ) : (
                <button
                  className='camera-control camera-control--start'
                  onClick={startCamera}
                  title='Start Camera'
                >
                  Start
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Status indicators */}
      <div className='camera-status'>
        {!capabilities && !error && (
          <div className='camera-status__loading'>Initializing camera...</div>
        )}
        {capabilities && !isActive && !error && (
          <div className='camera-status__ready'>Camera ready</div>
        )}
      </div>

      {/* Built-in styles */}
      <style jsx>{`
        .camera-view {
          position: relative;
          width: 100%;
          height: 100%;
          background: #000;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          border-radius: 8px;
        }

        .camera-preview {
          position: relative;
          flex: 1;
          overflow: hidden;
        }

        .camera-video {
          width: 100%;
          height: 100%;
          object-fit: cover;
          transform: scaleX(-1); /* Mirror front camera */
        }

        .camera-view--active .camera-video {
          transform: none;
        }

        .camera-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          pointer-events: none;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .camera-focus-indicator {
          width: 80px;
          height: 80px;
          border: 2px solid rgba(255, 255, 255, 0.8);
          border-radius: 50%;
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .camera-flash-indicator {
          position: absolute;
          top: 16px;
          right: 16px;
          font-size: 24px;
          color: #ffd700;
          animation: flash-pulse 1s infinite;
        }

        @keyframes flash-pulse {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0.3;
          }
        }

        .camera-controls {
          padding: 16px;
          background: rgba(0, 0, 0, 0.8);
          backdrop-filter: blur(10px);
        }

        .camera-controls__primary {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 32px;
          margin-bottom: 16px;
        }

        .camera-controls__secondary {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 16px;
        }

        .camera-control {
          padding: 12px;
          background: rgba(255, 255, 255, 0.2);
          border: none;
          border-radius: 50%;
          color: white;
          font-size: 20px;
          min-width: 48px;
          min-height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          touch-action: manipulation;
        }

        .camera-control:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: scale(1.05);
        }

        .camera-control:active {
          transform: scale(0.95);
        }

        .camera-control:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }

        .camera-control--capture {
          width: 72px;
          height: 72px;
          background: #ff4757;
          font-size: 24px;
        }

        .camera-control--active {
          background: #ffd700;
          color: #000;
        }

        .camera-zoom-control {
          display: flex;
          align-items: center;
          gap: 8px;
          color: white;
          font-size: 14px;
        }

        .camera-zoom-control input {
          width: 120px;
        }

        .camera-state-controls button {
          padding: 8px 16px;
          border-radius: 16px;
          font-size: 14px;
          min-width: 60px;
        }

        .camera-status {
          position: absolute;
          top: 16px;
          left: 16px;
          color: white;
          font-size: 14px;
          background: rgba(0, 0, 0, 0.6);
          padding: 8px 12px;
          border-radius: 16px;
          backdrop-filter: blur(4px);
        }

        .camera-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: white;
          text-align: center;
          padding: 32px;
        }

        .camera-error__icon {
          font-size: 64px;
          margin-bottom: 16px;
          opacity: 0.6;
        }

        .camera-error__message {
          font-size: 16px;
          margin-bottom: 24px;
          line-height: 1.5;
        }

        .camera-error__retry {
          padding: 12px 24px;
          background: #ff4757;
          color: white;
          border: none;
          border-radius: 24px;
          font-size: 16px;
          cursor: pointer;
          transition: background 0.2s ease;
        }

        .camera-error__retry:hover {
          background: #ff3838;
        }

        @media (max-width: 768px) {
          .camera-controls {
            padding: 12px;
          }

          .camera-controls__primary {
            gap: 24px;
          }

          .camera-control {
            min-width: 44px;
            min-height: 44px;
          }

          .camera-control--capture {
            width: 64px;
            height: 64px;
          }
        }
      `}</style>
    </div>
  );
}
