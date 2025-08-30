import { BarcodeResult, BarcodeFormat, ScannerConfig, CameraError } from './types';

export class BarcodeScanner {
  private worker: Worker | null = null;
  private canvas: HTMLCanvasElement;
  private context: CanvasRenderingContext2D;
  private config: Required<ScannerConfig>;
  private scanning = false;
  private animationFrame: number | null = null;
  private onResultCallback?: (result: BarcodeResult) => void;
  private onErrorCallback?: (error: CameraError) => void;

  constructor(config: Partial<ScannerConfig> = {}) {
    this.config = {
      formats: ['QR_CODE', 'CODE_128', 'CODE_39', 'EAN_13', 'EAN_8'],
      continuous: true,
      beep: true,
      vibrate: true,
      torch: false,
      overlay: true,
      timeout: 10000,
      ...config
    };

    // Create canvas for barcode detection
    this.canvas = document.createElement('canvas');
    const context = this.canvas.getContext('2d');
    if (!context) {
      throw new Error('Canvas 2D context not available');
    }
    this.context = context;

    // Initialize Web Worker for barcode detection
    this.initializeWorker();
  }

  async startScanning(
    videoElement: HTMLVideoElement,
    onResult: (result: BarcodeResult) => void,
    onError?: (error: CameraError) => void
  ): Promise<void> {
    if (this.scanning) {
      return;
    }

    this.onResultCallback = onResult;
    this.onErrorCallback = onError;
    this.scanning = true;

    // Start scanning loop
    this.scanFrame(videoElement);

    // Set timeout if configured
    if (this.config.timeout) {
      setTimeout(() => {
        if (this.scanning) {
          this.stopScanning();
          this.onErrorCallback?.({
            type: 'SCANNER_ERROR',
            message: 'Scanning timeout exceeded'
          });
        }
      }, this.config.timeout);
    }
  }

  stopScanning(): void {
    this.scanning = false;
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  updateConfig(updates: Partial<ScannerConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  getConfig(): ScannerConfig {
    return { ...this.config };
  }

  // Static method to detect barcodes in image data
  static async detectBarcodes(imageData: ImageData, formats?: BarcodeFormat[]): Promise<BarcodeResult[]> {
    // Use BarcodeDetector API if available (Chrome/Edge)
    if ('BarcodeDetector' in window) {
      try {
        const detector = new (window as any).BarcodeDetector({
          formats: formats?.map(f => f.toLowerCase()) || ['qr_code', 'code_128', 'ean_13']
        });

        const barcodes = await detector.detect(imageData);

        return barcodes.map((barcode: any) => ({
          data: barcode.rawValue,
          format: barcode.format.toUpperCase() as BarcodeFormat,
          quality: 1.0,
          corners: barcode.cornerPoints?.map((p: any) => ({ x: p.x, y: p.y })),
          timestamp: Date.now()
        }));
      } catch (error) {
        console.warn('BarcodeDetector failed:', error);
      }
    }

    // Fallback to ZXing-js or similar library
    return BarcodeScanner.fallbackDetection(imageData, formats);
  }

  // Fallback barcode detection using pattern matching
  private static async fallbackDetection(imageData: ImageData, formats?: BarcodeFormat[]): Promise<BarcodeResult[]> {
    // This would integrate with a JavaScript barcode library like ZXing-js
    // For now, we'll implement basic QR code detection

    const results: BarcodeResult[] = [];

    try {
      // Basic pattern detection for QR codes
      const qrResult = BarcodeScanner.detectQRCode(imageData);
      if (qrResult) {
        results.push(qrResult);
      }

      // Add more format detectors as needed
      if (!formats || formats.includes('CODE_128')) {
        const code128Result = BarcodeScanner.detectCode128(imageData);
        if (code128Result) {
          results.push(code128Result);
        }
      }

    } catch (error) {
      console.warn('Fallback barcode detection failed:', error);
    }

    return results;
  }

  private static detectQRCode(imageData: ImageData): BarcodeResult | null {
    // Simplified QR code pattern detection
    // In a real implementation, this would use a proper QR decoder

    const { data, width, height } = imageData;

    // Look for QR code finder patterns (3 black squares in corners)
    const finderPatterns = BarcodeScanner.findQRFinderPatterns(data, width, height);

    if (finderPatterns.length >= 3) {
      // Mock QR code data for demonstration
      return {
        data: 'mock-qr-code-data',
        format: 'QR_CODE',
        quality: 0.8,
        corners: finderPatterns.slice(0, 4),
        timestamp: Date.now()
      };
    }

    return null;
  }

  private static detectCode128(imageData: ImageData): BarcodeResult | null {
    // Simplified Code128 detection
    // This would implement proper Code128 decoding in a real scenario

    const { data, width, height } = imageData;

    // Look for horizontal bar patterns typical of Code128
    if (BarcodeScanner.hasHorizontalBarPattern(data, width, height)) {
      return {
        data: 'mock-code128-data',
        format: 'CODE_128',
        quality: 0.7,
        timestamp: Date.now()
      };
    }

    return null;
  }

  private static findQRFinderPatterns(data: Uint8ClampedArray, width: number, height: number): Array<{ x: number; y: number }> {
    const patterns: Array<{ x: number; y: number }> = [];
    const blockSize = Math.min(width, height) / 20; // Approximate finder pattern size

    // Scan for dark square patterns
    for (let y = 0; y < height - blockSize; y += blockSize) {
      for (let x = 0; x < width - blockSize; x += blockSize) {
        if (BarcodeScanner.isFinderPattern(data, width, x, y, blockSize)) {
          patterns.push({ x, y });
        }
      }
    }

    return patterns;
  }

  private static isFinderPattern(data: Uint8ClampedArray, width: number, x: number, y: number, size: number): boolean {
    // Check if the region contains a dark square (simplified)
    let darkPixels = 0;
    let totalPixels = 0;

    for (let dy = 0; dy < size; dy++) {
      for (let dx = 0; dx < size; dx++) {
        const pixelIndex = ((y + dy) * width + (x + dx)) * 4;
        if (pixelIndex < data.length - 3) {
          const brightness = (data[pixelIndex] + data[pixelIndex + 1] + data[pixelIndex + 2]) / 3;
          if (brightness < 128) darkPixels++;
          totalPixels++;
        }
      }
    }

    return totalPixels > 0 && (darkPixels / totalPixels) > 0.6;
  }

  private static hasHorizontalBarPattern(data: Uint8ClampedArray, width: number, height: number): boolean {
    // Look for alternating dark/light horizontal patterns
    const midHeight = Math.floor(height / 2);
    let transitions = 0;
    let lastBrightness = 0;

    for (let x = 0; x < width; x += 2) {
      const pixelIndex = (midHeight * width + x) * 4;
      if (pixelIndex < data.length - 3) {
        const brightness = (data[pixelIndex] + data[pixelIndex + 1] + data[pixelIndex + 2]) / 3;
        const isDark = brightness < 128;
        const wasLastDark = lastBrightness < 128;

        if (isDark !== wasLastDark) {
          transitions++;
        }

        lastBrightness = brightness;
      }
    }

    // Code128 should have many transitions
    return transitions > width / 20;
  }

  private scanFrame(videoElement: HTMLVideoElement): void {
    if (!this.scanning || !videoElement.videoWidth || !videoElement.videoHeight) {
      if (this.scanning) {
        this.animationFrame = requestAnimationFrame(() => this.scanFrame(videoElement));
      }
      return;
    }

    // Set canvas size to match video
    const { videoWidth: width, videoHeight: height } = videoElement;
    this.canvas.width = width;
    this.canvas.height = height;

    // Draw video frame to canvas
    this.context.drawImage(videoElement, 0, 0, width, height);

    // Get image data for scanning
    const imageData = this.context.getImageData(0, 0, width, height);

    // Apply crop rect if configured
    const scanArea = this.config.cropRect
      ? this.context.getImageData(
          this.config.cropRect.x,
          this.config.cropRect.y,
          this.config.cropRect.width,
          this.config.cropRect.height
        )
      : imageData;

    // Scan for barcodes
    this.processScanArea(scanArea);

    // Continue scanning if continuous mode
    if (this.config.continuous && this.scanning) {
      this.animationFrame = requestAnimationFrame(() => this.scanFrame(videoElement));
    }
  }

  private async processScanArea(imageData: ImageData): Promise<void> {
    try {
      const results = await BarcodeScanner.detectBarcodes(imageData, this.config.formats);

      if (results.length > 0) {
        const result = results[0]; // Take the first result

        // Provide feedback
        await this.provideFeedback();

        // Call result callback
        this.onResultCallback?.(result);

        // Stop scanning if not continuous
        if (!this.config.continuous) {
          this.stopScanning();
        }
      }
    } catch (error) {
      this.onErrorCallback?.({
        type: 'SCANNER_ERROR',
        message: 'Barcode detection failed',
        details: error
      });
    }
  }

  private async provideFeedback(): Promise<void> {
    // Haptic feedback
    if (this.config.vibrate && navigator.vibrate) {
      navigator.vibrate([100, 50, 100]);
    }

    // Audio feedback
    if (this.config.beep) {
      try {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 800;
        oscillator.type = 'square';

        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.1);
      } catch (error) {
        // Audio feedback failed
      }
    }
  }

  private initializeWorker(): void {
    // In a real implementation, this would create a Web Worker
    // for offloading barcode detection to prevent UI blocking

    const workerCode = `
      self.onmessage = function(e) {
        const { imageData, formats } = e.data;

        // Perform barcode detection in worker
        // This would use a barcode detection library

        // Mock result for demonstration
        setTimeout(() => {
          self.postMessage({
            success: false,
            results: []
          });
        }, 100);
      };
    `;

    try {
      const blob = new Blob([workerCode], { type: 'application/javascript' });
      this.worker = new Worker(URL.createObjectURL(blob));

      this.worker.onmessage = (e) => {
        const { success, results, error } = e.data;
        // Handle worker results
      };
    } catch (error) {
      console.warn('Failed to create barcode scanner worker:', error);
    }
  }

  dispose(): void {
    this.stopScanning();
    this.worker?.terminate();
    this.canvas.remove();
  }
}
