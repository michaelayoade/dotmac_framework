/**
 * Inventory Barcode Scanner Component
 * Handles barcode scanning for inventory management
 */

'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Camera,
  X,
  Zap,
  ZapOff,
  RotateCcw,
  Check,
  AlertCircle,
  Loader2,
  ScanLine,
} from 'lucide-react';
import jsQR, { QRCode } from 'jsqr';
import { InventoryItem } from '../../lib/enhanced-offline-db';
import { createAppError, ErrorType } from '../error/ErrorBoundary';

interface InventoryScannerProps {
  onScanSuccess: (barcode: string, item?: InventoryItem) => void;
  onClose: () => void;
  onManualEntry?: () => void;
  scanMode?: 'barcode' | 'qr' | 'both';
  autoClose?: boolean;
}

export function InventoryScanner({
  onScanSuccess,
  onClose,
  onManualEntry,
  scanMode = 'both',
  autoClose = true,
}: InventoryScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const streamRef = useRef<MediaStream | null>(null);

  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFlash, setHasFlash] = useState(false);
  const [flashEnabled, setFlashEnabled] = useState(false);
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]);
  const [currentCameraIndex, setCurrentCameraIndex] = useState(0);
  const [scanSuccess, setScanSuccess] = useState(false);
  const [lastScanResult, setLastScanResult] = useState<string | null>(null);
  const [cameraPermissionGranted, setCameraPermissionGranted] = useState(false);

  useEffect(() => {
    initializeCamera();
    return () => {
      cleanup();
    };
  }, [currentCameraIndex]);

  useEffect(() => {
    if (isScanning) {
      startScanning();
    } else {
      stopScanning();
    }
  }, [isScanning]);

  const initializeCamera = async () => {
    try {
      setError(null);

      // Check for camera permission
      const permissionStatus = await navigator.permissions?.query({ name: 'camera' as PermissionName });
      
      if (permissionStatus?.state === 'denied') {
        throw createAppError(
          ErrorType.PERMISSION,
          'Camera permission denied. Please enable camera access to scan barcodes.',
        );
      }

      // Get available cameras
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      setCameras(videoDevices);

      if (videoDevices.length === 0) {
        throw createAppError(
          ErrorType.CAMERA,
          'No cameras found on this device.',
        );
      }

      // Stop existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }

      // Start camera stream
      const constraints: MediaStreamConstraints = {
        video: {
          deviceId: videoDevices[currentCameraIndex]?.deviceId,
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: currentCameraIndex === 0 ? 'environment' : 'user',
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // Check for flash capability
      const track = stream.getVideoTracks()[0];
      const capabilities = track.getCapabilities?.();
      setHasFlash(capabilities?.torch === true);

      setCameraPermissionGranted(true);
      setIsScanning(true);
    } catch (error) {
      console.error('Camera initialization failed:', error);
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError('Failed to access camera. Please check permissions.');
      }
    }
  };

  const startScanning = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    if (!video || !canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    const scan = () => {
      if (!isScanning || !video.videoWidth) {
        animationRef.current = requestAnimationFrame(scan);
        return;
      }

      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      // Draw video frame to canvas
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Get image data for scanning
      const imageData = context.getImageData(0, 0, canvas.width, canvas.height);

      try {
        // Try QR code scanning first
        if (scanMode === 'qr' || scanMode === 'both') {
          const qrCode = jsQR(imageData.data, imageData.width, imageData.height);
          if (qrCode) {
            handleScanResult(qrCode.data, 'qr');
            return;
          }
        }

        // Try barcode scanning using a different approach
        if (scanMode === 'barcode' || scanMode === 'both') {
          const barcode = detectBarcode(imageData);
          if (barcode) {
            handleScanResult(barcode, 'barcode');
            return;
          }
        }
      } catch (scanError) {
        console.warn('Scan error:', scanError);
      }

      animationRef.current = requestAnimationFrame(scan);
    };

    scan();
  };

  const stopScanning = () => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  };

  const detectBarcode = (imageData: ImageData): string | null => {
    // Simple barcode detection using edge detection
    // This is a basic implementation - in production, you'd use a proper barcode library
    const { data, width, height } = imageData;
    const threshold = 128;
    let barcodePattern = '';
    
    // Scan horizontal lines for barcode patterns
    for (let y = Math.floor(height / 2) - 10; y < Math.floor(height / 2) + 10; y++) {
      let linePattern = '';
      let prevIntensity = 0;
      
      for (let x = 0; x < width; x++) {
        const index = (y * width + x) * 4;
        const intensity = (data[index] + data[index + 1] + data[index + 2]) / 3;
        
        if (Math.abs(intensity - prevIntensity) > threshold) {
          linePattern += intensity > prevIntensity ? '1' : '0';
        }
        
        prevIntensity = intensity;
      }
      
      // Check if pattern looks like a barcode (alternating bars)
      if (linePattern.length > 20 && /^[01]+$/.test(linePattern)) {
        const binaryGroups = linePattern.match(/.{1,8}/g) || [];
        if (binaryGroups.length >= 3) {
          // Convert to mock barcode (in production, use proper decoding)
          barcodePattern = binaryGroups.slice(0, 12).map(group => 
            parseInt(group.padEnd(8, '0'), 2) % 10
          ).join('');
          
          if (barcodePattern.length >= 8) {
            return barcodePattern;
          }
        }
      }
    }
    
    return null;
  };

  const handleScanResult = async (result: string, type: 'qr' | 'barcode') => {
    if (result === lastScanResult) return; // Prevent duplicate scans
    
    setLastScanResult(result);
    setScanSuccess(true);
    
    // Provide haptic feedback
    if ('vibrate' in navigator) {
      navigator.vibrate(100);
    }

    try {
      // Look up inventory item by barcode/QR code
      const item = await lookupInventoryItem(result);
      
      // Call success callback
      onScanSuccess(result, item);
      
      if (autoClose) {
        setTimeout(() => {
          cleanup();
          onClose();
        }, 1500);
      } else {
        // Reset for next scan
        setTimeout(() => {
          setScanSuccess(false);
          setLastScanResult(null);
        }, 2000);
      }
    } catch (error) {
      console.error('Failed to process scan result:', error);
      setError('Failed to process scanned item');
      setScanSuccess(false);
      setLastScanResult(null);
    }
  };

  const lookupInventoryItem = async (barcode: string): Promise<InventoryItem | undefined> => {
    // This would typically query your inventory database
    // For now, return undefined as item lookup is not implemented
    return undefined;
  };

  const toggleFlash = async () => {
    if (!hasFlash || !streamRef.current) return;

    try {
      const track = streamRef.current.getVideoTracks()[0];
      await track.applyConstraints({
        advanced: [{ torch: !flashEnabled } as any],
      });
      setFlashEnabled(!flashEnabled);
    } catch (error) {
      console.warn('Failed to toggle flash:', error);
    }
  };

  const switchCamera = () => {
    if (cameras.length <= 1) return;
    setCurrentCameraIndex((prev) => (prev + 1) % cameras.length);
  };

  const cleanup = () => {
    setIsScanning(false);
    stopScanning();
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const handleManualEntry = () => {
    cleanup();
    onManualEntry?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black z-50 flex flex-col"
    >
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-black bg-opacity-50 p-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => {
              cleanup();
              onClose();
            }}
            className="w-10 h-10 bg-black bg-opacity-50 rounded-full flex items-center justify-center text-white hover:bg-opacity-70"
          >
            <X className="w-5 h-5" />
          </button>
          
          <h1 className="text-white font-semibold">
            {scanMode === 'both' ? 'Scan Barcode or QR Code' :
             scanMode === 'qr' ? 'Scan QR Code' : 'Scan Barcode'}
          </h1>
          
          <div className="flex items-center space-x-2">
            {/* Flash Toggle */}
            {hasFlash && (
              <button
                onClick={toggleFlash}
                className={`w-10 h-10 bg-black bg-opacity-50 rounded-full flex items-center justify-center text-white hover:bg-opacity-70 ${
                  flashEnabled ? 'bg-yellow-500 bg-opacity-80' : ''
                }`}
              >
                {flashEnabled ? <Zap className="w-5 h-5" /> : <ZapOff className="w-5 h-5" />}
              </button>
            )}
            
            {/* Camera Switch */}
            {cameras.length > 1 && (
              <button
                onClick={switchCamera}
                className="w-10 h-10 bg-black bg-opacity-50 rounded-full flex items-center justify-center text-white hover:bg-opacity-70"
              >
                <RotateCcw className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Camera View */}
      <div className="flex-1 relative overflow-hidden">
        {!error && (
          <>
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              playsInline
              muted
            />
            <canvas
              ref={canvasRef}
              className="hidden"
            />
          </>
        )}

        {/* Scanning Overlay */}
        {!error && !scanSuccess && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative">
              <div className="w-64 h-64 border-2 border-white rounded-lg">
                {/* Animated scanning line */}
                <motion.div
                  className="absolute inset-0 border border-primary-500"
                  animate={{
                    boxShadow: [
                      '0 0 0 0 rgba(59, 130, 246, 0.7)',
                      '0 0 0 10px rgba(59, 130, 246, 0)',
                    ],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                  }}
                />
                
                <motion.div
                  className="w-full h-0.5 bg-primary-500"
                  animate={{ y: [0, 256] }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                />
                
                {/* Corner markers */}
                <div className="absolute top-0 left-0 w-6 h-6 border-t-4 border-l-4 border-primary-500"></div>
                <div className="absolute top-0 right-0 w-6 h-6 border-t-4 border-r-4 border-primary-500"></div>
                <div className="absolute bottom-0 left-0 w-6 h-6 border-b-4 border-l-4 border-primary-500"></div>
                <div className="absolute bottom-0 right-0 w-6 h-6 border-b-4 border-r-4 border-primary-500"></div>
              </div>
              
              <div className="text-center mt-4">
                <p className="text-white text-sm">
                  Position the {scanMode === 'both' ? 'barcode or QR code' : scanMode === 'qr' ? 'QR code' : 'barcode'} within the frame
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Success Animation */}
        <AnimatePresence>
          {scanSuccess && (
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.5 }}
              className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50"
            >
              <div className="text-center">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4"
                >
                  <Check className="w-10 h-10 text-white" />
                </motion.div>
                <h3 className="text-white text-lg font-semibold mb-2">Scan Successful!</h3>
                <p className="text-white text-sm opacity-80">
                  {lastScanResult}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error State */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black">
            <div className="text-center text-white p-6">
              <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Camera Error</h3>
              <p className="text-sm opacity-80 mb-6 max-w-sm">
                {error}
              </p>
              <div className="space-y-3">
                <button
                  onClick={initializeCamera}
                  className="w-full bg-primary-600 hover:bg-primary-700 text-white py-3 px-6 rounded-lg font-medium"
                >
                  Try Again
                </button>
                {onManualEntry && (
                  <button
                    onClick={handleManualEntry}
                    className="w-full bg-gray-600 hover:bg-gray-700 text-white py-3 px-6 rounded-lg font-medium"
                  >
                    Enter Manually
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {!cameraPermissionGranted && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black">
            <div className="text-center text-white">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
              <p className="text-sm">Initializing camera...</p>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-black bg-opacity-50">
        <div className="flex justify-center space-x-4">
          {onManualEntry && (
            <button
              onClick={handleManualEntry}
              className="flex-1 bg-gray-600 hover:bg-gray-700 text-white py-3 px-6 rounded-lg font-medium transition-colors"
            >
              Enter Manually
            </button>
          )}
        </div>
        
        <div className="text-center mt-4">
          <p className="text-white text-xs opacity-70">
            Make sure the item is well lit and the code is clearly visible
          </p>
        </div>
      </div>
    </motion.div>
  );
}