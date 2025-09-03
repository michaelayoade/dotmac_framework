// Core services
export { MLService } from './services/MLService';
export { InsightService } from './services/InsightService';

// Algorithms
export * from './algorithms';

// Utilities
export * from './utils';

// Types
export * from './types';

// Main exports for easy consumption
export {
  // Forecasting
  createForecast,
  linearTrendForecast,
  exponentialSmoothingForecast,
  holtForecast,
  holtWintersForecast,
  detectSeasonality,

  // Anomaly Detection
  detectAnomalies,
  zScoreAnomalyDetection,
  iqrAnomalyDetection,
  statisticalAnomalyDetection,

  // Pattern Recognition
  recognizePatterns,
  detectTrendPatterns,
  detectSeasonalPatterns,
  detectSpikesAndDips,
  detectRepeatingPatterns,

  // Data Preprocessing
  preprocessTimeSeriesData,
  createLagFeatures,
  createRollingFeatures,
  trainTestSplit,
} from './algorithms';

// Default export for convenience
export default {
  MLService,
  InsightService,
};
