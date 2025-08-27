/**
 * Digital Signature Capture Component
 * Provides touch-friendly signature capture for work order completion
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PenTool,
  Trash2,
  Check,
  X,
  RotateCcw,
  Download,
  Smartphone,
} from 'lucide-react';
import SignatureCanvas from 'react-signature-canvas';

interface SignatureCaptureProps {
  onSignatureComplete: (signatureDataUrl: string) => void;
  onCancel: () => void;
  customerName?: string;
  workOrderId?: string;
  required?: boolean;
  title?: string;
  subtitle?: string;
  backgroundColor?: string;
  penColor?: string;
}

export function SignatureCapture({
  onSignatureComplete,
  onCancel,
  customerName,
  workOrderId,
  required = false,
  title = 'Digital Signature Required',
  subtitle = 'Please sign below to confirm completion of work',
  backgroundColor = '#ffffff',
  penColor = '#000000',
}: SignatureCaptureProps) {
  const signatureRef = useRef<SignatureCanvas>(null);
  const [isEmpty, setIsEmpty] = useState(true);
  const [isLandscape, setIsLandscape] = useState(false);
  const [signatureData, setSignatureData] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    // Check initial orientation
    checkOrientation();
    
    // Listen for orientation changes
    const handleOrientationChange = () => {
      setTimeout(checkOrientation, 100); // Small delay to ensure DOM updates
    };
    
    window.addEventListener('orientationchange', handleOrientationChange);
    window.addEventListener('resize', checkOrientation);
    
    return () => {
      window.removeEventListener('orientationchange', handleOrientationChange);
      window.removeEventListener('resize', checkOrientation);
    };
  }, []);

  const checkOrientation = () => {
    const landscape = window.innerWidth > window.innerHeight;
    setIsLandscape(landscape);
    
    // Resize signature canvas after orientation change
    setTimeout(() => {
      if (signatureRef.current) {
        signatureRef.current.getCanvas().width = signatureRef.current.getCanvas().offsetWidth;
        signatureRef.current.getCanvas().height = signatureRef.current.getCanvas().offsetHeight;
        signatureRef.current.clear();
      }
    }, 200);
  };

  const handleSignatureEnd = () => {
    if (signatureRef.current) {
      const canvas = signatureRef.current.getCanvas();
      const context = canvas.getContext('2d');
      
      // Check if canvas has any content
      const imageData = context?.getImageData(0, 0, canvas.width, canvas.height);
      const hasContent = imageData?.data.some((channel, index) => 
        index % 4 !== 3 && channel !== 0
      );
      
      setIsEmpty(!hasContent);
    }
  };

  const handleClear = () => {
    if (signatureRef.current) {
      signatureRef.current.clear();
      setIsEmpty(true);
      setSignatureData(null);
      setShowPreview(false);
    }
  };

  const handleSave = () => {
    if (signatureRef.current && !isEmpty) {
      const dataUrl = signatureRef.current.toDataURL('image/png');
      setSignatureData(dataUrl);
      setShowPreview(true);
    }
  };

  const handleConfirm = () => {
    if (signatureData) {
      onSignatureComplete(signatureData);
    }
  };

  const handleDownload = () => {
    if (signatureData) {
      const link = document.createElement('a');
      link.download = `signature_${workOrderId || Date.now()}.png`;
      link.href = signatureData;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const suggestLandscape = () => {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      >
        <div className="bg-white rounded-lg p-6 max-w-sm w-full text-center">
          <Smartphone className="w-12 h-12 text-primary-600 mx-auto mb-4 transform rotate-90" />
          <h3 className="text-lg font-semibold mb-2">Better in Landscape</h3>
          <p className="text-gray-600 text-sm mb-4">
            For a better signature experience, please rotate your device to landscape mode.
          </p>
          <button
            onClick={() => setIsLandscape(true)}
            className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm"
          >
            Continue Anyway
          </button>
        </div>
      </motion.div>
    );
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className={`fixed inset-0 bg-white z-40 flex flex-col ${
          isLandscape ? 'landscape-mode' : ''
        }`}
      >
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
              <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
              {customerName && (
                <p className="text-sm text-primary-600 mt-1">
                  Customer: {customerName}
                </p>
              )}
            </div>
            
            <button
              onClick={onCancel}
              className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Signature Area */}
        <div className="flex-1 flex flex-col bg-gray-50 relative">
          <div className="flex-1 m-4 bg-white rounded-lg shadow-sm border-2 border-dashed border-gray-300 relative overflow-hidden">
            {/* Instructions */}
            {isEmpty && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="absolute inset-0 flex items-center justify-center pointer-events-none z-10"
              >
                <div className="text-center text-gray-400">
                  <PenTool className="w-8 h-8 mx-auto mb-2" />
                  <p className="text-sm">
                    {isLandscape 
                      ? 'Sign here with your finger or stylus'
                      : 'Use your finger or stylus to sign'
                    }
                  </p>
                  {!isLandscape && (
                    <p className="text-xs mt-1">
                      Rotate device for better experience
                    </p>
                  )}
                </div>
              </motion.div>
            )}

            {/* Signature Canvas */}
            <SignatureCanvas
              ref={signatureRef}
              canvasProps={{
                className: 'w-full h-full',
                style: { 
                  backgroundColor,
                  touchAction: 'none',
                },
              }}
              backgroundColor={backgroundColor}
              penColor={penColor}
              minWidth={2}
              maxWidth={4}
              dotSize={0}
              throttle={16}
              onEnd={handleSignatureEnd}
            />
            
            {/* Signature Line */}
            <div className="absolute bottom-8 left-8 right-8 border-b border-gray-300 pointer-events-none">
              <div className="absolute -bottom-6 left-0 text-xs text-gray-500">
                {customerName ? `${customerName}'s Signature` : 'Signature'}
              </div>
              <div className="absolute -bottom-6 right-0 text-xs text-gray-500">
                {new Date().toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="bg-white border-t border-gray-200 p-4 flex-shrink-0">
          <div className="flex items-center justify-between space-x-4">
            <div className="flex space-x-2">
              <button
                onClick={handleClear}
                disabled={isEmpty}
                className="flex items-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                <span>Clear</span>
              </button>
              
              {signatureData && !showPreview && (
                <button
                  onClick={handleDownload}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Save</span>
                </button>
              )}
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={onCancel}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              
              <button
                onClick={handleSave}
                disabled={isEmpty}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
              >
                <Check className="w-4 h-4" />
                <span>Accept</span>
              </button>
            </div>
          </div>
          
          {required && isEmpty && (
            <div className="mt-2 text-xs text-red-600 text-center">
              Signature is required to continue
            </div>
          )}
        </div>
      </motion.div>

      {/* Signature Preview Modal */}
      <AnimatePresence>
        {showPreview && signatureData && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-white rounded-lg max-w-md w-full p-6"
            >
              <h3 className="text-lg font-semibold mb-4 text-center">
                Confirm Signature
              </h3>
              
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <img
                  src={signatureData}
                  alt="Digital Signature"
                  className="w-full h-32 object-contain bg-white rounded border"
                />
              </div>
              
              <div className="text-sm text-gray-600 mb-4 space-y-1">
                {customerName && (
                  <p><strong>Signee:</strong> {customerName}</p>
                )}
                {workOrderId && (
                  <p><strong>Work Order:</strong> #{workOrderId}</p>
                )}
                <p><strong>Date:</strong> {new Date().toLocaleString()}</p>
                <p><strong>Device:</strong> {navigator.userAgent.includes('Mobile') ? 'Mobile Device' : 'Desktop'}</p>
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowPreview(false)}
                  className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                >
                  Edit
                </button>
                
                <button
                  onClick={handleDownload}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  <Download className="w-4 h-4" />
                </button>
                
                <button
                  onClick={handleConfirm}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                >
                  Confirm
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Landscape Suggestion (shown on portrait mobile) */}
      {!isLandscape && window.innerWidth < 768 && window.innerHeight > window.innerWidth && (
        suggestLandscape()
      )}
    </>
  );
}