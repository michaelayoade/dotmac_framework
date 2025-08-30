'use client';

import React, { useState, useRef, useCallback } from 'react';
import {
  Upload,
  Download,
  RotateCcw,
  RotateCw,
  Crop,
  Palette,
  Settings,
  Zap,
  Eye,
  Check,
  X,
  Loader2,
  ZoomIn,
  ZoomOut,
  Move
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ImageProcessingOptions, ThumbnailOptions } from '../../types';
import { createThumbnail, processImage, isImageFile } from '../../utils/fileUtils';

interface ImageProcessorProps {
  onImageProcessed?: (processedBlob: Blob) => void;
  onCancel?: () => void;
  initialImage?: File | string;
  className?: string;
  maxWidth?: number;
  maxHeight?: number;
}

interface FilterOptions {
  brightness: number;
  contrast: number;
  saturation: number;
  blur: number;
  sepia: number;
  grayscale: number;
}

export function ImageProcessor({
  onImageProcessed,
  onCancel,
  initialImage,
  className = '',
  maxWidth = 1920,
  maxHeight = 1080
}: ImageProcessorProps) {
  const [originalImage, setOriginalImage] = useState<File | null>(null);
  const [processedImageUrl, setProcessedImageUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [scale, setScale] = useState(1);
  const [filters, setFilters] = useState<FilterOptions>({
    brightness: 100,
    contrast: 100,
    saturation: 100,
    blur: 0,
    sepia: 0,
    grayscale: 0
  });
  const [activeTab, setActiveTab] = useState<'adjust' | 'filters' | 'crop'>('adjust');
  const [cropArea, setCropArea] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Load initial image if provided
  React.useEffect(() => {
    if (initialImage) {
      if (typeof initialImage === 'string') {
        fetch(initialImage)
          .then(res => res.blob())
          .then(blob => {
            const file = new File([blob], 'image', { type: blob.type });
            setOriginalImage(file);
            setProcessedImageUrl(initialImage);
          })
          .catch(console.error);
      } else {
        setOriginalImage(initialImage);
        setProcessedImageUrl(URL.createObjectURL(initialImage));
      }
    }
  }, [initialImage]);

  const handleFileSelect = useCallback(async (file: File) => {
    if (!isImageFile(file)) {
      alert('Please select a valid image file');
      return;
    }

    setOriginalImage(file);
    const url = URL.createObjectURL(file);
    setProcessedImageUrl(url);

    // Reset all modifications
    setRotation(0);
    setScale(1);
    setFilters({
      brightness: 100,
      contrast: 100,
      saturation: 100,
      blur: 0,
      sepia: 0,
      grayscale: 0
    });
    setCropArea(null);
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const applyTransformations = useCallback(async () => {
    if (!originalImage || !canvasRef.current) return;

    setIsProcessing(true);

    try {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Could not get canvas context');

      // Load original image
      const img = new Image();
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = URL.createObjectURL(originalImage);
      });

      // Calculate dimensions
      let { width, height } = img;

      // Apply rotation (adjust canvas size for 90/270 degree rotations)
      const isRotated90or270 = Math.abs(rotation) % 180 === 90;
      const canvasWidth = isRotated90or270 ? height * scale : width * scale;
      const canvasHeight = isRotated90or270 ? width * scale : height * scale;

      canvas.width = canvasWidth;
      canvas.height = canvasHeight;

      // Clear canvas
      ctx.clearRect(0, 0, canvasWidth, canvasHeight);

      // Save context state
      ctx.save();

      // Apply transformations
      ctx.translate(canvasWidth / 2, canvasHeight / 2);
      ctx.rotate((rotation * Math.PI) / 180);
      ctx.scale(scale, scale);

      // Apply filters
      const filterString = [
        `brightness(${filters.brightness}%)`,
        `contrast(${filters.contrast}%)`,
        `saturate(${filters.saturation}%)`,
        `blur(${filters.blur}px)`,
        `sepia(${filters.sepia}%)`,
        `grayscale(${filters.grayscale}%)`
      ].join(' ');

      ctx.filter = filterString;

      // Draw image
      ctx.drawImage(img, -width / 2, -height / 2, width, height);

      // Restore context state
      ctx.restore();

      // Convert canvas to blob
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          setProcessedImageUrl(url);
        }
      }, 'image/png', 0.9);

    } catch (error) {
      console.error('Error processing image:', error);
    } finally {
      setIsProcessing(false);
    }
  }, [originalImage, rotation, scale, filters]);

  // Apply transformations when values change
  React.useEffect(() => {
    if (originalImage) {
      applyTransformations();
    }
  }, [originalImage, rotation, scale, filters, applyTransformations]);

  const handleRotateLeft = () => {
    setRotation(prev => prev - 90);
  };

  const handleRotateRight = () => {
    setRotation(prev => prev + 90);
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.1, 3));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.1, 0.1));
  };

  const handleFilterChange = (filterName: keyof FilterOptions, value: number) => {
    setFilters(prev => ({ ...prev, [filterName]: value }));
  };

  const resetFilters = () => {
    setFilters({
      brightness: 100,
      contrast: 100,
      saturation: 100,
      blur: 0,
      sepia: 0,
      grayscale: 0
    });
  };

  const resetAll = () => {
    setRotation(0);
    setScale(1);
    resetFilters();
    setCropArea(null);
  };

  const handleSave = async () => {
    if (!originalImage || !canvasRef.current) return;

    setIsProcessing(true);

    try {
      const options: ImageProcessingOptions = {
        maxWidth,
        maxHeight,
        quality: 90,
        format: 'png',
        maintainAspectRatio: true
      };

      const processedBlob = await processImage(originalImage, options);
      onImageProcessed?.(processedBlob);
    } catch (error) {
      console.error('Error saving processed image:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!processedImageUrl) return;

    const link = document.createElement('a');
    link.href = processedImageUrl;
    link.download = `processed-${originalImage?.name || 'image.png'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!originalImage) {
    return (
      <div className={`${className} bg-white rounded-lg border border-gray-200 p-8`}>
        <div className="text-center">
          <Upload className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Select an image to process
          </h3>
          <p className="text-gray-500 mb-6">
            Upload an image to start editing with filters, rotation, and cropping
          </p>

          <button
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Upload className="w-4 h-4 mr-2" />
            Choose Image
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileInputChange}
            className="hidden"
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`${className} bg-white rounded-lg border border-gray-200 overflow-hidden`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-medium text-gray-900">Image Editor</h3>
            {originalImage && (
              <span className="text-sm text-gray-500">
                {originalImage.name}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={resetAll}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            >
              Reset
            </button>

            <button
              onClick={handleDownload}
              disabled={!processedImageUrl}
              className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 border border-blue-300 rounded hover:bg-blue-50 transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4 mr-1 inline" />
              Download
            </button>

            <button
              onClick={handleSave}
              disabled={isProcessing}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {isProcessing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Check className="w-4 h-4 mr-1 inline" />
              )}
              {isProcessing ? 'Processing...' : 'Save'}
            </button>

            {onCancel && (
              <button
                onClick={onCancel}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="flex h-96">
        {/* Toolbar */}
        <div className="w-80 border-r border-gray-200 p-4 overflow-y-auto">
          {/* Tab Navigation */}
          <div className="flex mb-4 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setActiveTab('adjust')}
              className={`flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                activeTab === 'adjust' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Settings className="w-4 h-4 mr-1 inline" />
              Adjust
            </button>

            <button
              onClick={() => setActiveTab('filters')}
              className={`flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                activeTab === 'filters' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Palette className="w-4 h-4 mr-1 inline" />
              Filters
            </button>

            <button
              onClick={() => setActiveTab('crop')}
              className={`flex-1 px-3 py-2 text-sm rounded-md transition-colors ${
                activeTab === 'crop' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Crop className="w-4 h-4 mr-1 inline" />
              Crop
            </button>
          </div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            {activeTab === 'adjust' && (
              <motion.div
                key="adjust"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4"
              >
                {/* Rotation */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Rotation</label>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handleRotateLeft}
                      className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <span className="flex-1 text-center text-sm text-gray-600">{rotation}°</span>
                    <button
                      onClick={handleRotateRight}
                      className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                    >
                      <RotateCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Scale */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">Scale</label>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handleZoomOut}
                      className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                    >
                      <ZoomOut className="w-4 h-4" />
                    </button>
                    <span className="flex-1 text-center text-sm text-gray-600">
                      {Math.round(scale * 100)}%
                    </span>
                    <button
                      onClick={handleZoomIn}
                      className="p-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                    >
                      <ZoomIn className="w-4 h-4" />
                    </button>
                  </div>
                  <input
                    type="range"
                    min="0.1"
                    max="3"
                    step="0.1"
                    value={scale}
                    onChange={(e) => setScale(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </motion.div>
            )}

            {activeTab === 'filters' && (
              <motion.div
                key="filters"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4"
              >
                {/* Brightness */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center justify-between">
                    Brightness
                    <span className="text-xs text-gray-500">{filters.brightness}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    value={filters.brightness}
                    onChange={(e) => handleFilterChange('brightness', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Contrast */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center justify-between">
                    Contrast
                    <span className="text-xs text-gray-500">{filters.contrast}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    value={filters.contrast}
                    onChange={(e) => handleFilterChange('contrast', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Saturation */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center justify-between">
                    Saturation
                    <span className="text-xs text-gray-500">{filters.saturation}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    value={filters.saturation}
                    onChange={(e) => handleFilterChange('saturation', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Blur */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center justify-between">
                    Blur
                    <span className="text-xs text-gray-500">{filters.blur}px</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    value={filters.blur}
                    onChange={(e) => handleFilterChange('blur', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Sepia */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center justify-between">
                    Sepia
                    <span className="text-xs text-gray-500">{filters.sepia}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={filters.sepia}
                    onChange={(e) => handleFilterChange('sepia', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Grayscale */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center justify-between">
                    Grayscale
                    <span className="text-xs text-gray-500">{filters.grayscale}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={filters.grayscale}
                    onChange={(e) => handleFilterChange('grayscale', parseInt(e.target.value))}
                    className="w-full"
                  />
                </div>

                <button
                  onClick={resetFilters}
                  className="w-full px-3 py-2 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                >
                  Reset Filters
                </button>
              </motion.div>
            )}

            {activeTab === 'crop' && (
              <motion.div
                key="crop"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-4"
              >
                <div className="text-sm text-gray-600">
                  <p>Crop functionality coming soon...</p>
                  <p className="mt-2">This feature will allow you to:</p>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>Select crop area</li>
                    <li>Maintain aspect ratio</li>
                    <li>Apply common ratios</li>
                  </ul>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Canvas Area */}
        <div className="flex-1 p-4 bg-gray-50 flex items-center justify-center relative">
          {isProcessing && (
            <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10">
              <div className="flex items-center space-x-2 text-blue-600">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span>Processing...</span>
              </div>
            </div>
          )}

          <div className="relative max-w-full max-h-full">
            {processedImageUrl && (
              <img
                ref={imageRef}
                src={processedImageUrl}
                alt="Processed image"
                className="max-w-full max-h-full object-contain border border-gray-300 rounded shadow-sm"
              />
            )}
          </div>

          {/* Hidden canvas for processing */}
          <canvas
            ref={canvasRef}
            className="hidden"
          />
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileInputChange}
        className="hidden"
      />
    </div>
  );
}
