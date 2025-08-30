import React, { useState } from 'react';
import {
  CameraView,
  TechnicianScanner,
  BarcodeScanner as BarcodeScannerComponent,
  useCamera,
  useBarcodeScanner,
  type CameraCaptureResult,
  type BarcodeResult,
  type WorkflowScanResult,
  type WorkflowType
} from '@dotmac/mobile/camera';

export function CameraDemoPage() {
  const [activeDemo, setActiveDemo] = useState<'camera' | 'scanner' | 'workflow'>('camera');
  const [workflowType, setWorkflowType] = useState<WorkflowType>('equipment_serial');
  const [captureResults, setCaptureResults] = useState<CameraCaptureResult[]>([]);
  const [scanResults, setScanResults] = useState<BarcodeResult[]>([]);
  const [workflowResults, setWorkflowResults] = useState<WorkflowScanResult[]>([]);

  const handleCameraCapture = (result: CameraCaptureResult) => {
    setCaptureResults(prev => [result, ...prev.slice(0, 4)]);
    console.log('Camera capture:', result);
  };

  const handleBarcodeResult = (result: BarcodeResult) => {
    setScanResults(prev => [result, ...prev.slice(0, 9)]);
    console.log('Barcode scan:', result);
  };

  const handleWorkflowResult = (result: WorkflowScanResult) => {
    setWorkflowResults(prev => [result, ...prev.slice(0, 9)]);
    console.log('Workflow result:', result);
  };

  return (
    <div className="camera-demo-page">
      {/* Header */}
      <div className="demo-header">
        <h1>Camera & Barcode Features</h1>
        <p>Enhanced mobile features for technician workflows</p>
      </div>

      {/* Demo tabs */}
      <div className="demo-tabs">
        <button
          className={`demo-tab ${activeDemo === 'camera' ? 'demo-tab--active' : ''}`}
          onClick={() => setActiveDemo('camera')}
        >
          📷 Camera
        </button>
        <button
          className={`demo-tab ${activeDemo === 'scanner' ? 'demo-tab--active' : ''}`}
          onClick={() => setActiveDemo('scanner')}
        >
          📱 Barcode Scanner
        </button>
        <button
          className={`demo-tab ${activeDemo === 'workflow' ? 'demo-tab--active' : ''}`}
          onClick={() => setActiveDemo('workflow')}
        >
          🔧 Workflow Scanner
        </button>
      </div>

      {/* Demo content */}
      <div className="demo-content">
        {activeDemo === 'camera' && (
          <div className="camera-demo">
            <div className="camera-demo__view">
              <CameraView
                onCapture={handleCameraCapture}
                showControls={true}
                className="camera-demo__camera"
              />
            </div>

            {captureResults.length > 0 && (
              <div className="camera-demo__results">
                <h3>Recent Captures ({captureResults.length})</h3>
                <div className="capture-grid">
                  {captureResults.map((result, index) => (
                    <div key={index} className="capture-item">
                      <img
                        src={result.dataUrl}
                        alt={`Capture ${index + 1}`}
                        className="capture-image"
                      />
                      <div className="capture-info">
                        <div>Size: {result.width}×{result.height}</div>
                        <div>Size: {Math.round(result.blob.size / 1024)}KB</div>
                        <div>{new Date(result.timestamp).toLocaleTimeString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeDemo === 'scanner' && (
          <div className="scanner-demo">
            <div className="scanner-demo__view">
              <BarcodeScannerComponent
                onResult={handleBarcodeResult}
                showOverlay={true}
                showFormats={true}
                className="scanner-demo__scanner"
              />
            </div>

            {scanResults.length > 0 && (
              <div className="scanner-demo__results">
                <h3>Recent Scans ({scanResults.length})</h3>
                <div className="scan-list">
                  {scanResults.map((result, index) => (
                    <div key={index} className="scan-item">
                      <div className="scan-item__header">
                        <span className="scan-format">{result.format}</span>
                        <span className="scan-time">
                          {new Date(result.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="scan-data">{result.data}</div>
                      <div className="scan-quality">
                        Quality: {Math.round(result.quality * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeDemo === 'workflow' && (
          <div className="workflow-demo">
            <div className="workflow-demo__controls">
              <label htmlFor="workflow-select">Workflow Type:</label>
              <select
                id="workflow-select"
                value={workflowType}
                onChange={(e) => setWorkflowType(e.target.value as WorkflowType)}
                className="workflow-select"
              >
                <option value="equipment_serial">Equipment Serial</option>
                <option value="work_order">Work Order</option>
                <option value="location_qr">Location QR</option>
                <option value="inventory_check">Inventory Check</option>
                <option value="customer_account">Customer Account</option>
                <option value="maintenance_tag">Maintenance Tag</option>
              </select>
            </div>

            <div className="workflow-demo__view">
              <TechnicianScanner
                workflowType={workflowType}
                onWorkflowResult={handleWorkflowResult}
                className="workflow-demo__scanner"
              />
            </div>

            {workflowResults.length > 0 && (
              <div className="workflow-demo__results">
                <h3>Workflow Results ({workflowResults.length})</h3>
                <div className="workflow-list">
                  {workflowResults.map((result, index) => (
                    <div
                      key={index}
                      className={`workflow-item ${result.isValid ? 'workflow-item--valid' : 'workflow-item--invalid'}`}
                    >
                      <div className="workflow-item__header">
                        <span className="workflow-type">
                          {result.type.replace('_', ' ').toUpperCase()}
                        </span>
                        <span className="workflow-confidence">
                          {Math.round(result.confidence * 100)}%
                        </span>
                      </div>

                      <div className="workflow-data">
                        {Object.entries(result.parsedData).map(([key, value]) => (
                          <div key={key} className="workflow-field">
                            <strong>{key}:</strong> {String(value)}
                          </div>
                        ))}
                      </div>

                      <div className="workflow-status">
                        {result.isValid ? '✅ Valid' : '❌ Invalid'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Built-in styles */}
      <style jsx>{`
        .camera-demo-page {
          min-height: 100vh;
          background: #f5f5f5;
          display: flex;
          flex-direction: column;
        }

        .demo-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          text-align: center;
        }

        .demo-header h1 {
          margin: 0 0 8px 0;
          font-size: 24px;
        }

        .demo-header p {
          margin: 0;
          opacity: 0.9;
        }

        .demo-tabs {
          display: flex;
          background: white;
          border-bottom: 1px solid #e0e0e0;
          overflow-x: auto;
        }

        .demo-tab {
          flex: 1;
          padding: 16px 20px;
          border: none;
          background: none;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s ease;
          border-bottom: 3px solid transparent;
          white-space: nowrap;
        }

        .demo-tab:hover {
          background: #f5f5f5;
        }

        .demo-tab--active {
          color: #667eea;
          border-bottom-color: #667eea;
          background: #f8f9ff;
        }

        .demo-content {
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        .camera-demo,
        .scanner-demo,
        .workflow-demo {
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        .camera-demo__view,
        .scanner-demo__view,
        .workflow-demo__view {
          height: 400px;
          background: #000;
          position: relative;
        }

        .camera-demo__camera,
        .scanner-demo__scanner,
        .workflow-demo__scanner {
          width: 100%;
          height: 100%;
        }

        .workflow-demo__controls {
          padding: 16px 20px;
          background: white;
          border-bottom: 1px solid #e0e0e0;
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .workflow-select {
          flex: 1;
          max-width: 200px;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
        }

        .camera-demo__results,
        .scanner-demo__results,
        .workflow-demo__results {
          padding: 20px;
          background: white;
          border-top: 1px solid #e0e0e0;
          max-height: 300px;
          overflow-y: auto;
        }

        .camera-demo__results h3,
        .scanner-demo__results h3,
        .workflow-demo__results h3 {
          margin: 0 0 16px 0;
          font-size: 16px;
          color: #333;
        }

        .capture-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 12px;
        }

        .capture-item {
          background: #f8f9fa;
          border-radius: 8px;
          overflow: hidden;
          border: 1px solid #e9ecef;
        }

        .capture-image {
          width: 100%;
          height: 80px;
          object-fit: cover;
        }

        .capture-info {
          padding: 8px;
          font-size: 11px;
          color: #666;
          line-height: 1.3;
        }

        .scan-list,
        .workflow-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .scan-item,
        .workflow-item {
          padding: 12px;
          background: #f8f9fa;
          border-radius: 8px;
          border: 1px solid #e9ecef;
        }

        .workflow-item--valid {
          border-left: 4px solid #28a745;
        }

        .workflow-item--invalid {
          border-left: 4px solid #dc3545;
        }

        .scan-item__header,
        .workflow-item__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .scan-format,
        .workflow-type {
          font-size: 12px;
          font-weight: 600;
          color: #667eea;
          background: rgba(102, 126, 234, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
        }

        .scan-time,
        .workflow-confidence {
          font-size: 12px;
          color: #666;
        }

        .scan-data {
          font-family: monospace;
          font-size: 12px;
          background: #fff;
          padding: 8px;
          border-radius: 4px;
          margin-bottom: 8px;
          word-break: break-all;
        }

        .workflow-data {
          margin-bottom: 8px;
        }

        .workflow-field {
          font-size: 13px;
          margin-bottom: 4px;
        }

        .workflow-field strong {
          color: #333;
          margin-right: 6px;
        }

        .scan-quality,
        .workflow-status {
          font-size: 12px;
          font-weight: 500;
        }

        .scan-quality {
          color: #666;
        }

        .workflow-status {
          color: #28a745;
        }

        .workflow-item--invalid .workflow-status {
          color: #dc3545;
        }

        @media (max-width: 768px) {
          .demo-header {
            padding: 16px;
          }

          .demo-header h1 {
            font-size: 20px;
          }

          .demo-tab {
            padding: 12px 16px;
            font-size: 13px;
          }

          .camera-demo__view,
          .scanner-demo__view,
          .workflow-demo__view {
            height: 350px;
          }

          .camera-demo__results,
          .scanner-demo__results,
          .workflow-demo__results {
            padding: 16px;
            max-height: 250px;
          }

          .workflow-demo__controls {
            padding: 12px 16px;
            flex-direction: column;
            align-items: stretch;
            gap: 8px;
          }

          .workflow-select {
            max-width: none;
          }

          .capture-grid {
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 8px;
          }

          .capture-image {
            height: 60px;
          }

          .capture-info {
            padding: 6px;
            font-size: 10px;
          }
        }
      `}</style>
    </div>
  );
}
