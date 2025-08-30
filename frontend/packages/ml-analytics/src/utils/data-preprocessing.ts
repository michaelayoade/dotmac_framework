import { mean, median, standardDeviation, quantile } from 'simple-statistics';
import type { TimeSeriesData, ModelDataset } from '../types';

export interface PreprocessingOptions {
  handleMissingValues: 'drop' | 'mean' | 'median' | 'forward_fill' | 'backward_fill';
  normalizeData: boolean;
  removeOutliers: boolean;
  outlierMethod: 'iqr' | 'z_score';
  outlierThreshold: number;
  aggregationPeriod?: 'hour' | 'day' | 'week' | 'month';
  smoothingWindow?: number;
}

export interface DataQuality {
  totalRecords: number;
  missingValues: number;
  duplicates: number;
  outliers: number;
  dataTypes: Record<string, string>;
  completeness: number;
  uniqueness: number;
  validity: number;
}

// Data cleaning and preprocessing
export function preprocessTimeSeriesData(
  data: TimeSeriesData[],
  options: Partial<PreprocessingOptions> = {}
): { data: TimeSeriesData[]; quality: DataQuality; transformations: string[] } {
  const config: PreprocessingOptions = {
    handleMissingValues: 'mean',
    normalizeData: false,
    removeOutliers: false,
    outlierMethod: 'iqr',
    outlierThreshold: 1.5,
    ...options
  };

  let processedData = [...data];
  const transformations: string[] = [];

  // Sort by timestamp
  processedData.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  transformations.push('sorted_by_timestamp');

  // Remove duplicates
  const uniqueData = removeDuplicates(processedData);
  const duplicatesRemoved = processedData.length - uniqueData.length;
  processedData = uniqueData;
  if (duplicatesRemoved > 0) {
    transformations.push(`removed_${duplicatesRemoved}_duplicates`);
  }

  // Handle missing values
  const { data: cleanedData, missingCount } = handleMissingValues(processedData, config.handleMissingValues);
  processedData = cleanedData;
  if (missingCount > 0) {
    transformations.push(`handled_${missingCount}_missing_values_with_${config.handleMissingValues}`);
  }

  // Remove outliers
  if (config.removeOutliers) {
    const { data: outlierFreeData, outliersRemoved } = removeOutliers(
      processedData,
      config.outlierMethod,
      config.outlierThreshold
    );
    processedData = outlierFreeData;
    if (outliersRemoved > 0) {
      transformations.push(`removed_${outliersRemoved}_outliers_using_${config.outlierMethod}`);
    }
  }

  // Apply smoothing
  if (config.smoothingWindow && config.smoothingWindow > 1) {
    processedData = applySmoothing(processedData, config.smoothingWindow);
    transformations.push(`applied_smoothing_window_${config.smoothingWindow}`);
  }

  // Normalize data
  if (config.normalizeData) {
    processedData = normalizeData(processedData);
    transformations.push('normalized_values');
  }

  // Aggregate if requested
  if (config.aggregationPeriod) {
    processedData = aggregateByPeriod(processedData, config.aggregationPeriod);
    transformations.push(`aggregated_by_${config.aggregationPeriod}`);
  }

  // Calculate data quality metrics
  const quality = assessDataQuality(data, processedData);

  return { data: processedData, quality, transformations };
}

// Remove duplicate entries
function removeDuplicates(data: TimeSeriesData[]): TimeSeriesData[] {
  const seen = new Set<string>();
  return data.filter(item => {
    const key = `${item.timestamp.getTime()}-${item.value}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

// Handle missing values
function handleMissingValues(
  data: TimeSeriesData[],
  method: PreprocessingOptions['handleMissingValues']
): { data: TimeSeriesData[]; missingCount: number } {
  let missingCount = 0;
  let processedData = [...data];

  // Find missing values (NaN, null, undefined)
  const missingIndices: number[] = [];
  processedData.forEach((item, index) => {
    if (item.value == null || isNaN(item.value)) {
      missingIndices.push(index);
      missingCount++;
    }
  });

  if (missingCount === 0) {
    return { data: processedData, missingCount };
  }

  const validValues = processedData
    .filter(item => item.value != null && !isNaN(item.value))
    .map(item => item.value);

  switch (method) {
    case 'drop':
      processedData = processedData.filter(item => item.value != null && !isNaN(item.value));
      break;

    case 'mean': {
      const meanValue = mean(validValues);
      processedData.forEach(item => {
        if (item.value == null || isNaN(item.value)) {
          item.value = meanValue;
        }
      });
      break;
    }

    case 'median': {
      const medianValue = median(validValues);
      processedData.forEach(item => {
        if (item.value == null || isNaN(item.value)) {
          item.value = medianValue;
        }
      });
      break;
    }

    case 'forward_fill':
      for (let i = 1; i < processedData.length; i++) {
        if (processedData[i].value == null || isNaN(processedData[i].value)) {
          // Find the last valid value
          for (let j = i - 1; j >= 0; j--) {
            if (processedData[j].value != null && !isNaN(processedData[j].value)) {
              processedData[i].value = processedData[j].value;
              break;
            }
          }
        }
      }
      break;

    case 'backward_fill':
      for (let i = processedData.length - 2; i >= 0; i--) {
        if (processedData[i].value == null || isNaN(processedData[i].value)) {
          // Find the next valid value
          for (let j = i + 1; j < processedData.length; j++) {
            if (processedData[j].value != null && !isNaN(processedData[j].value)) {
              processedData[i].value = processedData[j].value;
              break;
            }
          }
        }
      }
      break;
  }

  // Remove any remaining invalid values if forward/backward fill couldn't handle them
  if (method === 'forward_fill' || method === 'backward_fill') {
    processedData = processedData.filter(item => item.value != null && !isNaN(item.value));
  }

  return { data: processedData, missingCount };
}

// Remove outliers
function removeOutliers(
  data: TimeSeriesData[],
  method: 'iqr' | 'z_score',
  threshold: number
): { data: TimeSeriesData[]; outliersRemoved: number } {
  const values = data.map(d => d.value);
  let outlierIndices: Set<number>;

  if (method === 'iqr') {
    outlierIndices = detectOutliersIQR(values, threshold);
  } else {
    outlierIndices = detectOutliersZScore(values, threshold);
  }

  const cleanedData = data.filter((_, index) => !outlierIndices.has(index));

  return {
    data: cleanedData,
    outliersRemoved: outlierIndices.size
  };
}

function detectOutliersIQR(values: number[], multiplier: number): Set<number> {
  const sortedValues = [...values].sort((a, b) => a - b);
  const q1 = quantile(sortedValues, 0.25);
  const q3 = quantile(sortedValues, 0.75);
  const iqr = q3 - q1;

  const lowerBound = q1 - multiplier * iqr;
  const upperBound = q3 + multiplier * iqr;

  const outlierIndices = new Set<number>();
  values.forEach((value, index) => {
    if (value < lowerBound || value > upperBound) {
      outlierIndices.add(index);
    }
  });

  return outlierIndices;
}

function detectOutliersZScore(values: number[], threshold: number): Set<number> {
  const meanValue = mean(values);
  const stdValue = standardDeviation(values);

  const outlierIndices = new Set<number>();

  if (stdValue > 0) {
    values.forEach((value, index) => {
      const zScore = Math.abs(value - meanValue) / stdValue;
      if (zScore > threshold) {
        outlierIndices.add(index);
      }
    });
  }

  return outlierIndices;
}

// Apply smoothing
function applySmoothing(data: TimeSeriesData[], windowSize: number): TimeSeriesData[] {
  if (windowSize <= 1) return data;

  return data.map((item, index) => {
    const start = Math.max(0, index - Math.floor(windowSize / 2));
    const end = Math.min(data.length, index + Math.ceil(windowSize / 2));

    const windowValues = data.slice(start, end).map(d => d.value);
    const smoothedValue = mean(windowValues);

    return {
      ...item,
      value: smoothedValue
    };
  });
}

// Normalize data
function normalizeData(data: TimeSeriesData[]): TimeSeriesData[] {
  const values = data.map(d => d.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue;

  if (range === 0) return data;

  return data.map(item => ({
    ...item,
    value: (item.value - minValue) / range
  }));
}

// Aggregate by time period
function aggregateByPeriod(
  data: TimeSeriesData[],
  period: 'hour' | 'day' | 'week' | 'month'
): TimeSeriesData[] {
  const groupedData = new Map<string, TimeSeriesData[]>();

  data.forEach(item => {
    const key = getPeriodKey(item.timestamp, period);
    if (!groupedData.has(key)) {
      groupedData.set(key, []);
    }
    groupedData.get(key)!.push(item);
  });

  return Array.from(groupedData.entries()).map(([key, items]) => {
    const values = items.map(item => item.value);
    return {
      timestamp: new Date(key),
      value: mean(values)
    };
  }).sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
}

function getPeriodKey(timestamp: Date, period: 'hour' | 'day' | 'week' | 'month'): string {
  const date = new Date(timestamp);

  switch (period) {
    case 'hour':
      return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}-${date.getHours()}`;

    case 'day':
      return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;

    case 'week': {
      const weekStart = new Date(date);
      weekStart.setDate(date.getDate() - date.getDay());
      return `${weekStart.getFullYear()}-${weekStart.getMonth()}-${weekStart.getDate()}`;
    }

    case 'month':
      return `${date.getFullYear()}-${date.getMonth()}`;

    default:
      return date.toISOString().split('T')[0];
  }
}

// Assess data quality
function assessDataQuality(originalData: TimeSeriesData[], processedData: TimeSeriesData[]): DataQuality {
  const totalRecords = originalData.length;

  // Count missing values in original data
  const missingValues = originalData.filter(
    item => item.value == null || isNaN(item.value)
  ).length;

  // Count duplicates (already removed, so calculate from difference)
  const duplicates = totalRecords - removeDuplicates(originalData).length;

  // Estimate outliers (difference between original and processed if outliers were removed)
  const outliers = Math.max(0, originalData.length - processedData.length - missingValues - duplicates);

  const completeness = totalRecords > 0 ? (totalRecords - missingValues) / totalRecords : 1;
  const uniqueness = totalRecords > 0 ? (totalRecords - duplicates) / totalRecords : 1;
  const validity = totalRecords > 0 ? (totalRecords - missingValues - outliers) / totalRecords : 1;

  return {
    totalRecords,
    missingValues,
    duplicates,
    outliers,
    dataTypes: {
      timestamp: 'Date',
      value: 'number'
    },
    completeness: Math.round(completeness * 100) / 100,
    uniqueness: Math.round(uniqueness * 100) / 100,
    validity: Math.round(validity * 100) / 100
  };
}

// Feature engineering utilities
export function createLagFeatures(data: TimeSeriesData[], lags: number[]): ModelDataset {
  const features: number[][] = [];
  const targets: number[] = [];
  const timestamps: Date[] = [];

  const maxLag = Math.max(...lags);

  for (let i = maxLag; i < data.length; i++) {
    const featureRow: number[] = [];

    // Add lag features
    lags.forEach(lag => {
      featureRow.push(data[i - lag].value);
    });

    // Add time-based features
    const date = data[i].timestamp;
    featureRow.push(date.getHours()); // Hour of day
    featureRow.push(date.getDay()); // Day of week
    featureRow.push(date.getMonth()); // Month

    features.push(featureRow);
    targets.push(data[i].value);
    timestamps.push(data[i].timestamp);
  }

  return {
    features,
    targets,
    timestamps,
    featureNames: [
      ...lags.map(lag => `lag_${lag}`),
      'hour_of_day',
      'day_of_week',
      'month'
    ]
  };
}

export function createRollingFeatures(
  data: TimeSeriesData[],
  windows: number[]
): { features: number[][]; featureNames: string[] } {
  const features: number[][] = [];
  const featureNames: string[] = [];

  // Create feature names
  windows.forEach(window => {
    featureNames.push(`rolling_mean_${window}`);
    featureNames.push(`rolling_std_${window}`);
    featureNames.push(`rolling_min_${window}`);
    featureNames.push(`rolling_max_${window}`);
  });

  const maxWindow = Math.max(...windows);

  for (let i = maxWindow - 1; i < data.length; i++) {
    const featureRow: number[] = [];

    windows.forEach(window => {
      const windowData = data.slice(i - window + 1, i + 1).map(d => d.value);

      featureRow.push(mean(windowData)); // Rolling mean
      featureRow.push(standardDeviation(windowData)); // Rolling std
      featureRow.push(Math.min(...windowData)); // Rolling min
      featureRow.push(Math.max(...windowData)); // Rolling max
    });

    features.push(featureRow);
  }

  return { features, featureNames };
}

// Split data for training/testing
export function trainTestSplit(
  data: ModelDataset,
  testSize: number = 0.2,
  shuffle: boolean = false
): {
  trainFeatures: number[][];
  trainTargets: number[];
  testFeatures: number[][];
  testTargets: number[];
  trainTimestamps?: Date[];
  testTimestamps?: Date[];
} {
  let indices = Array.from({ length: data.features.length }, (_, i) => i);

  if (shuffle) {
    indices = shuffleArray(indices);
  }

  const splitIndex = Math.floor(data.features.length * (1 - testSize));

  const trainIndices = indices.slice(0, splitIndex);
  const testIndices = indices.slice(splitIndex);

  return {
    trainFeatures: trainIndices.map(i => data.features[i]),
    trainTargets: trainIndices.map(i => data.targets[i]),
    testFeatures: testIndices.map(i => data.features[i]),
    testTargets: testIndices.map(i => data.targets[i]),
    trainTimestamps: data.timestamps ? trainIndices.map(i => data.timestamps![i]) : undefined,
    testTimestamps: data.timestamps ? testIndices.map(i => data.timestamps![i]) : undefined
  };
}

function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}
