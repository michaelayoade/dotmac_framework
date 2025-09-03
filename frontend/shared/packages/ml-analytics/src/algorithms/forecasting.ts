import { mean, standardDeviation, linearRegression } from 'simple-statistics';
import type { ForecastResult, SeasonalityInfo } from '../types';

export interface TimeSeriesData {
  timestamp: Date;
  value: number;
}

export interface ForecastingOptions {
  method: 'linear' | 'exponential' | 'holt_winters' | 'arima' | 'seasonal_naive';
  seasonality?: {
    period: number;
    method: 'additive' | 'multiplicative';
  };
  confidenceLevel: number;
  includeSeasonality: boolean;
  trendDamping?: number;
}

// Simple Moving Average
export function simpleMovingAverage(data: number[], windowSize: number): number[] {
  const result: number[] = [];

  for (let i = windowSize - 1; i < data.length; i++) {
    const window = data.slice(i - windowSize + 1, i + 1);
    result.push(mean(window));
  }

  return result;
}

// Exponential Moving Average
export function exponentialMovingAverage(data: number[], alpha: number = 0.3): number[] {
  const result: number[] = [data[0]];

  for (let i = 1; i < data.length; i++) {
    const ema = alpha * data[i] + (1 - alpha) * result[i - 1];
    result.push(ema);
  }

  return result;
}

// Linear Trend Forecasting
export function linearTrendForecast(
  data: TimeSeriesData[],
  horizon: number
): { predictions: Array<{ timestamp: Date; value: number }> } {
  // Convert timestamps to numeric values for regression
  const baseTime = data[0].timestamp.getTime();
  const points: Array<[number, number]> = data.map((d) => [
    (d.timestamp.getTime() - baseTime) / (1000 * 60 * 60 * 24), // Convert to days
    d.value,
  ]);

  const regression = linearRegression(points);
  const slope = regression.m;
  const intercept = regression.b;

  // Generate predictions
  const lastTimestamp = data[data.length - 1].timestamp;
  const interval =
    data.length > 1
      ? data[1].timestamp.getTime() - data[0].timestamp.getTime()
      : 24 * 60 * 60 * 1000; // Default to daily

  const predictions: Array<{ timestamp: Date; value: number }> = [];

  for (let i = 1; i <= horizon; i++) {
    const futureTimestamp = new Date(lastTimestamp.getTime() + interval * i);
    const x = (futureTimestamp.getTime() - baseTime) / (1000 * 60 * 60 * 24);
    const predictedValue = slope * x + intercept;

    predictions.push({
      timestamp: futureTimestamp,
      value: Math.max(0, predictedValue), // Ensure non-negative values
    });
  }

  return { predictions };
}

// Simple Exponential Smoothing
export function exponentialSmoothingForecast(
  data: number[],
  horizon: number,
  alpha: number = 0.3
): number[] {
  if (data.length === 0) return [];

  let level = data[0];
  const smoothed: number[] = [level];

  // Smooth historical data
  for (let i = 1; i < data.length; i++) {
    level = alpha * data[i] + (1 - alpha) * level;
    smoothed.push(level);
  }

  // Generate forecasts
  const forecasts: number[] = [];
  for (let i = 0; i < horizon; i++) {
    forecasts.push(level);
  }

  return forecasts;
}

// Double Exponential Smoothing (Holt's method)
export function holtForecast(
  data: number[],
  horizon: number,
  alpha: number = 0.3,
  beta: number = 0.1
): { forecasts: number[]; level: number; trend: number } {
  if (data.length < 2) {
    return { forecasts: Array(horizon).fill(data[0] || 0), level: data[0] || 0, trend: 0 };
  }

  let level = data[0];
  let trend = data[1] - data[0];

  // Apply smoothing to historical data
  for (let i = 1; i < data.length; i++) {
    const prevLevel = level;
    level = alpha * data[i] + (1 - alpha) * (level + trend);
    trend = beta * (level - prevLevel) + (1 - beta) * trend;
  }

  // Generate forecasts
  const forecasts: number[] = [];
  for (let h = 1; h <= horizon; h++) {
    forecasts.push(level + h * trend);
  }

  return { forecasts, level, trend };
}

// Triple Exponential Smoothing (Holt-Winters)
export function holtWintersForecast(
  data: number[],
  horizon: number,
  seasonLength: number,
  alpha: number = 0.3,
  beta: number = 0.1,
  gamma: number = 0.1,
  seasonal: 'additive' | 'multiplicative' = 'additive'
): {
  forecasts: number[];
  level: number;
  trend: number;
  seasonals: number[];
} {
  if (data.length < seasonLength * 2) {
    // Fallback to Holt's method if insufficient data
    const holtResult = holtForecast(data, horizon, alpha, beta);
    return {
      forecasts: holtResult.forecasts,
      level: holtResult.level,
      trend: holtResult.trend,
      seasonals: Array(seasonLength).fill(seasonal === 'additive' ? 0 : 1),
    };
  }

  // Initialize level, trend, and seasonal components
  let level = mean(data.slice(0, seasonLength));
  let trend = 0;

  // Calculate initial trend
  for (let i = 0; i < seasonLength; i++) {
    trend += (data[seasonLength + i] - data[i]) / seasonLength;
  }
  trend /= seasonLength;

  // Initialize seasonal components
  const seasonals: number[] = [];
  for (let i = 0; i < seasonLength; i++) {
    if (seasonal === 'additive') {
      seasonals[i] = data[i] - level;
    } else {
      seasonals[i] = level !== 0 ? data[i] / level : 1;
    }
  }

  // Apply triple smoothing
  for (let i = 0; i < data.length; i++) {
    const seasonalIndex = i % seasonLength;
    const prevLevel = level;

    if (seasonal === 'additive') {
      level = alpha * (data[i] - seasonals[seasonalIndex]) + (1 - alpha) * (level + trend);
      trend = beta * (level - prevLevel) + (1 - beta) * trend;
      seasonals[seasonalIndex] = gamma * (data[i] - level) + (1 - gamma) * seasonals[seasonalIndex];
    } else {
      level = alpha * (data[i] / seasonals[seasonalIndex]) + (1 - alpha) * (level + trend);
      trend = beta * (level - prevLevel) + (1 - beta) * trend;
      seasonals[seasonalIndex] = gamma * (data[i] / level) + (1 - gamma) * seasonals[seasonalIndex];
    }
  }

  // Generate forecasts
  const forecasts: number[] = [];
  for (let h = 1; h <= horizon; h++) {
    const seasonalIndex = (data.length + h - 1) % seasonLength;
    let forecast: number;

    if (seasonal === 'additive') {
      forecast = level + h * trend + seasonals[seasonalIndex];
    } else {
      forecast = (level + h * trend) * seasonals[seasonalIndex];
    }

    forecasts.push(Math.max(0, forecast));
  }

  return { forecasts, level, trend, seasonals };
}

// Seasonal Naive Forecast
export function seasonalNaiveForecast(
  data: number[],
  horizon: number,
  seasonLength: number
): number[] {
  if (data.length < seasonLength) {
    return Array(horizon).fill(data[data.length - 1] || 0);
  }

  const forecasts: number[] = [];
  const lastSeasonData = data.slice(-seasonLength);

  for (let i = 0; i < horizon; i++) {
    const seasonalIndex = i % seasonLength;
    forecasts.push(lastSeasonData[seasonalIndex]);
  }

  return forecasts;
}

// Detect Seasonality
export function detectSeasonality(data: number[]): SeasonalityInfo {
  if (data.length < 24) {
    return { detected: false };
  }

  // Test common seasonal periods
  const testPeriods = [7, 12, 24, 30, 365]; // Weekly, monthly, daily (hourly), monthly (daily), yearly (daily)
  let bestPeriod = 0;
  let bestStrength = 0;

  for (const period of testPeriods) {
    if (data.length < period * 2) continue;

    const strength = calculateSeasonalStrength(data, period);
    if (strength > bestStrength) {
      bestStrength = strength;
      bestPeriod = period;
    }
  }

  if (bestStrength > 0.3) {
    // Threshold for seasonal detection
    const components = decomposeTimeSeries(data, bestPeriod);
    return {
      detected: true,
      period: bestPeriod,
      strength: bestStrength,
      components,
    };
  }

  return { detected: false };
}

function calculateSeasonalStrength(data: number[], period: number): number {
  if (data.length < period * 2) return 0;

  const seasons = Math.floor(data.length / period);
  const seasonalMeans: number[] = Array(period).fill(0);
  const seasonalCounts: number[] = Array(period).fill(0);

  // Calculate seasonal means
  for (let i = 0; i < data.length; i++) {
    const seasonIndex = i % period;
    seasonalMeans[seasonIndex] += data[i];
    seasonalCounts[seasonIndex]++;
  }

  for (let i = 0; i < period; i++) {
    seasonalMeans[i] /= seasonalCounts[i];
  }

  // Calculate seasonal variance vs total variance
  const overallMean = mean(data);
  let seasonalVariance = 0;
  let totalVariance = 0;

  for (let i = 0; i < data.length; i++) {
    const seasonIndex = i % period;
    seasonalVariance += Math.pow(seasonalMeans[seasonIndex] - overallMean, 2);
    totalVariance += Math.pow(data[i] - overallMean, 2);
  }

  return totalVariance > 0 ? seasonalVariance / totalVariance : 0;
}

function decomposeTimeSeries(
  data: number[],
  period: number
): {
  trend: number[];
  seasonal: number[];
  residual: number[];
} {
  const trend = simpleMovingAverage(data, Math.max(3, Math.floor(period / 2)));
  const seasonal: number[] = Array(data.length).fill(0);
  const residual: number[] = Array(data.length).fill(0);

  // Extend trend to match data length
  const extendedTrend = [...Array(Math.floor((period - 1) / 2)).fill(trend[0]), ...trend];
  while (extendedTrend.length < data.length) {
    extendedTrend.push(trend[trend.length - 1]);
  }

  // Calculate seasonal component
  const seasonalComponents: number[] = Array(period).fill(0);
  const seasonalCounts: number[] = Array(period).fill(0);

  for (let i = 0; i < data.length; i++) {
    if (i < extendedTrend.length) {
      const detrended = data[i] - extendedTrend[i];
      const seasonIndex = i % period;
      seasonalComponents[seasonIndex] += detrended;
      seasonalCounts[seasonIndex]++;
    }
  }

  // Average seasonal components
  for (let i = 0; i < period; i++) {
    if (seasonalCounts[i] > 0) {
      seasonalComponents[i] /= seasonalCounts[i];
    }
  }

  // Apply seasonal components and calculate residuals
  for (let i = 0; i < data.length; i++) {
    const seasonIndex = i % period;
    seasonal[i] = seasonalComponents[seasonIndex];
    if (i < extendedTrend.length) {
      residual[i] = data[i] - extendedTrend[i] - seasonal[i];
    }
  }

  return {
    trend: extendedTrend.slice(0, data.length),
    seasonal,
    residual,
  };
}

// Calculate forecast confidence intervals
export function calculateConfidenceIntervals(
  data: number[],
  forecasts: number[],
  confidenceLevel: number = 0.95
): Array<{ lower: number; upper: number }> {
  const residuals: number[] = [];

  // Calculate residuals from a simple method (moving average)
  const windowSize = Math.min(5, Math.floor(data.length / 4));
  for (let i = windowSize; i < data.length; i++) {
    const window = data.slice(i - windowSize, i);
    const predicted = mean(window);
    residuals.push(data[i] - predicted);
  }

  if (residuals.length === 0) {
    return forecasts.map((f) => ({ lower: f * 0.9, upper: f * 1.1 }));
  }

  const residualStd = standardDeviation(residuals);
  const zScore = confidenceLevel === 0.95 ? 1.96 : 2.58; // 95% or 99%

  return forecasts.map((forecast, index) => {
    const interval = zScore * residualStd * Math.sqrt(index + 1); // Increasing uncertainty
    return {
      lower: Math.max(0, forecast - interval),
      upper: forecast + interval,
    };
  });
}

// Comprehensive forecasting function
export function createForecast(
  data: TimeSeriesData[],
  horizon: number,
  options: Partial<ForecastingOptions> = {}
): ForecastResult {
  const config: ForecastingOptions = {
    method: 'holt_winters',
    confidenceLevel: 0.95,
    includeSeasonality: true,
    ...options,
  };

  const values = data.map((d) => d.value);
  const timestamps = data.map((d) => d.timestamp);

  // Detect seasonality if requested
  let seasonalityInfo: SeasonalityInfo = { detected: false };
  if (config.includeSeasonality) {
    seasonalityInfo = detectSeasonality(values);
  }

  // Choose forecasting method
  let forecasts: number[];

  switch (config.method) {
    case 'linear': {
      const linearResult = linearTrendForecast(data, horizon);
      forecasts = linearResult.predictions.map((p) => p.value);
      break;
    }

    case 'exponential':
      forecasts = exponentialSmoothingForecast(values, horizon);
      break;

    case 'holt_winters': {
      const period = seasonalityInfo.detected ? seasonalityInfo.period! : 7;
      const hwResult = holtWintersForecast(values, horizon, period);
      forecasts = hwResult.forecasts;
      break;
    }

    case 'seasonal_naive': {
      const period = seasonalityInfo.detected ? seasonalityInfo.period! : 7;
      forecasts = seasonalNaiveForecast(values, horizon, period);
      break;
    }

    default: {
      // Default to Holt's method
      const holtResult = holtForecast(values, horizon);
      forecasts = holtResult.forecasts;
    }
  }

  // Calculate confidence intervals
  const confidenceIntervals = calculateConfidenceIntervals(
    values,
    forecasts,
    config.confidenceLevel
  );

  // Generate future timestamps
  const lastTimestamp = timestamps[timestamps.length - 1];
  const interval =
    timestamps.length > 1 ? timestamps[1].getTime() - timestamps[0].getTime() : 24 * 60 * 60 * 1000;

  const predictions = forecasts.map((value, index) => ({
    timestamp: new Date(lastTimestamp.getTime() + interval * (index + 1)),
    value: Math.max(0, value),
    confidence: config.confidenceLevel,
    bounds: {
      lower: confidenceIntervals[index].lower,
      upper: confidenceIntervals[index].upper,
    },
  }));

  // Calculate forecast metrics (simplified)
  const mae = values.length > 10 ? calculateMAE(values.slice(-10), forecasts.slice(0, 10)) : 0;
  const mse = values.length > 10 ? calculateMSE(values.slice(-10), forecasts.slice(0, 10)) : 0;

  return {
    id: `forecast-${Date.now()}`,
    modelId: 'built-in-forecast',
    generatedAt: new Date(),
    horizon,
    granularity: 'day', // Would be inferred from data
    predictions,
    metrics: {
      mae,
      mse,
      rmse: Math.sqrt(mse),
      mape: values.length > 10 ? calculateMAPE(values.slice(-10), forecasts.slice(0, 10)) : 0,
      accuracy: Math.max(0, 1 - mae / mean(values.filter((v) => v > 0))),
      trendAccuracy: 0.8, // Simplified
    },
    seasonality: seasonalityInfo,
  };
}

// Helper functions for metrics
function calculateMAE(actual: number[], predicted: number[]): number {
  const errors = actual.map((a, i) => Math.abs(a - (predicted[i] || 0)));
  return mean(errors);
}

function calculateMSE(actual: number[], predicted: number[]): number {
  const errors = actual.map((a, i) => Math.pow(a - (predicted[i] || 0), 2));
  return mean(errors);
}

function calculateMAPE(actual: number[], predicted: number[]): number {
  const errors = actual
    .filter((a) => a !== 0)
    .map((a, i) => Math.abs((a - (predicted[i] || 0)) / a) * 100);
  return errors.length > 0 ? mean(errors) : 0;
}
