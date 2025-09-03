import { mean, median, standardDeviation, quantile } from 'simple-statistics';
import type { TimeSeriesData } from '../types';

export interface FeatureEngineeringOptions {
  includeTimeFeatures: boolean;
  includeLagFeatures: boolean;
  includeRollingFeatures: boolean;
  includeSeasonalFeatures: boolean;
  lagPeriods: number[];
  rollingWindows: number[];
  seasonalPeriods: number[];
}

export interface EngineeredFeatures {
  features: number[][];
  featureNames: string[];
  timestamps: Date[];
  metadata: {
    originalFeatureCount: number;
    engineeredFeatureCount: number;
    transformations: string[];
  };
}

// Main feature engineering function
export function engineerFeatures(
  data: TimeSeriesData[],
  options: Partial<FeatureEngineeringOptions> = {}
): EngineeredFeatures {
  const config: FeatureEngineeringOptions = {
    includeTimeFeatures: true,
    includeLagFeatures: true,
    includeRollingFeatures: true,
    includeSeasonalFeatures: true,
    lagPeriods: [1, 2, 3, 7, 14],
    rollingWindows: [3, 7, 14, 30],
    seasonalPeriods: [7, 30, 365],
    ...options,
  };

  const transformations: string[] = [];
  let allFeatures: number[][] = [];
  let allFeatureNames: string[] = [];

  // Start with basic value feature
  const values = data.map((d) => d.value);
  allFeatures = values.map((v) => [v]);
  allFeatureNames = ['value'];
  transformations.push('base_value');

  // Time-based features
  if (config.includeTimeFeatures) {
    const { features: timeFeatures, featureNames: timeFeatureNames } = createTimeFeatures(data);
    allFeatures = combineFeatures(allFeatures, timeFeatures);
    allFeatureNames.push(...timeFeatureNames);
    transformations.push('time_features');
  }

  // Lag features
  if (config.includeLagFeatures) {
    const { features: lagFeatures, featureNames: lagFeatureNames } = createLagFeatures(
      data,
      config.lagPeriods
    );
    const maxLag = Math.max(...config.lagPeriods);

    // Align features by trimming earlier ones
    if (allFeatures.length > lagFeatures.length) {
      allFeatures = allFeatures.slice(-lagFeatures.length);
    }

    allFeatures = combineFeatures(allFeatures, lagFeatures);
    allFeatureNames.push(...lagFeatureNames);
    transformations.push(`lag_features_${config.lagPeriods.join('_')}`);
  }

  // Rolling window features
  if (config.includeRollingFeatures) {
    const { features: rollingFeatures, featureNames: rollingFeatureNames } =
      createRollingWindowFeatures(data, config.rollingWindows);

    // Align features
    const minLength = Math.min(allFeatures.length, rollingFeatures.length);
    allFeatures = allFeatures.slice(-minLength);
    allFeatures = combineFeatures(allFeatures, rollingFeatures.slice(-minLength));
    allFeatureNames.push(...rollingFeatureNames);
    transformations.push(`rolling_features_${config.rollingWindows.join('_')}`);
  }

  // Seasonal features
  if (config.includeSeasonalFeatures) {
    const { features: seasonalFeatures, featureNames: seasonalFeatureNames } =
      createSeasonalFeatures(data, config.seasonalPeriods);

    // Align features
    const minLength = Math.min(allFeatures.length, seasonalFeatures.length);
    allFeatures = allFeatures.slice(-minLength);
    allFeatures = combineFeatures(allFeatures, seasonalFeatures.slice(-minLength));
    allFeatureNames.push(...seasonalFeatureNames);
    transformations.push(`seasonal_features_${config.seasonalPeriods.join('_')}`);
  }

  // Technical indicators
  const { features: technicalFeatures, featureNames: technicalFeatureNames } =
    createTechnicalIndicators(data);
  const minLength = Math.min(allFeatures.length, technicalFeatures.length);
  allFeatures = allFeatures.slice(-minLength);
  allFeatures = combineFeatures(allFeatures, technicalFeatures.slice(-minLength));
  allFeatureNames.push(...technicalFeatureNames);
  transformations.push('technical_indicators');

  // Get corresponding timestamps
  const startIndex = data.length - allFeatures.length;
  const timestamps = data.slice(startIndex).map((d) => d.timestamp);

  return {
    features: allFeatures,
    featureNames: allFeatureNames,
    timestamps,
    metadata: {
      originalFeatureCount: 1, // Just the value
      engineeredFeatureCount: allFeatureNames.length,
      transformations,
    },
  };
}

// Time-based features
export function createTimeFeatures(data: TimeSeriesData[]): {
  features: number[][];
  featureNames: string[];
} {
  const features: number[][] = [];
  const featureNames = [
    'hour',
    'day_of_week',
    'day_of_month',
    'month',
    'quarter',
    'year',
    'is_weekend',
    'is_month_start',
    'is_month_end',
    'is_quarter_start',
    'is_quarter_end',
    'days_since_epoch',
  ];

  data.forEach((item) => {
    const date = item.timestamp;
    const featureRow: number[] = [];

    featureRow.push(date.getHours());
    featureRow.push(date.getDay());
    featureRow.push(date.getDate());
    featureRow.push(date.getMonth() + 1);
    featureRow.push(Math.floor(date.getMonth() / 3) + 1);
    featureRow.push(date.getFullYear());
    featureRow.push(date.getDay() === 0 || date.getDay() === 6 ? 1 : 0);
    featureRow.push(date.getDate() === 1 ? 1 : 0);
    featureRow.push(isLastDayOfMonth(date) ? 1 : 0);
    featureRow.push(date.getDate() <= 7 && date.getMonth() % 3 === 0 ? 1 : 0);
    featureRow.push(isLastWeekOfQuarter(date) ? 1 : 0);
    featureRow.push(Math.floor(date.getTime() / (1000 * 60 * 60 * 24)));

    features.push(featureRow);
  });

  return { features, featureNames };
}

// Lag features
export function createLagFeatures(
  data: TimeSeriesData[],
  lagPeriods: number[]
): { features: number[][]; featureNames: string[] } {
  const features: number[][] = [];
  const featureNames: string[] = [];
  const values = data.map((d) => d.value);

  lagPeriods.forEach((lag) => {
    featureNames.push(`lag_${lag}`);
  });

  const maxLag = Math.max(...lagPeriods);

  for (let i = maxLag; i < data.length; i++) {
    const featureRow: number[] = [];

    lagPeriods.forEach((lag) => {
      featureRow.push(values[i - lag]);
    });

    features.push(featureRow);
  }

  return { features, featureNames };
}

// Rolling window features
export function createRollingWindowFeatures(
  data: TimeSeriesData[],
  windows: number[]
): { features: number[][]; featureNames: string[] } {
  const features: number[][] = [];
  const featureNames: string[] = [];
  const values = data.map((d) => d.value);

  windows.forEach((window) => {
    featureNames.push(`rolling_mean_${window}`);
    featureNames.push(`rolling_std_${window}`);
    featureNames.push(`rolling_min_${window}`);
    featureNames.push(`rolling_max_${window}`);
    featureNames.push(`rolling_median_${window}`);
    featureNames.push(`rolling_q25_${window}`);
    featureNames.push(`rolling_q75_${window}`);
  });

  const maxWindow = Math.max(...windows);

  for (let i = maxWindow - 1; i < values.length; i++) {
    const featureRow: number[] = [];

    windows.forEach((window) => {
      const windowData = values.slice(i - window + 1, i + 1);

      featureRow.push(mean(windowData));
      featureRow.push(standardDeviation(windowData));
      featureRow.push(Math.min(...windowData));
      featureRow.push(Math.max(...windowData));
      featureRow.push(median(windowData));
      featureRow.push(quantile(windowData, 0.25));
      featureRow.push(quantile(windowData, 0.75));
    });

    features.push(featureRow);
  }

  return { features, featureNames };
}

// Seasonal features
export function createSeasonalFeatures(
  data: TimeSeriesData[],
  periods: number[]
): { features: number[][]; featureNames: string[] } {
  const features: number[][] = [];
  const featureNames: string[] = [];
  const values = data.map((d) => d.value);

  periods.forEach((period) => {
    featureNames.push(`seasonal_mean_${period}`);
    featureNames.push(`seasonal_std_${period}`);
    featureNames.push(`seasonal_position_${period}`);
  });

  data.forEach((item, index) => {
    const featureRow: number[] = [];

    periods.forEach((period) => {
      // Calculate seasonal statistics
      const seasonalValues: number[] = [];
      const currentPosition = index % period;

      // Collect all values at the same seasonal position
      for (let i = currentPosition; i < values.length; i += period) {
        if (i < index) {
          // Only use past data
          seasonalValues.push(values[i]);
        }
      }

      if (seasonalValues.length > 0) {
        featureRow.push(mean(seasonalValues));
        featureRow.push(standardDeviation(seasonalValues));
      } else {
        featureRow.push(0);
        featureRow.push(0);
      }

      // Seasonal position (normalized)
      featureRow.push(currentPosition / period);
    });

    features.push(featureRow);
  });

  return { features, featureNames };
}

// Technical indicators
export function createTechnicalIndicators(data: TimeSeriesData[]): {
  features: number[][];
  featureNames: string[];
} {
  const features: number[][] = [];
  const featureNames = [
    'rsi_14',
    'macd_signal',
    'bb_position',
    'momentum_5',
    'momentum_10',
    'price_change_1',
    'price_change_7',
    'volatility_10',
    'trend_strength',
  ];

  const values = data.map((d) => d.value);

  // Calculate indicators
  const rsi14 = calculateRSI(values, 14);
  const macd = calculateMACD(values);
  const bb = calculateBollingerBands(values, 20, 2);

  for (let i = 20; i < data.length; i++) {
    // Start from index 20 to ensure all indicators are available
    const featureRow: number[] = [];

    // RSI
    featureRow.push(rsi14[i] || 50);

    // MACD signal
    featureRow.push(macd.signal[i] || 0);

    // Bollinger Band position
    const bbUpper = bb.upper[i] || values[i];
    const bbLower = bb.lower[i] || values[i];
    const bbPosition = bbUpper !== bbLower ? (values[i] - bbLower) / (bbUpper - bbLower) : 0.5;
    featureRow.push(bbPosition);

    // Momentum
    featureRow.push(i >= 5 ? (values[i] - values[i - 5]) / values[i - 5] : 0);
    featureRow.push(i >= 10 ? (values[i] - values[i - 10]) / values[i - 10] : 0);

    // Price changes
    featureRow.push(i >= 1 ? (values[i] - values[i - 1]) / values[i - 1] : 0);
    featureRow.push(i >= 7 ? (values[i] - values[i - 7]) / values[i - 7] : 0);

    // Volatility (10-period standard deviation)
    const volatilityWindow = values.slice(Math.max(0, i - 9), i + 1);
    featureRow.push(standardDeviation(volatilityWindow) / mean(volatilityWindow));

    // Trend strength (correlation with time)
    const trendWindow = values.slice(Math.max(0, i - 19), i + 1);
    const trendIndices = Array.from({ length: trendWindow.length }, (_, idx) => idx);
    featureRow.push(calculateCorrelation(trendIndices, trendWindow));

    features.push(featureRow);
  }

  return { features, featureNames };
}

// Feature scaling and normalization
export function normalizeFeatures(
  features: number[][],
  method: 'minmax' | 'zscore' | 'robust' = 'zscore'
): {
  normalizedFeatures: number[][];
  scalers: Array<{
    min?: number;
    max?: number;
    mean?: number;
    std?: number;
    median?: number;
    iqr?: number;
  }>;
} {
  if (features.length === 0) return { normalizedFeatures: [], scalers: [] };

  const numFeatures = features[0].length;
  const normalizedFeatures: number[][] = [];
  const scalers: Array<any> = [];

  for (let featureIdx = 0; featureIdx < numFeatures; featureIdx++) {
    const featureValues = features.map((row) => row[featureIdx]);
    let scaler: any = {};

    switch (method) {
      case 'minmax': {
        const min = Math.min(...featureValues);
        const max = Math.max(...featureValues);
        scaler = { min, max };
        break;
      }
      case 'zscore': {
        const meanVal = mean(featureValues);
        const stdVal = standardDeviation(featureValues);
        scaler = { mean: meanVal, std: stdVal };
        break;
      }
      case 'robust': {
        const medianVal = median(featureValues);
        const q25 = quantile(featureValues, 0.25);
        const q75 = quantile(featureValues, 0.75);
        const iqr = q75 - q25;
        scaler = { median: medianVal, iqr };
        break;
      }
    }

    scalers.push(scaler);
  }

  // Apply normalization
  features.forEach((row) => {
    const normalizedRow: number[] = [];

    row.forEach((value, featureIdx) => {
      const scaler = scalers[featureIdx];
      let normalizedValue: number;

      switch (method) {
        case 'minmax':
          normalizedValue =
            scaler.max !== scaler.min ? (value - scaler.min) / (scaler.max - scaler.min) : 0;
          break;
        case 'zscore':
          normalizedValue = scaler.std !== 0 ? (value - scaler.mean) / scaler.std : 0;
          break;
        case 'robust':
          normalizedValue = scaler.iqr !== 0 ? (value - scaler.median) / scaler.iqr : 0;
          break;
        default:
          normalizedValue = value;
      }

      normalizedRow.push(normalizedValue);
    });

    normalizedFeatures.push(normalizedRow);
  });

  return { normalizedFeatures, scalers };
}

// Feature selection
export function selectTopFeatures(
  features: number[][],
  targets: number[],
  featureNames: string[],
  k: number,
  method: 'correlation' | 'variance' = 'correlation'
): {
  selectedFeatures: number[][];
  selectedFeatureNames: string[];
  featureScores: Array<{ name: string; score: number; rank: number }>;
} {
  if (features.length !== targets.length) {
    throw new Error('Features and targets must have the same length');
  }

  const numFeatures = features[0]?.length || 0;
  const featureScores: Array<{ name: string; score: number; rank: number }> = [];

  for (let featureIdx = 0; featureIdx < numFeatures; featureIdx++) {
    const featureValues = features.map((row) => row[featureIdx]);
    let score: number;

    switch (method) {
      case 'correlation':
        score = Math.abs(calculateCorrelation(featureValues, targets));
        break;
      case 'variance':
        score = standardDeviation(featureValues);
        break;
      default:
        score = Math.abs(calculateCorrelation(featureValues, targets));
    }

    featureScores.push({
      name: featureNames[featureIdx] || `feature_${featureIdx}`,
      score,
      rank: 0, // Will be set after sorting
    });
  }

  // Sort by score and assign ranks
  featureScores.sort((a, b) => b.score - a.score);
  featureScores.forEach((item, index) => {
    item.rank = index + 1;
  });

  // Select top k features
  const topFeatureIndices = featureScores
    .slice(0, k)
    .map((item) => featureNames.indexOf(item.name));

  const selectedFeatures = features.map((row) => topFeatureIndices.map((idx) => row[idx]));

  const selectedFeatureNames = topFeatureIndices.map((idx) => featureNames[idx]);

  return {
    selectedFeatures,
    selectedFeatureNames,
    featureScores,
  };
}

// Helper functions
function combineFeatures(features1: number[][], features2: number[][]): number[][] {
  const minLength = Math.min(features1.length, features2.length);
  const combined: number[][] = [];

  for (let i = 0; i < minLength; i++) {
    const row1 = features1[features1.length - minLength + i] || [];
    const row2 = features2[features2.length - minLength + i] || [];
    combined.push([...row1, ...row2]);
  }

  return combined;
}

function isLastDayOfMonth(date: Date): boolean {
  const nextDay = new Date(date);
  nextDay.setDate(date.getDate() + 1);
  return nextDay.getMonth() !== date.getMonth();
}

function isLastWeekOfQuarter(date: Date): boolean {
  const month = date.getMonth();
  const isQuarterEnd = month === 2 || month === 5 || month === 8 || month === 11;
  return isQuarterEnd && isLastDayOfMonth(date);
}

function calculateRSI(values: number[], period: number = 14): number[] {
  const rsi: number[] = [];

  if (values.length < period + 1) {
    return Array(values.length).fill(50);
  }

  for (let i = 0; i < period; i++) {
    rsi.push(50); // Default neutral RSI
  }

  for (let i = period; i < values.length; i++) {
    let gains = 0;
    let losses = 0;

    for (let j = i - period + 1; j <= i; j++) {
      const change = values[j] - values[j - 1];
      if (change > 0) {
        gains += change;
      } else {
        losses -= change;
      }
    }

    const avgGain = gains / period;
    const avgLoss = losses / period;

    if (avgLoss === 0) {
      rsi.push(100);
    } else {
      const rs = avgGain / avgLoss;
      rsi.push(100 - 100 / (1 + rs));
    }
  }

  return rsi;
}

function calculateMACD(
  values: number[],
  fastPeriod: number = 12,
  slowPeriod: number = 26,
  signalPeriod: number = 9
): { macd: number[]; signal: number[]; histogram: number[] } {
  const ema12 = calculateEMA(values, fastPeriod);
  const ema26 = calculateEMA(values, slowPeriod);

  const macd = ema12.map((fast, i) => fast - ema26[i]);
  const signal = calculateEMA(macd, signalPeriod);
  const histogram = macd.map((m, i) => m - signal[i]);

  return { macd, signal, histogram };
}

function calculateEMA(values: number[], period: number): number[] {
  const ema: number[] = [];
  const multiplier = 2 / (period + 1);

  ema[0] = values[0];

  for (let i = 1; i < values.length; i++) {
    ema[i] = values[i] * multiplier + ema[i - 1] * (1 - multiplier);
  }

  return ema;
}

function calculateBollingerBands(
  values: number[],
  period: number = 20,
  stdDev: number = 2
): { upper: number[]; lower: number[]; middle: number[] } {
  const upper: number[] = [];
  const lower: number[] = [];
  const middle: number[] = [];

  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      upper.push(values[i]);
      lower.push(values[i]);
      middle.push(values[i]);
    } else {
      const window = values.slice(i - period + 1, i + 1);
      const sma = mean(window);
      const std = standardDeviation(window);

      middle.push(sma);
      upper.push(sma + stdDev * std);
      lower.push(sma - stdDev * std);
    }
  }

  return { upper, lower, middle };
}

function calculateCorrelation(x: number[], y: number[]): number {
  if (x.length !== y.length || x.length === 0) return 0;

  const n = x.length;
  const meanX = mean(x);
  const meanY = mean(y);

  let numerator = 0;
  let sumXSquared = 0;
  let sumYSquared = 0;

  for (let i = 0; i < n; i++) {
    const xDiff = x[i] - meanX;
    const yDiff = y[i] - meanY;

    numerator += xDiff * yDiff;
    sumXSquared += xDiff * xDiff;
    sumYSquared += yDiff * yDiff;
  }

  const denominator = Math.sqrt(sumXSquared * sumYSquared);
  return denominator > 0 ? numerator / denominator : 0;
}
