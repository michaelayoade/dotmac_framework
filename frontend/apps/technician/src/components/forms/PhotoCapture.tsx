/**
 * Photo Capture Component
 * Handles photo capture for work order documentation with offline support
 */

'use client';

import { useState, useRef, useEffect } from 'react';
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
  Image,
  Upload,
} from 'lucide-react';

interface PhotoCaptureProps {
  onPhotoCapture: (photoDataUrl: string) => void;
  onCancel: () => void;
  workOrderId?: string;
  category?: 'BEFORE' | 'DURING' | 'AFTER' | 'EQUIPMENT' | 'DAMAGE' | 'COMPLETION';
  title?: string;
  allowUpload?: boolean;
}

export function PhotoCapture({
  onPhotoCapture,
  onCancel,
  workOrderId,
  category = 'DURING',
  title = 'Take Photo',
  allowUpload = true,
}: PhotoCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasFlash, setHasFlash] = useState(false);
  const [flashEnabled, setFlashEnabled] = useState(false);
  const [cameras, setCameras] = useState<MediaDeviceInfo[]>([]);
  const [currentCameraIndex, setCurrentCameraIndex] = useState(0);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [cameraPermissionGranted, setCameraPermissionGranted] = useState(false);

  useEffect(() => {
    initializeCamera();
    return () => {
      cleanup();
    };
  }, [currentCameraIndex]);

  const initializeCamera = async () => {
    try {
      setError(null);

      // Check for camera permission
      const permissionStatus = await navigator.permissions?.query({ name: 'camera' as PermissionName });
      
      if (permissionStatus?.state === 'denied') {
        setError('Camera permission denied. Please enable camera access or use file upload.');
        return;
      }

      // Get available cameras
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(device => device.kind === 'videoinput');
      setCameras(videoDevices);

      if (videoDevices.length === 0) {
        setError('No cameras found on this device.');
        return;
      }

      // Stop existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }

      // Start camera stream
      const constraints: MediaStreamConstraints = {
        video: {
          deviceId: videoDevices[currentCameraIndex]?.deviceId,
          width: { ideal: 1920, max: 1920 },
          height: { ideal: 1080, max: 1080 },
          facingMode: currentCameraIndex === 0 ? 'environment' : 'user',
        },
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setIsStreaming(true);
      }

      // Check for flash capability
      const track = stream.getVideoTracks()[0];
      const capabilities = track.getCapabilities?.();
      setHasFlash(capabilities?.torch === true);

      setCameraPermissionGranted(true);
    } catch (error) {
      console.error('Camera initialization failed:', error);
      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError('Failed to access camera. Please check permissions or use file upload.');
      }
    }
  };

  const capturePhoto = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    if (!video || !canvas) return;

    setIsProcessing(true);

    try {
      // Set canvas dimensions to match video
      canvas.width = video.videoWidth || 1920;
      canvas.height = video.videoHeight || 1080;

      const context = canvas.getContext('2d');
      if (!context) {
        throw new Error('Failed to get canvas context');
      }

      // Draw video frame to canvas
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Add metadata overlay
      addMetadataOverlay(context, canvas.width, canvas.height);

      // Convert to blob with compression
      const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
      
      setCapturedPhoto(dataUrl);
    } catch (error) {
      console.error('Failed to capture photo:', error);
      setError('Failed to capture photo. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const addMetadataOverlay = (context: CanvasRenderingContext2D, width: number, height: number) => {
    const now = new Date();
    const dateTime = now.toLocaleString();
    const metadata = [
      `Date: ${dateTime}`,
      `Work Order: ${workOrderId || 'N/A'}`,
      `Category: ${category}`,
      `Location: ${navigator.geolocation ? 'GPS Enabled' : 'No GPS'}`,
    ];

    // Set up text style
    context.fillStyle = 'rgba(0, 0, 0, 0.7)';
    context.fillRect(0, height - 80, width, 80);
    
    context.fillStyle = 'white';
    context.font = '14px Arial';
    context.textAlign = 'left';

    // Draw metadata
    metadata.forEach((text, index) => {
      context.fillText(text, 10, height - 60 + (index * 15));
    });
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file');
      return;
    }

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('Image file is too large. Please select a file smaller than 10MB');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const dataUrl = await fileToDataUrl(file);
      
      // Process uploaded image (resize if needed)
      const processedDataUrl = await processUploadedImage(dataUrl);
      
      setCapturedPhoto(processedDataUrl);
    } catch (error) {
      console.error('Failed to process uploaded file:', error);
      setError('Failed to process uploaded image');
    } finally {
      setIsProcessing(false);
    }
  };

  const fileToDataUrl = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const processUploadedImage = async (dataUrl: string): Promise<string> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d')!;

        // Calculate dimensions (max 1920x1080)
        const maxWidth = 1920;
        const maxHeight = 1080;
        let { width, height } = img;

        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width *= ratio;
          height *= ratio;
        }

        canvas.width = width;
        canvas.height = height;

        // Draw image
        context.drawImage(img, 0, 0, width, height);

        // Add metadata overlay
        addMetadataOverlay(context, width, height);

        // Return compressed image
        resolve(canvas.toDataURL('image/jpeg', 0.8));
      };
      img.src = dataUrl;
    });
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

  const retakePhoto = () => {
    setCapturedPhoto(null);
    setError(null);
  };

  const confirmPhoto = () => {
    if (capturedPhoto) {
      onPhotoCapture(capturedPhoto);
    }
  };

  const cleanup = () => {
    setIsStreaming(false);
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
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
              onCancel();
            }}
            className="w-10 h-10 bg-black bg-opacity-50 rounded-full flex items-center justify-center text-white hover:bg-opacity-70"
          >
            <X className="w-5 h-5" />
          </button>
          
          <h1 className="text-white font-semibold">{title}</h1>
          
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

      {/* Camera/Photo View */}
      <div className="flex-1 relative overflow-hidden">
        {capturedPhoto ? (
          // Photo Preview
          <div className="absolute inset-0 flex items-center justify-center bg-black">
            <img
              src={capturedPhoto}
              alt="Captured photo"
              className="max-w-full max-h-full object-contain"
            />
          </div>
        ) : (
          // Camera View
          <>
            {!error && isStreaming && (
              <>
                <video
                  ref={videoRef}
                  className="w-full h-full object-cover"
                  playsInline
                  muted
                />
                <canvas ref={canvasRef} className="hidden" />
              </>
            )}

            {/* Camera Grid Overlay */}
            {isStreaming && !capturedPhoto && (
              <div className="absolute inset-0 pointer-events-none">
                <div className="w-full h-full border border-white opacity-20">
                  <div className="absolute top-1/3 left-0 right-0 border-t border-white opacity-20"></div>
                  <div className="absolute top-2/3 left-0 right-0 border-t border-white opacity-20"></div>
                  <div className="absolute left-1/3 top-0 bottom-0 border-l border-white opacity-20"></div>
                  <div className="absolute left-2/3 top-0 bottom-0 border-l border-white opacity-20"></div>
                </div>
              </div>
            )}

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
                    {cameraPermissionGranted && (
                      <button
                        onClick={initializeCamera}
                        className="w-full bg-primary-600 hover:bg-primary-700 text-white py-3 px-6 rounded-lg font-medium"
                      >
                        Try Again
                      </button>
                    )}
                    {allowUpload && (
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="w-full bg-gray-600 hover:bg-gray-700 text-white py-3 px-6 rounded-lg font-medium"
                      >
                        Upload from Gallery
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
          </>
        )}
      </div>

      {/* Controls */}
      <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 p-4">
        {capturedPhoto ? (
          // Photo Confirmation Controls
          <div className="flex items-center justify-center space-x-4">
            <button
              onClick={retakePhoto}
              className="w-16 h-16 bg-gray-600 hover:bg-gray-700 rounded-full flex items-center justify-center text-white transition-colors"
            >
              <RotateCcw className="w-6 h-6" />
            </button>
            
            <button
              onClick={confirmPhoto}
              className="w-20 h-20 bg-green-600 hover:bg-green-700 rounded-full flex items-center justify-center text-white transition-colors"
            >
              <Check className="w-8 h-8" />
            </button>
          </div>
        ) : (
          // Camera Controls
          <div className="flex items-center justify-between">
            {/* Upload Button */}
            {allowUpload && (
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isProcessing}
                className="w-12 h-12 bg-gray-600 hover:bg-gray-700 disabled:opacity-50 rounded-full flex items-center justify-center text-white transition-colors"
              >
                <Upload className="w-5 h-5" />
              </button>
            )}
            
            {/* Capture Button */}
            <button
              onClick={capturePhoto}
              disabled={!isStreaming || isProcessing}
              className="w-20 h-20 bg-white hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed rounded-full flex items-center justify-center transition-colors relative"
            >
              {isProcessing ? (
                <Loader2 className="w-8 h-8 animate-spin text-gray-600" />
              ) : (
                <>
                  <div className="w-16 h-16 border-4 border-gray-300 rounded-full flex items-center justify-center">
                    <Camera className="w-6 h-6 text-gray-600" />
                  </div>
                </>
              )}
            </button>
            
            {/* Gallery Indicator */}
            <div className="w-12 h-12 bg-gray-600 rounded-lg flex items-center justify-center">
              <Image className="w-5 h-5 text-white" />
            </div>
          </div>
        )}
        
        {/* Category Indicator */}
        <div className="text-center mt-3">
          <span className="text-white text-xs opacity-70">
            Category: {category} • {workOrderId ? `Work Order #${workOrderId}` : 'General'}
          </span>
        </div>
      </div>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileUpload}
        className="hidden"
      />
    </motion.div>
  );
}