import React, { useState, useCallback } from 'react';
import { BarcodeScanner as BarcodeScannerComponent } from './BarcodeScanner';
import { BarcodeResult } from '../types';
import {
  TechnicianWorkflowScanner,
  WorkflowType,
  WorkflowScanResult,
} from '../utils/TechnicianWorkflowScanner';

interface TechnicianScannerProps {
  workflowType?: WorkflowType;
  onWorkflowResult?: (result: WorkflowScanResult) => void;
  onAllResults?: (results: WorkflowScanResult[]) => void;
  className?: string;
}

export function TechnicianScanner({
  workflowType,
  onWorkflowResult,
  onAllResults,
  className = '',
}: TechnicianScannerProps) {
  const [lastScanResult, setLastScanResult] = useState<BarcodeResult | null>(null);
  const [workflowResults, setWorkflowResults] = useState<WorkflowScanResult[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleBarcodeResult = useCallback(
    async (result: BarcodeResult) => {
      setLastScanResult(result);
      setIsAnalyzing(true);

      try {
        // Analyze the barcode for workflow patterns
        const analyses = TechnicianWorkflowScanner.analyzeBarcode(result);
        setWorkflowResults(analyses);
        onAllResults?.(analyses);

        // If looking for specific workflow, find best match
        if (workflowType) {
          const workflowSpecific = TechnicianWorkflowScanner.filterByWorkflow(analyses, [
            workflowType,
          ]);
          const bestMatch = TechnicianWorkflowScanner.getBestMatch(workflowSpecific);

          if (bestMatch) {
            onWorkflowResult?.(bestMatch);
          }
        } else {
          // Otherwise return best overall match
          const bestMatch = TechnicianWorkflowScanner.getBestMatch(analyses);
          if (bestMatch) {
            onWorkflowResult?.(bestMatch);
          }
        }
      } catch (error) {
        console.error('Failed to analyze barcode:', error);
      } finally {
        setIsAnalyzing(false);
      }
    },
    [workflowType, onWorkflowResult, onAllResults]
  );

  const getBestResult = () => {
    if (!workflowResults.length) return null;
    return workflowType
      ? TechnicianWorkflowScanner.getBestMatch(
          TechnicianWorkflowScanner.filterByWorkflow(workflowResults, [workflowType])
        )
      : TechnicianWorkflowScanner.getBestMatch(workflowResults);
  };

  const bestResult = getBestResult();
  const instructions = workflowType
    ? TechnicianWorkflowScanner.getWorkflowInstructions(workflowType)
    : 'Scan any barcode or QR code';

  return (
    <div className={`technician-scanner ${className}`}>
      <BarcodeScannerComponent
        config={{
          formats: workflowType
            ? TechnicianWorkflowScanner.getExpectedFormats(workflowType)
            : ['QR_CODE', 'CODE_128', 'CODE_39', 'EAN_13'],
          continuous: false,
          beep: true,
          vibrate: true,
          overlay: true,
        }}
        onResult={handleBarcodeResult}
        className='technician-scanner__camera'
        showOverlay={true}
        showFormats={false}
      />

      {/* Results overlay */}
      <div className='technician-scanner__overlay'>
        {/* Instructions */}
        <div className='scanner-instructions'>
          <div className='scanner-instructions__text'>{instructions}</div>
          {workflowType && (
            <div className='scanner-instructions__workflow'>
              Expected: {workflowType.replace('_', ' ').toUpperCase()}
            </div>
          )}
        </div>

        {/* Analysis results */}
        {isAnalyzing && (
          <div className='scanner-analysis'>
            <div className='scanner-analysis__loading'>
              <div className='loading-spinner' />
              Analyzing...
            </div>
          </div>
        )}

        {lastScanResult && !isAnalyzing && (
          <div className='scanner-results'>
            <div className='scanner-results__header'>
              <div className='scanner-results__title'>Scan Result</div>
              <div className='scanner-results__format'>{lastScanResult.format}</div>
            </div>

            {bestResult ? (
              <div
                className={`scanner-result-item ${bestResult.isValid ? 'scanner-result-item--valid' : 'scanner-result-item--invalid'}`}
              >
                <div className='scanner-result-item__header'>
                  <div className='scanner-result-item__type'>
                    {bestResult.type.replace('_', ' ').toUpperCase()}
                  </div>
                  <div className='scanner-result-item__confidence'>
                    {Math.round(bestResult.confidence * 100)}%
                  </div>
                </div>

                <div className='scanner-result-item__data'>
                  {bestResult.isValid ? (
                    <div className='scanner-result-item__parsed'>
                      {Object.entries(bestResult.parsedData).map(([key, value]) => (
                        <div key={key} className='scanner-data-field'>
                          <span className='scanner-data-field__key'>{key}:</span>
                          <span className='scanner-data-field__value'>{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className='scanner-result-item__raw'>Raw: {bestResult.data}</div>
                  )}
                </div>

                <div className='scanner-result-item__status'>
                  {bestResult.isValid ? (
                    <span className='status-indicator status-indicator--success'>
                      ✅ Valid {bestResult.type.replace('_', ' ')}
                    </span>
                  ) : (
                    <span className='status-indicator status-indicator--warning'>
                      ⚠️ Format not recognized
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className='scanner-result-item scanner-result-item--no-match'>
                <div className='scanner-result-item__header'>
                  <div className='scanner-result-item__type'>UNKNOWN FORMAT</div>
                </div>
                <div className='scanner-result-item__raw'>{lastScanResult.data}</div>
                <div className='scanner-result-item__status'>
                  <span className='status-indicator status-indicator--error'>
                    ❌ No workflow pattern detected
                  </span>
                </div>
              </div>
            )}

            {/* Alternative matches */}
            {workflowResults.length > 1 && (
              <details className='scanner-alternatives'>
                <summary>Alternative interpretations ({workflowResults.length - 1})</summary>
                {workflowResults.slice(1).map((result, index) => (
                  <div key={index} className='scanner-alternative'>
                    <div className='scanner-alternative__type'>
                      {result.type.replace('_', ' ')} ({Math.round(result.confidence * 100)}%)
                    </div>
                    <div className='scanner-alternative__data'>
                      {result.isValid ? 'Valid' : 'Invalid'}
                    </div>
                  </div>
                ))}
              </details>
            )}
          </div>
        )}
      </div>

      {/* Built-in styles */}
      <style jsx>{`
        .technician-scanner {
          position: relative;
          width: 100%;
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .technician-scanner__camera {
          flex: 1;
        }

        .technician-scanner__overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          pointer-events: none;
          display: flex;
          flex-direction: column;
        }

        .scanner-instructions {
          position: absolute;
          top: 20px;
          left: 20px;
          right: 20px;
          background: rgba(0, 0, 0, 0.8);
          color: white;
          padding: 16px;
          border-radius: 8px;
          backdrop-filter: blur(4px);
          text-align: center;
        }

        .scanner-instructions__text {
          font-size: 16px;
          margin-bottom: 4px;
        }

        .scanner-instructions__workflow {
          font-size: 12px;
          color: #00ff88;
          font-weight: 600;
        }

        .scanner-analysis {
          position: absolute;
          bottom: 100px;
          left: 20px;
          right: 20px;
          background: rgba(0, 0, 0, 0.9);
          color: white;
          padding: 16px;
          border-radius: 8px;
          backdrop-filter: blur(4px);
          text-align: center;
        }

        .scanner-analysis__loading {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
        }

        .loading-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top: 2px solid white;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        .scanner-results {
          position: absolute;
          bottom: 20px;
          left: 20px;
          right: 20px;
          background: rgba(0, 0, 0, 0.9);
          color: white;
          border-radius: 8px;
          backdrop-filter: blur(4px);
          max-height: 300px;
          overflow-y: auto;
        }

        .scanner-results__header {
          padding: 16px 16px 8px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.2);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .scanner-results__title {
          font-size: 16px;
          font-weight: 600;
        }

        .scanner-results__format {
          font-size: 12px;
          padding: 4px 8px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 4px;
        }

        .scanner-result-item {
          padding: 16px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .scanner-result-item:last-child {
          border-bottom: none;
        }

        .scanner-result-item--valid {
          border-left: 4px solid #00ff88;
        }

        .scanner-result-item--invalid {
          border-left: 4px solid #ff6b6b;
        }

        .scanner-result-item--no-match {
          border-left: 4px solid #ffa500;
        }

        .scanner-result-item__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }

        .scanner-result-item__type {
          font-weight: 600;
          color: #00ff88;
        }

        .scanner-result-item__confidence {
          font-size: 12px;
          padding: 2px 6px;
          background: rgba(0, 255, 136, 0.2);
          border-radius: 3px;
          color: #00ff88;
        }

        .scanner-result-item__data {
          margin-bottom: 12px;
        }

        .scanner-data-field {
          display: flex;
          margin-bottom: 4px;
          font-size: 14px;
        }

        .scanner-data-field__key {
          color: #ccc;
          margin-right: 8px;
          min-width: 80px;
        }

        .scanner-data-field__value {
          color: white;
          font-weight: 500;
        }

        .scanner-result-item__raw {
          font-family: monospace;
          font-size: 12px;
          color: #ccc;
          word-break: break-all;
        }

        .scanner-result-item__status {
          font-size: 14px;
        }

        .status-indicator {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          font-weight: 500;
        }

        .status-indicator--success {
          color: #00ff88;
        }

        .status-indicator--warning {
          color: #ffa500;
        }

        .status-indicator--error {
          color: #ff6b6b;
        }

        .scanner-alternatives {
          margin-top: 12px;
          border-top: 1px solid rgba(255, 255, 255, 0.1);
          padding-top: 12px;
        }

        .scanner-alternatives summary {
          cursor: pointer;
          font-size: 14px;
          color: #ccc;
          margin-bottom: 8px;
        }

        .scanner-alternative {
          padding: 8px;
          margin-bottom: 4px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 4px;
          display: flex;
          justify-content: space-between;
          font-size: 12px;
        }

        .scanner-alternative__type {
          color: #ccc;
        }

        .scanner-alternative__data {
          color: white;
        }

        @media (max-width: 768px) {
          .scanner-instructions,
          .scanner-analysis,
          .scanner-results {
            left: 12px;
            right: 12px;
          }

          .scanner-results {
            max-height: 250px;
          }

          .scanner-data-field {
            flex-direction: column;
            gap: 2px;
          }

          .scanner-data-field__key {
            min-width: auto;
            margin-right: 0;
          }
        }
      `}</style>
    </div>
  );
}
