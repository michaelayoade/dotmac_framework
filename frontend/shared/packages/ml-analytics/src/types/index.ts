// Core ML Analytics Types
export interface MLModel {
  id: string;
  name: string;
  type: ModelType;
  status: ModelStatus;
  version: string;
  createdAt: Date;
  updatedAt: Date;
  trainedAt?: Date;
  accuracy?: number;
  parameters: ModelParameters;
  metadata: ModelMetadata;
}

export type ModelType =
  | 'linear_regression'
  | 'polynomial_regression'
  | 'decision_tree'
  | 'random_forest'
  | 'neural_network'
  | 'time_series_forecast'
  | 'anomaly_detection'
  | 'classification'
  | 'clustering'
  | 'association_rules';

export type ModelStatus = 'training' | 'trained' | 'deployed' | 'deprecated' | 'failed';

export interface ModelParameters {
  hyperparameters: Record<string, any>;
  features: string[];
  target: string;
  trainingConfig: TrainingConfig;
  validationConfig: ValidationConfig;
}

export interface TrainingConfig {
  trainSplit: number;
  validationSplit: number;
  testSplit: number;
  maxEpochs?: number;
  batchSize?: number;
  learningRate?: number;
  regularization?: {
    type: 'l1' | 'l2' | 'elastic_net';
    lambda: number;
  };
  earlyStoppingPatience?: number;
}

export interface ValidationConfig {
  crossValidationFolds?: number;
  validationMetrics: string[];
  minimumAccuracy?: number;
  maximumLoss?: number;
}

export interface ModelMetadata {
  description?: string;
  tags?: string[];
  author: string;
  dataSource: string;
  featureEngineering?: string[];
  experimentId?: string;
  parentModelId?: string;
}

// Prediction and Forecasting Types
export interface Prediction {
  id: string;
  modelId: string;
  timestamp: Date;
  input: Record<string, any>;
  output: PredictionOutput;
  confidence: number;
  explanation?: PredictionExplanation;
  metadata?: Record<string, any>;
}

export interface PredictionOutput {
  value: number | string | boolean;
  probability?: number;
  class?: string;
  distribution?: Record<string, number>;
  bounds?: {
    lower: number;
    upper: number;
    confidenceLevel: number;
  };
}

export interface PredictionExplanation {
  featureImportance: Record<string, number>;
  reasoning: string[];
  similarSamples?: Array<{
    id: string;
    similarity: number;
    outcome: any;
  }>;
}

export interface ForecastResult {
  id: string;
  modelId: string;
  generatedAt: Date;
  horizon: number; // Number of periods ahead
  granularity: 'minute' | 'hour' | 'day' | 'week' | 'month' | 'quarter' | 'year';
  predictions: Array<{
    timestamp: Date;
    value: number;
    confidence: number;
    bounds: {
      lower: number;
      upper: number;
    };
  }>;
  metrics: ForecastMetrics;
  seasonality?: SeasonalityInfo;
}

export interface ForecastMetrics {
  mae: number; // Mean Absolute Error
  mse: number; // Mean Squared Error
  rmse: number; // Root Mean Squared Error
  mape: number; // Mean Absolute Percentage Error
  accuracy: number;
  trendAccuracy: number;
}

export interface SeasonalityInfo {
  detected: boolean;
  period?: number;
  strength?: number;
  components?: {
    trend: number[];
    seasonal: number[];
    residual: number[];
  };
}

// Anomaly Detection Types
export interface AnomalyDetection {
  id: string;
  timestamp: Date;
  dataPoint: Record<string, any>;
  anomalyScore: number;
  isAnomaly: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  type: AnomalyType;
  explanation: string;
  context: AnomalyContext;
  recommendations?: string[];
}

export type AnomalyType =
  | 'statistical_outlier'
  | 'contextual_anomaly'
  | 'collective_anomaly'
  | 'point_anomaly'
  | 'seasonal_anomaly'
  | 'trend_anomaly';

export interface AnomalyContext {
  baseline: {
    mean: number;
    standardDeviation: number;
    median: number;
    percentile95: number;
  };
  historicalRange: {
    min: number;
    max: number;
    typical: [number, number]; // [lower bound, upper bound]
  };
  seasonalExpectation?: number;
  trendExpectation?: number;
}

// Pattern Recognition Types
export interface PatternRecognition {
  id: string;
  type: PatternType;
  description: string;
  confidence: number;
  timeRange: {
    start: Date;
    end: Date;
  };
  data: Array<{
    timestamp: Date;
    value: number;
    contribution: number;
  }>;
  characteristics: PatternCharacteristics;
  significance: 'low' | 'medium' | 'high';
  actionable: boolean;
}

export type PatternType =
  | 'trend'
  | 'cycle'
  | 'seasonality'
  | 'level_shift'
  | 'spike'
  | 'dip'
  | 'gradual_change'
  | 'periodic_pattern'
  | 'correlation'
  | 'causation';

export interface PatternCharacteristics {
  duration: number; // in periods
  amplitude: number;
  frequency?: number;
  correlation?: number;
  strength: number; // 0-1
  stability: number; // 0-1
  predictability: number; // 0-1
}

// Feature Engineering Types
export interface FeatureSet {
  id: string;
  name: string;
  version: string;
  features: Feature[];
  createdAt: Date;
  updatedAt: Date;
  statistics?: FeatureStatistics;
}

export interface Feature {
  name: string;
  type: FeatureType;
  description?: string;
  transformation?: FeatureTransformation;
  importance?: number;
  correlation?: Record<string, number>;
  nullable: boolean;
  categorical?: {
    categories: string[];
    encoding: 'one_hot' | 'label' | 'target' | 'frequency';
  };
  numerical?: {
    scaling: 'standard' | 'minmax' | 'robust' | 'none';
    distribution: 'normal' | 'skewed' | 'uniform' | 'unknown';
  };
}

export type FeatureType =
  | 'numerical'
  | 'categorical'
  | 'boolean'
  | 'datetime'
  | 'text'
  | 'derived'
  | 'engineered';

export interface FeatureTransformation {
  method: string;
  parameters?: Record<string, any>;
  dependencies?: string[];
  code?: string;
}

export interface FeatureStatistics {
  count: number;
  missing: number;
  unique: number;
  mean?: number;
  median?: number;
  mode?: string | number;
  standardDeviation?: number;
  min?: number;
  max?: number;
  percentiles?: Record<string, number>;
  outliers?: number;
}

// Model Performance and Evaluation Types
export interface ModelPerformance {
  modelId: string;
  evaluatedAt: Date;
  dataset: {
    name: string;
    size: number;
    features: number;
  };
  metrics: PerformanceMetrics;
  confusionMatrix?: ConfusionMatrix;
  featureImportance: Record<string, number>;
  crossValidation?: CrossValidationResults;
  benchmarkComparison?: BenchmarkResults;
}

export interface PerformanceMetrics {
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1Score?: number;
  auc?: number;
  logLoss?: number;
  meanSquaredError?: number;
  meanAbsoluteError?: number;
  r2Score?: number;
  adjustedR2?: number;
  customMetrics?: Record<string, number>;
}

export interface ConfusionMatrix {
  truePositives: number;
  falsePositives: number;
  trueNegatives: number;
  falseNegatives: number;
  classes?: string[];
  matrix?: number[][];
}

export interface CrossValidationResults {
  folds: number;
  meanScore: number;
  standardDeviation: number;
  scores: number[];
  bestFold: number;
  worstFold: number;
}

export interface BenchmarkResults {
  baseline: {
    name: string;
    score: number;
  };
  competitors: Array<{
    name: string;
    score: number;
    improvement: number;
  }>;
  ranking: number;
  significanceTest?: {
    pValue: number;
    isSignificant: boolean;
  };
}

// Business Intelligence and Insights Types
export interface MLInsight {
  id: string;
  type: InsightType;
  title: string;
  description: string;
  confidence: number;
  severity: 'info' | 'warning' | 'critical';
  category: 'performance' | 'trend' | 'anomaly' | 'opportunity' | 'risk';
  generatedAt: Date;
  expiresAt?: Date;
  dataSource: string;
  evidence: Evidence[];
  recommendations: Recommendation[];
  impact: ImpactAssessment;
  metadata?: Record<string, any>;
}

export type InsightType =
  | 'predictive'
  | 'diagnostic'
  | 'prescriptive'
  | 'descriptive'
  | 'correlation_discovery'
  | 'trend_analysis'
  | 'anomaly_alert'
  | 'optimization_opportunity';

export interface Evidence {
  type: 'statistical' | 'visual' | 'comparative' | 'historical';
  description: string;
  data?: any;
  significance: number;
  supportingMetrics?: Record<string, number>;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  effort: 'low' | 'medium' | 'high';
  impact: 'low' | 'medium' | 'high';
  timeframe: string;
  actions: string[];
  expectedOutcome?: string;
  riskFactors?: string[];
}

export interface ImpactAssessment {
  businessValue: 'low' | 'medium' | 'high';
  estimatedROI?: number;
  affectedMetrics: string[];
  stakeholders: string[];
  timeToValue?: number; // in days
  confidence: number;
}

// AutoML and Model Management Types
export interface AutoMLExperiment {
  id: string;
  name: string;
  objective: 'regression' | 'classification' | 'forecasting' | 'clustering';
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startedAt: Date;
  completedAt?: Date;
  dataset: DatasetInfo;
  configuration: AutoMLConfig;
  results?: AutoMLResults;
  bestModel?: MLModel;
  allModels: MLModel[];
}

export interface DatasetInfo {
  name: string;
  size: number;
  features: number;
  target: string;
  missingValues: number;
  duplicates: number;
  dataQualityScore: number;
  schema: Record<string, string>;
}

export interface AutoMLConfig {
  maxTime: number; // in minutes
  maxModels: number;
  optimization: 'accuracy' | 'speed' | 'interpretability' | 'balanced';
  algorithms: ModelType[];
  preprocessing: {
    handleMissing: boolean;
    featureSelection: boolean;
    featureEngineering: boolean;
    outlierDetection: boolean;
  };
  validation: ValidationConfig;
}

export interface AutoMLResults {
  bestScore: number;
  bestModel: string;
  leaderboard: Array<{
    rank: number;
    modelId: string;
    score: number;
    trainingTime: number;
  }>;
  insights: string[];
  recommendations: string[];
}

// Real-time ML Types
export interface MLStream {
  id: string;
  name: string;
  modelId: string;
  status: 'active' | 'paused' | 'stopped';
  throughput: number; // predictions per second
  latency: number; // average response time in ms
  accuracy: number; // real-time accuracy
  configuration: StreamConfig;
  metrics: StreamMetrics;
  alerts?: StreamAlert[];
}

export interface StreamConfig {
  batchSize: number;
  maxLatency: number; // max acceptable latency in ms
  scalingPolicy: 'fixed' | 'auto';
  retryPolicy: {
    maxRetries: number;
    backoffMs: number;
  };
  fallbackModel?: string;
}

export interface StreamMetrics {
  predictionsCount: number;
  errorRate: number;
  averageLatency: number;
  throughput: number;
  memoryUsage: number;
  cpuUsage: number;
  lastUpdated: Date;
}

export interface StreamAlert {
  id: string;
  type: 'latency' | 'accuracy' | 'error_rate' | 'throughput';
  severity: 'warning' | 'critical';
  threshold: number;
  currentValue: number;
  triggeredAt: Date;
  resolved: boolean;
  resolvedAt?: Date;
}

// Data Drift and Model Monitoring Types
export interface DataDriftReport {
  id: string;
  modelId: string;
  generatedAt: Date;
  period: {
    start: Date;
    end: Date;
  };
  overallDriftScore: number;
  isDriftDetected: boolean;
  featureDrift: Record<string, FeatureDriftInfo>;
  targetDrift?: TargetDriftInfo;
  recommendations: string[];
  actionRequired: boolean;
}

export interface FeatureDriftInfo {
  feature: string;
  driftScore: number;
  isDrifted: boolean;
  method: 'psi' | 'ks_test' | 'js_divergence' | 'wasserstein';
  pValue?: number;
  threshold: number;
  baseline: DistributionInfo;
  current: DistributionInfo;
}

export interface TargetDriftInfo {
  driftScore: number;
  isDrifted: boolean;
  baseline: {
    mean: number;
    variance: number;
    distribution: Record<string, number>;
  };
  current: {
    mean: number;
    variance: number;
    distribution: Record<string, number>;
  };
}

export interface DistributionInfo {
  mean: number;
  variance: number;
  skewness: number;
  kurtosis: number;
  percentiles: Record<string, number>;
  histogram: Array<{
    bin: string;
    count: number;
    frequency: number;
  }>;
}

// Component and Hook Types for React Integration
export interface MLAnalyticsContextValue {
  // Models
  models: MLModel[];
  currentModel: MLModel | null;
  isModelLoading: boolean;

  // Predictions
  predictions: Prediction[];
  forecasts: ForecastResult[];

  // Insights
  insights: MLInsight[];
  anomalies: AnomalyDetection[];
  patterns: PatternRecognition[];

  // Performance
  performance: ModelPerformance[];
  driftReports: DataDriftReport[];

  // Loading states
  isLoading: boolean;
  error: string | null;

  // Actions
  actions: {
    // Model management
    trainModel: (config: TrainingConfig) => Promise<string>;
    deployModel: (modelId: string) => Promise<void>;
    evaluateModel: (modelId: string) => Promise<ModelPerformance>;

    // Predictions
    predict: (modelId: string, input: Record<string, any>) => Promise<Prediction>;
    forecast: (modelId: string, horizon: number) => Promise<ForecastResult>;

    // AutoML
    startAutoMLExperiment: (config: AutoMLConfig) => Promise<string>;
    getExperimentStatus: (experimentId: string) => Promise<AutoMLExperiment>;

    // Monitoring
    detectDataDrift: (modelId: string) => Promise<DataDriftReport>;
    generateInsights: (dataSource: string) => Promise<MLInsight[]>;

    // Utilities
    refresh: () => Promise<void>;
    reset: () => void;
  };
}

export interface MLModelCardProps {
  model: MLModel;
  onSelect?: (model: MLModel) => void;
  onTrain?: (model: MLModel) => void;
  onDeploy?: (model: MLModel) => void;
  onEvaluate?: (model: MLModel) => void;
  showActions?: boolean;
  className?: string;
}

export interface PredictionChartProps {
  predictions: Prediction[];
  forecasts?: ForecastResult[];
  height?: number;
  showConfidenceBands?: boolean;
  className?: string;
}

export interface InsightsPanelProps {
  insights: MLInsight[];
  onInsightClick?: (insight: MLInsight) => void;
  onDismiss?: (insightId: string) => void;
  filterBy?: {
    category?: string;
    severity?: string;
    type?: string;
  };
  maxHeight?: string;
  className?: string;
}

export interface ModelPerformanceChartProps {
  performance: ModelPerformance[];
  metric: keyof PerformanceMetrics;
  chartType?: 'line' | 'bar';
  className?: string;
}

// API Response Types
export interface MLApiResponse<T = any> {
  data: T;
  pagination?: {
    page: number;
    size: number;
    total: number;
  };
  metadata?: {
    executionTime: number;
    modelVersion: string;
    cacheHit: boolean;
    computeResources?: {
      cpu: number;
      memory: number;
      gpu?: number;
    };
  };
}

export interface TrainingJobResponse {
  jobId: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  estimatedCompletion?: Date;
  logs?: string[];
  metrics?: Record<string, number>;
}

// Configuration Types
export interface MLAnalyticsConfig {
  apiEndpoint: string;
  mlServiceEndpoint: string;
  autoMLEndpoint?: string;
  maxConcurrentJobs: number;
  defaultTimeout: number;
  enableGPU: boolean;
  enableDistributedTraining: boolean;
  caching: {
    enabled: boolean;
    ttl: number;
    maxSize: number;
  };
  monitoring: {
    enableDriftDetection: boolean;
    driftCheckInterval: number;
    performanceThreshold: number;
  };
}
