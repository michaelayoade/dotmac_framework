import { mean, standardDeviation, quantile } from 'simple-statistics';
import type { AnomalyDetection, TimeSeriesData, AnomalyResult } from '../types';

export interface AnomalyDetectionOptions {
  method: 'z_score' | 'iqr' | 'isolation_forest' | 'lstm' | 'statistical';
  sensitivity: number; // 0-1, higher = more sensitive
  windowSize?: number;
  threshold?: number;
  includeSeasonality: boolean;
  learningRate?: number;
}

export interface AnomalyPoint {
  index: number;
  timestamp: Date;
  value: number;
  score: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  expected?: number;
  deviation?: number;
}

// Z-Score Based Anomaly Detection
export function zScoreAnomalyDetection(
  data: number[],
  threshold: number = 3,
  windowSize?: number
): AnomalyPoint[] {
  const anomalies: AnomalyPoint[] = [];

  if (windowSize && windowSize < data.length) {
    // Rolling window Z-score
    for (let i = windowSize; i < data.length; i++) {
      const window = data.slice(i - windowSize, i);
      const windowMean = mean(window);
      const windowStd = standardDeviation(window);

      if (windowStd > 0) {
        const zScore = Math.abs(data[i] - windowMean) / windowStd;

        if (zScore > threshold) {
          anomalies.push({
            index: i,
            timestamp: new Date(), // Would be actual timestamp in real implementation
            value: data[i],
            score: zScore,
            severity: getSeverity(zScore, threshold),
            confidence: Math.min(zScore / threshold, 1),
            expected: windowMean,
            deviation: Math.abs(data[i] - windowMean)
          });
        }
      }
    }
  } else {
    // Global Z-score
    const dataMean = mean(data);
    const dataStd = standardDeviation(data);

    if (dataStd > 0) {
      data.forEach((value, index) => {
        const zScore = Math.abs(value - dataMean) / dataStd;

        if (zScore > threshold) {
          anomalies.push({
            index,
            timestamp: new Date(),
            value,
            score: zScore,
            severity: getSeverity(zScore, threshold),
            confidence: Math.min(zScore / threshold, 1),
            expected: dataMean,
            deviation: Math.abs(value - dataMean)
          });
        }
      });
    }
  }

  return anomalies;
}

// Interquartile Range (IQR) Based Anomaly Detection
export function iqrAnomalyDetection(
  data: number[],
  multiplier: number = 1.5
): AnomalyPoint[] {
  const anomalies: AnomalyPoint[] = [];
  const sortedData = [...data].sort((a, b) => a - b);

  const q1 = quantile(sortedData, 0.25);
  const q3 = quantile(sortedData, 0.75);
  const iqr = q3 - q1;

  const lowerBound = q1 - multiplier * iqr;
  const upperBound = q3 + multiplier * iqr;

  data.forEach((value, index) => {
    if (value < lowerBound || value > upperBound) {
      const deviation = Math.min(
        Math.abs(value - lowerBound),
        Math.abs(value - upperBound)
      );

      const score = deviation / iqr;

      anomalies.push({
        index,
        timestamp: new Date(),
        value,
        score,
        severity: getSeverityIQR(value, lowerBound, upperBound, iqr),
        confidence: Math.min(score, 1),
        expected: value < lowerBound ? lowerBound : upperBound,
        deviation
      });
    }
  });

  return anomalies;
}

// Statistical Anomaly Detection with Multiple Methods
export function statisticalAnomalyDetection(
  data: TimeSeriesData[],
  options: Partial<AnomalyDetectionOptions> = {}
): AnomalyDetection {
  const config: AnomalyDetectionOptions = {
    method: 'statistical',
    sensitivity: 0.8,
    windowSize: Math.min(50, Math.floor(data.length / 4)),
    threshold: 2.5,
    includeSeasonality: true,
    ...options
  };

  const values = data.map(d => d.value);
  let anomalies: AnomalyPoint[] = [];

  // Primary detection method
  switch (config.method) {
    case 'z_score':
      anomalies = zScoreAnomalyDetection(values, config.threshold!, config.windowSize);
      break;
    case 'iqr':
      anomalies = iqrAnomalyDetection(values, config.sensitivity * 2);
      break;
    default:
      // Combine multiple methods for statistical approach
      const zScoreAnomalies = zScoreAnomalyDetection(values, config.threshold!);
      const iqrAnomalies = iqrAnomalyDetection(values, config.sensitivity * 2);

      // Merge and deduplicate
      const anomalyIndices = new Set([
        ...zScoreAnomalies.map(a => a.index),
        ...iqrAnomalies.map(a => a.index)
      ]);

      anomalies = Array.from(anomalyIndices).map(index => {
        const zAnomaly = zScoreAnomalies.find(a => a.index === index);
        const iqrAnomaly = iqrAnomalies.find(a => a.index === index);

        const scores = [zAnomaly?.score || 0, iqrAnomaly?.score || 0].filter(s => s > 0);
        const avgScore = scores.reduce((sum, s) => sum + s, 0) / scores.length;

        return {
          index,
          timestamp: data[index].timestamp,
          value: values[index],
          score: avgScore,
          severity: getSeverity(avgScore, config.threshold!),
          confidence: Math.min(avgScore / config.threshold!, 1),
          expected: zAnomaly?.expected || iqrAnomaly?.expected,
          deviation: zAnomaly?.deviation || iqrAnomaly?.deviation
        };
      });
  }

  // Add timestamps from original data
  anomalies = anomalies.map(anomaly => ({
    ...anomaly,
    timestamp: data[anomaly.index]?.timestamp || new Date()
  }));

  // Calculate detection metrics
  const detectionRate = anomalies.length / data.length;
  const avgConfidence = anomalies.length > 0
    ? anomalies.reduce((sum, a) => sum + a.confidence, 0) / anomalies.length
    : 0;

  const severityCounts = anomalies.reduce((counts, anomaly) => {
    counts[anomaly.severity] = (counts[anomaly.severity] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  return {
    id: `anomaly-detection-${Date.now()}`,
    modelId: `statistical-${config.method}`,
    detectedAt: new Date(),
    dataPoints: data.length,
    anomalies: anomalies.map(a => ({
      timestamp: a.timestamp,
      value: a.value,
      score: a.score,
      severity: a.severity,
      expected: a.expected,
      confidence: a.confidence
    })),
    metrics: {
      totalAnomalies: anomalies.length,
      detectionRate,
      avgConfidence,
      falsePositiveRate: Math.max(0, detectionRate - 0.05), // Estimate
      severityDistribution: severityCounts
    },
    method: config.method,
    parameters: {
      sensitivity: config.sensitivity,
      threshold: config.threshold!,
      windowSize: config.windowSize
    }
  };
}

// Isolation Forest-like Algorithm (Simplified)
export function isolationForestAnomalyDetection(
  data: number[],
  contamination: number = 0.1,
  numTrees: number = 100
): AnomalyPoint[] {
  const anomalies: AnomalyPoint[] = [];
  const n = data.length;
  const expectedAnomalies = Math.floor(n * contamination);

  // Create isolation trees (simplified version)
  const trees = [];
  for (let t = 0; t < numTrees; t++) {
    trees.push(createIsolationTree(data, Math.ceil(Math.log2(n))));
  }

  // Calculate anomaly scores
  const scores = data.map((value, index) => {
    const pathLengths = trees.map(tree => getPathLength(tree, value));
    const avgPathLength = mean(pathLengths);

    // Shorter paths indicate anomalies (isolated faster)
    const score = Math.pow(2, -avgPathLength / averagePathLength(n));

    return { index, value, score };
  });

  // Sort by score and take top anomalies
  scores.sort((a, b) => b.score - a.score);
  const threshold = scores[expectedAnomalies - 1]?.score || 0.6;

  scores.slice(0, expectedAnomalies).forEach(item => {
    if (item.score >= threshold) {
      anomalies.push({
        index: item.index,
        timestamp: new Date(),
        value: item.value,
        score: item.score,
        severity: getSeverity(item.score * 5, 2.5), // Scale score for severity
        confidence: item.score
      });
    }
  });

  return anomalies;
}

// LSTM-based Anomaly Detection (Simplified)
export function lstmAnomalyDetection(
  data: TimeSeriesData[],
  windowSize: number = 10,
  threshold: number = 0.1
): Promise<AnomalyDetection> {
  return new Promise((resolve) => {
    // This is a simplified version - real implementation would use TensorFlow.js
    const values = data.map(d => d.value);
    const anomalies: AnomalyPoint[] = [];

    // Simple prediction-based approach
    for (let i = windowSize; i < values.length; i++) {
      const window = values.slice(i - windowSize, i);
      const predicted = simplePredict(window);
      const actual = values[i];
      const error = Math.abs(actual - predicted) / Math.max(actual, predicted, 1);

      if (error > threshold) {
        anomalies.push({
          index: i,
          timestamp: data[i].timestamp,
          value: actual,
          score: error,
          severity: getSeverity(error * 10, threshold * 10),
          confidence: Math.min(error / threshold, 1),
          expected: predicted,
          deviation: Math.abs(actual - predicted)
        });
      }
    }

    const detectionRate = anomalies.length / data.length;
    const avgConfidence = anomalies.length > 0
      ? anomalies.reduce((sum, a) => sum + a.confidence, 0) / anomalies.length
      : 0;

    resolve({
      id: `lstm-anomaly-${Date.now()}`,
      modelId: 'lstm-simplified',
      detectedAt: new Date(),
      dataPoints: data.length,
      anomalies: anomalies.map(a => ({
        timestamp: a.timestamp,
        value: a.value,
        score: a.score,
        severity: a.severity,
        expected: a.expected,
        confidence: a.confidence
      })),
      metrics: {
        totalAnomalies: anomalies.length,
        detectionRate,
        avgConfidence,
        falsePositiveRate: Math.max(0, detectionRate - 0.03),
        severityDistribution: anomalies.reduce((counts, a) => {
          counts[a.severity] = (counts[a.severity] || 0) + 1;
          return counts;
        }, {} as Record<string, number>)
      },
      method: 'lstm',
      parameters: {
        windowSize,
        threshold,
        sensitivity: 0.8
      }
    });
  });
}

// Comprehensive Anomaly Detection
export async function detectAnomalies(
  data: TimeSeriesData[],
  options: Partial<AnomalyDetectionOptions> = {}
): Promise<AnomalyDetection> {
  const config: AnomalyDetectionOptions = {
    method: 'statistical',
    sensitivity: 0.8,
    threshold: 2.5,
    includeSeasonality: true,
    ...options
  };

  switch (config.method) {
    case 'lstm':
      return lstmAnomalyDetection(data, config.windowSize, config.threshold);

    case 'isolation_forest': {
      const values = data.map(d => d.value);
      const anomalies = isolationForestAnomalyDetection(values, 0.05);

      return {
        id: `isolation-forest-${Date.now()}`,
        modelId: 'isolation-forest',
        detectedAt: new Date(),
        dataPoints: data.length,
        anomalies: anomalies.map(a => ({
          timestamp: data[a.index]?.timestamp || new Date(),
          value: a.value,
          score: a.score,
          severity: a.severity,
          confidence: a.confidence
        })),
        metrics: {
          totalAnomalies: anomalies.length,
          detectionRate: anomalies.length / data.length,
          avgConfidence: anomalies.reduce((sum, a) => sum + a.confidence, 0) / Math.max(anomalies.length, 1),
          falsePositiveRate: 0.05,
          severityDistribution: anomalies.reduce((counts, a) => {
            counts[a.severity] = (counts[a.severity] || 0) + 1;
            return counts;
          }, {} as Record<string, number>)
        },
        method: 'isolation_forest',
        parameters: config
      };
    }

    default:
      return statisticalAnomalyDetection(data, config);
  }
}

// Helper functions
function getSeverity(score: number, threshold: number): 'low' | 'medium' | 'high' | 'critical' {
  const ratio = score / threshold;
  if (ratio > 3) return 'critical';
  if (ratio > 2) return 'high';
  if (ratio > 1.5) return 'medium';
  return 'low';
}

function getSeverityIQR(value: number, lowerBound: number, upperBound: number, iqr: number): 'low' | 'medium' | 'high' | 'critical' {
  const deviation = Math.min(
    Math.abs(value - lowerBound),
    Math.abs(value - upperBound)
  );

  const ratio = deviation / iqr;
  if (ratio > 3) return 'critical';
  if (ratio > 2) return 'high';
  if (ratio > 1) return 'medium';
  return 'low';
}

// Simplified isolation tree structure
interface IsolationNode {
  splitAttribute?: string;
  splitValue?: number;
  left?: IsolationNode;
  right?: IsolationNode;
  size?: number;
  depth: number;
}

function createIsolationTree(data: number[], maxDepth: number): IsolationNode {
  if (maxDepth === 0 || data.length <= 1) {
    return { depth: 0, size: data.length };
  }

  // Random split
  const min = Math.min(...data);
  const max = Math.max(...data);
  const splitValue = min + Math.random() * (max - min);

  const leftData = data.filter(d => d < splitValue);
  const rightData = data.filter(d => d >= splitValue);

  if (leftData.length === 0 || rightData.length === 0) {
    return { depth: 0, size: data.length };
  }

  return {
    splitValue,
    left: createIsolationTree(leftData, maxDepth - 1),
    right: createIsolationTree(rightData, maxDepth - 1),
    depth: maxDepth
  };
}

function getPathLength(tree: IsolationNode, value: number, currentDepth: number = 0): number {
  if (!tree.left || !tree.right || tree.splitValue === undefined) {
    return currentDepth + averagePathLength(tree.size || 1);
  }

  if (value < tree.splitValue) {
    return getPathLength(tree.left, value, currentDepth + 1);
  } else {
    return getPathLength(tree.right, value, currentDepth + 1);
  }
}

function averagePathLength(n: number): number {
  if (n <= 1) return 0;
  return 2 * (Math.log(n - 1) + 0.5772156649) - (2 * (n - 1) / n);
}

function simplePredict(window: number[]): number {
  if (window.length === 0) return 0;
  if (window.length === 1) return window[0];

  // Simple exponential smoothing
  const alpha = 0.3;
  let smoothed = window[0];

  for (let i = 1; i < window.length; i++) {
    smoothed = alpha * window[i] + (1 - alpha) * smoothed;
  }

  return smoothed;
}
