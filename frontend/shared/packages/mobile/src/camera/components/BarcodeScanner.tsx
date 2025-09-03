import React, { useRef, useEffect, useState, useCallback } from 'react';
import { CameraManager } from '../CameraManager';
import { BarcodeScanner as BarcodeScannerClass } from '../BarcodeScanner';
import { BarcodeResult, ScannerConfig, CameraError, BarcodeFormat } from '../types';

interface BarcodeScannerProps {
  config?: Partial<ScannerConfig>;
  onResult: (result: BarcodeResult) => void;
  onError?: (error: CameraError) => void;
  className?: string;
  showOverlay?: boolean;
  showFormats?: boolean;
}

export function BarcodeScanner({
  config = {},
  onResult,
  onError,
  className = '',
  showOverlay = true,
  showFormats = false,
}: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraManagerRef = useRef<CameraManager | null>(null);
  const scannerRef = useRef<BarcodeScannerClass | null>(null);

  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<CameraError | null>(null);
  const [detectedFormats, setDetectedFormats] = useState<BarcodeFormat[]>([]);

  // Initialize camera and scanner
  useEffect(() => {
    const initialize = async () => {
      try {
        // Initialize camera
        const camera = new CameraManager({
          facingMode: 'environment',
          resolution: 'high',
        });
        cameraManagerRef.current = camera;

        await camera.initialize();

        // Initialize scanner
        const scanner = new BarcodeScannerClass(config);
        scannerRef.current = scanner;

        // Start camera if video element is ready
        if (videoRef.current) {
          await camera.startCamera(videoRef.current);
          startScanning();
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
      cameraManagerRef.current?.dispose();
      scannerRef.current?.dispose();
    };
  }, []);

  const startScanning = useCallback(async () => {
    try {
      if (!scannerRef.current || !videoRef.current || isScanning) return;

      await scannerRef.current.startScanning(
        videoRef.current,
        (result: BarcodeResult) => {
          // Track detected formats
          if (!detectedFormats.includes(result.format)) {
            setDetectedFormats((prev) => [...prev, result.format]);
          }
          onResult(result);
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
  }, [isScanning, onResult, onError, detectedFormats]);

  const stopScanning = useCallback(() => {
    if (scannerRef.current) {
      scannerRef.current.stopScanning();
      setIsScanning(false);
    }
  }, []);

  const switchCamera = useCallback(async () => {
    try {
      if (!cameraManagerRef.current) return;

      stopScanning();
      await cameraManagerRef.current.switchCamera();
      startScanning();
    } catch (err) {
      const cameraError = err as CameraError;
      setError(cameraError);
      onError?.(cameraError);
    }
  }, [startScanning, stopScanning, onError]);

  if (error) {
    return (
      <div className={`barcode-scanner barcode-scanner--error ${className}`}>
        <div className='scanner-error'>
          <div className='scanner-error__icon'>📱</div>
          <div className='scanner-error__message'>{error.message}</div>
          <button
            className='scanner-error__retry'
            onClick={() => {
              setError(null);
              startScanning();
            }}
          >
            Retry Scanning
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`barcode-scanner ${isScanning ? 'barcode-scanner--scanning' : ''} ${className}`}
    >
      <div className='scanner-preview'>
        <video ref={videoRef} className='scanner-video' playsInline muted autoPlay />

        {showOverlay && (
          <div className='scanner-overlay'>
            {/* Scanning viewfinder */}
            <div className='scanner-viewfinder'>
              <div className='scanner-corner scanner-corner--top-left' />
              <div className='scanner-corner scanner-corner--top-right' />
              <div className='scanner-corner scanner-corner--bottom-left' />
              <div className='scanner-corner scanner-corner--bottom-right' />

              {/* Scanning line animation */}
              <div className='scanner-line' />
            </div>

            {/* Instructions */}
            <div className='scanner-instructions'>
              {isScanning ? 'Position barcode within the frame' : 'Ready to scan'}
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className='scanner-controls'>
        <button className='scanner-control' onClick={switchCamera} title='Switch Camera'>
          🔄
        </button>

        {isScanning ? (
          <button
            className='scanner-control scanner-control--stop'
            onClick={stopScanning}
            title='Stop Scanning'
          >
            ⏹️ Stop
          </button>
        ) : (
          <button
            className='scanner-control scanner-control--start'
            onClick={startScanning}
            title='Start Scanning'
          >
            ▶️ Scan
          </button>
        )}

        <button
          className='scanner-control'
          onClick={() =>
            cameraManagerRef.current?.setFlash(!cameraManagerRef.current.getConfig().enableFlash)
          }
          title='Toggle Torch'
        >
          🔦
        </button>
      </div>

      {/* Format information */}
      {showFormats && detectedFormats.length > 0 && (
        <div className='scanner-formats'>
          <div className='scanner-formats__title'>Detected Formats:</div>
          <div className='scanner-formats__list'>
            {detectedFormats.map((format) => (
              <span key={format} className='scanner-format-tag'>
                {format.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Status */}
      <div className='scanner-status'>
        {isScanning ? (
          <div className='scanner-status__scanning'>
            <div className='scanner-status__indicator' />
            Scanning...
          </div>
        ) : (
          <div className='scanner-status__ready'>Ready</div>
        )}
      </div>

      {/* Built-in styles */}
      <style jsx>{`
        .barcode-scanner {
          position: relative;
          width: 100%;
          height: 100%;
          background: #000;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          border-radius: 8px;
        }

        .scanner-preview {
          position: relative;
          flex: 1;
          overflow: hidden;
        }

        .scanner-video {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .scanner-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }

        .scanner-viewfinder {
          position: relative;
          width: 280px;
          height: 280px;
          max-width: 80vw;
          max-height: 40vh;
          border: 2px solid rgba(255, 255, 255, 0.3);
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(1px);
        }

        .scanner-corner {
          position: absolute;
          width: 24px;
          height: 24px;
          border: 3px solid #00ff88;
        }

        .scanner-corner--top-left {
          top: -3px;
          left: -3px;
          border-right: none;
          border-bottom: none;
        }

        .scanner-corner--top-right {
          top: -3px;
          right: -3px;
          border-left: none;
          border-bottom: none;
        }

        .scanner-corner--bottom-left {
          bottom: -3px;
          left: -3px;
          border-right: none;
          border-top: none;
        }

        .scanner-corner--bottom-right {
          bottom: -3px;
          right: -3px;
          border-left: none;
          border-top: none;
        }

        .scanner-line {
          position: absolute;
          left: 0;
          right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent, #00ff88, transparent);
          animation: scanner-sweep 2s ease-in-out infinite;
        }

        @keyframes scanner-sweep {
          0% {
            top: 0;
            opacity: 1;
          }
          50% {
            opacity: 0.8;
          }
          100% {
            top: calc(100% - 2px);
            opacity: 1;
          }
        }

        .barcode-scanner--scanning .scanner-line {
          animation-play-state: running;
        }

        .scanner-instructions {
          margin-top: 24px;
          color: white;
          font-size: 16px;
          text-align: center;
          background: rgba(0, 0, 0, 0.6);
          padding: 12px 24px;
          border-radius: 20px;
          backdrop-filter: blur(4px);
        }

        .scanner-controls {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 24px;
          padding: 16px;
          background: rgba(0, 0, 0, 0.8);
          backdrop-filter: blur(10px);
        }

        .scanner-control {
          padding: 12px;
          background: rgba(255, 255, 255, 0.2);
          border: none;
          border-radius: 50%;
          color: white;
          font-size: 18px;
          min-width: 48px;
          min-height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          touch-action: manipulation;
        }

        .scanner-control:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: scale(1.05);
        }

        .scanner-control:active {
          transform: scale(0.95);
        }

        .scanner-control--start {
          background: #00ff88;
          color: #000;
          padding: 12px 20px;
          border-radius: 24px;
          font-size: 16px;
          font-weight: 600;
          gap: 8px;
        }

        .scanner-control--stop {
          background: #ff4757;
          color: white;
          padding: 12px 20px;
          border-radius: 24px;
          font-size: 16px;
          font-weight: 600;
          gap: 8px;
        }

        .scanner-formats {
          padding: 12px 16px;
          background: rgba(0, 0, 0, 0.6);
          color: white;
          backdrop-filter: blur(4px);
        }

        .scanner-formats__title {
          font-size: 14px;
          margin-bottom: 8px;
          opacity: 0.8;
        }

        .scanner-formats__list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .scanner-format-tag {
          padding: 4px 8px;
          background: rgba(0, 255, 136, 0.2);
          border: 1px solid rgba(0, 255, 136, 0.4);
          border-radius: 12px;
          font-size: 12px;
          color: #00ff88;
        }

        .scanner-status {
          position: absolute;
          top: 16px;
          right: 16px;
          background: rgba(0, 0, 0, 0.8);
          color: white;
          padding: 8px 16px;
          border-radius: 16px;
          font-size: 14px;
          backdrop-filter: blur(4px);
        }

        .scanner-status__scanning {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .scanner-status__indicator {
          width: 8px;
          height: 8px;
          background: #00ff88;
          border-radius: 50%;
          animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(0.8);
          }
        }

        .scanner-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: white;
          text-align: center;
          padding: 32px;
        }

        .scanner-error__icon {
          font-size: 64px;
          margin-bottom: 16px;
          opacity: 0.6;
        }

        .scanner-error__message {
          font-size: 16px;
          margin-bottom: 24px;
          line-height: 1.5;
        }

        .scanner-error__retry {
          padding: 12px 24px;
          background: #00ff88;
          color: #000;
          border: none;
          border-radius: 24px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.2s ease;
        }

        .scanner-error__retry:hover {
          background: #00e77a;
        }

        @media (max-width: 768px) {
          .scanner-viewfinder {
            width: 240px;
            height: 240px;
          }

          .scanner-controls {
            gap: 16px;
            padding: 12px;
          }

          .scanner-control {
            min-width: 44px;
            min-height: 44px;
            font-size: 16px;
          }

          .scanner-instructions {
            font-size: 14px;
            padding: 8px 16px;
            margin-top: 16px;
          }
        }
      `}</style>
    </div>
  );
}
