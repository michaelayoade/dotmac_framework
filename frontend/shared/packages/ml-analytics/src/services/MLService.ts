import type {
  MLModel,
  Prediction,
  ForecastResult,
  MLInsight,
  AnomalyDetection,
  PatternRecognition,
  ModelPerformance,
  DataDriftReport,
  AutoMLExperiment,
  TrainingConfig,
  AutoMLConfig,
  MLApiResponse,
  TrainingJobResponse,
  MLAnalyticsConfig,
} from '../types';

class MLAnalyticsService {
  private config: MLAnalyticsConfig;
  private cache: Map<string, { data: any; timestamp: number; ttl: number }> = new Map();

  constructor(config: Partial<MLAnalyticsConfig> = {}) {
    this.config = {
      apiEndpoint: '/api/ml',
      mlServiceEndpoint: '/api/ml-service',
      autoMLEndpoint: '/api/automl',
      maxConcurrentJobs: 5,
      defaultTimeout: 30000,
      enableGPU: false,
      enableDistributedTraining: false,
      caching: {
        enabled: true,
        ttl: 300000, // 5 minutes
        maxSize: 1000,
      },
      monitoring: {
        enableDriftDetection: true,
        driftCheckInterval: 86400000, // 24 hours
        performanceThreshold: 0.8,
      },
      ...config,
    };
  }

  // Cache management
  private getCacheKey(method: string, params: any): string {
    return `${method}:${JSON.stringify(params)}`;
  }

  private getFromCache<T>(key: string): T | null {
    if (!this.config.caching.enabled) return null;

    const cached = this.cache.get(key);
    if (!cached) return null;

    if (Date.now() - cached.timestamp > cached.ttl) {
      this.cache.delete(key);
      return null;
    }

    return cached.data as T;
  }

  private setCache(key: string, data: any, ttl?: number): void {
    if (!this.config.caching.enabled) return;

    // Clean cache if it's too large
    if (this.cache.size >= this.config.caching.maxSize) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttl || this.config.caching.ttl,
    });
  }

  // HTTP utilities
  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.config.apiEndpoint}${endpoint}`;

    const response = await fetch(url, {
      timeout: this.config.defaultTimeout,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`ML API Error: ${response.status} ${response.statusText}`);
    }

    const result: MLApiResponse<T> = await response.json();
    return result.data;
  }

  // Model Management
  async getModels(): Promise<MLModel[]> {
    const cacheKey = this.getCacheKey('getModels', {});
    const cached = this.getFromCache<MLModel[]>(cacheKey);
    if (cached) return cached;

    const models = await this.makeRequest<MLModel[]>('/models');
    this.setCache(cacheKey, models);
    return models;
  }

  async getModel(modelId: string): Promise<MLModel> {
    const cacheKey = this.getCacheKey('getModel', { modelId });
    const cached = this.getFromCache<MLModel>(cacheKey);
    if (cached) return cached;

    const model = await this.makeRequest<MLModel>(`/models/${modelId}`);
    this.setCache(cacheKey, model, 60000); // Cache for 1 minute
    return model;
  }

  async createModel(modelConfig: {
    name: string;
    type: MLModel['type'];
    description?: string;
    parameters: MLModel['parameters'];
  }): Promise<string> {
    const response = await this.makeRequest<{ id: string }>('/models', {
      method: 'POST',
      body: JSON.stringify({
        ...modelConfig,
        createdAt: new Date().toISOString(),
        status: 'training',
        version: '1.0.0',
      }),
    });

    // Invalidate models cache
    this.cache.forEach((_, key) => {
      if (key.startsWith('getModels:')) {
        this.cache.delete(key);
      }
    });

    return response.id;
  }

  async updateModel(modelId: string, updates: Partial<MLModel>): Promise<void> {
    await this.makeRequest(`/models/${modelId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });

    // Invalidate related caches
    this.cache.forEach((_, key) => {
      if (key.includes('getModel') && key.includes(modelId)) {
        this.cache.delete(key);
      }
    });
  }

  async deleteModel(modelId: string): Promise<void> {
    await this.makeRequest(`/models/${modelId}`, {
      method: 'DELETE',
    });

    // Invalidate caches
    this.cache.forEach((_, key) => {
      if (key.includes(modelId)) {
        this.cache.delete(key);
      }
    });
  }

  // Model Training
  async trainModel(modelId: string, config: TrainingConfig): Promise<TrainingJobResponse> {
    return await this.makeRequest<TrainingJobResponse>(`/models/${modelId}/train`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async getTrainingStatus(jobId: string): Promise<TrainingJobResponse> {
    return await this.makeRequest<TrainingJobResponse>(`/training/jobs/${jobId}`);
  }

  async deployModel(
    modelId: string,
    config: {
      environment: 'staging' | 'production';
      replicas?: number;
      resources?: {
        cpu: string;
        memory: string;
        gpu?: string;
      };
    }
  ): Promise<void> {
    await this.makeRequest(`/models/${modelId}/deploy`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  // Predictions
  async predict(
    modelId: string,
    input: Record<string, any>,
    options: {
      explainPrediction?: boolean;
      confidence?: boolean;
      timeout?: number;
    } = {}
  ): Promise<Prediction> {
    const prediction = await this.makeRequest<Prediction>(`/models/${modelId}/predict`, {
      method: 'POST',
      body: JSON.stringify({ input, options }),
      timeout: options.timeout || this.config.defaultTimeout,
    });

    return {
      ...prediction,
      timestamp: new Date(prediction.timestamp),
    };
  }

  async batchPredict(
    modelId: string,
    inputs: Record<string, any>[],
    options: {
      batchSize?: number;
      parallelism?: number;
    } = {}
  ): Promise<Prediction[]> {
    const predictions = await this.makeRequest<Prediction[]>(`/models/${modelId}/batch-predict`, {
      method: 'POST',
      body: JSON.stringify({ inputs, options }),
    });

    return predictions.map((p) => ({
      ...p,
      timestamp: new Date(p.timestamp),
    }));
  }

  // Forecasting
  async forecast(
    modelId: string,
    horizon: number,
    options: {
      granularity?: ForecastResult['granularity'];
      includeBounds?: boolean;
      seasonalityDetection?: boolean;
    } = {}
  ): Promise<ForecastResult> {
    const cacheKey = this.getCacheKey('forecast', { modelId, horizon, options });
    const cached = this.getFromCache<ForecastResult>(cacheKey);
    if (cached) return cached;

    const forecast = await this.makeRequest<ForecastResult>(`/models/${modelId}/forecast`, {
      method: 'POST',
      body: JSON.stringify({ horizon, options }),
    });

    const result: ForecastResult = {
      ...forecast,
      generatedAt: new Date(forecast.generatedAt),
      predictions: forecast.predictions.map((p) => ({
        ...p,
        timestamp: new Date(p.timestamp),
      })),
    };

    this.setCache(cacheKey, result, 600000); // Cache for 10 minutes
    return result;
  }

  async multiSeriesForecast(
    modelId: string,
    series: Array<{
      name: string;
      data: Array<{ timestamp: Date; value: number }>;
    }>,
    horizon: number
  ): Promise<Record<string, ForecastResult>> {
    const forecasts = await this.makeRequest<Record<string, ForecastResult>>(
      `/models/${modelId}/multi-forecast`,
      {
        method: 'POST',
        body: JSON.stringify({ series, horizon }),
      }
    );

    // Convert timestamps
    Object.keys(forecasts).forEach((seriesName) => {
      forecasts[seriesName] = {
        ...forecasts[seriesName],
        generatedAt: new Date(forecasts[seriesName].generatedAt),
        predictions: forecasts[seriesName].predictions.map((p) => ({
          ...p,
          timestamp: new Date(p.timestamp),
        })),
      };
    });

    return forecasts;
  }

  // Anomaly Detection
  async detectAnomalies(
    data: Array<{ timestamp: Date; value: number; [key: string]: any }>,
    options: {
      method?: 'statistical' | 'isolation_forest' | 'autoencoder' | 'lstm';
      sensitivity?: 'low' | 'medium' | 'high';
      seasonality?: boolean;
    } = {}
  ): Promise<AnomalyDetection[]> {
    const anomalies = await this.makeRequest<AnomalyDetection[]>('/anomalies/detect', {
      method: 'POST',
      body: JSON.stringify({ data, options }),
    });

    return anomalies.map((a) => ({
      ...a,
      timestamp: new Date(a.timestamp),
    }));
  }

  async detectRealTimeAnomalies(
    modelId: string,
    dataPoint: Record<string, any>
  ): Promise<AnomalyDetection | null> {
    const result = await this.makeRequest<AnomalyDetection | null>(
      `/models/${modelId}/anomaly-check`,
      {
        method: 'POST',
        body: JSON.stringify({ dataPoint }),
      }
    );

    return result
      ? {
          ...result,
          timestamp: new Date(result.timestamp),
        }
      : null;
  }

  // Pattern Recognition
  async recognizePatterns(
    data: Array<{ timestamp: Date; value: number }>,
    options: {
      patternTypes?: PatternRecognition['type'][];
      minConfidence?: number;
      timeWindow?: number;
    } = {}
  ): Promise<PatternRecognition[]> {
    const patterns = await this.makeRequest<PatternRecognition[]>('/patterns/recognize', {
      method: 'POST',
      body: JSON.stringify({ data, options }),
    });

    return patterns.map((p) => ({
      ...p,
      timeRange: {
        start: new Date(p.timeRange.start),
        end: new Date(p.timeRange.end),
      },
      data: p.data.map((d) => ({
        ...d,
        timestamp: new Date(d.timestamp),
      })),
    }));
  }

  async findCorrelations(
    datasets: Record<string, Array<{ timestamp: Date; value: number }>>,
    options: {
      method?: 'pearson' | 'spearman' | 'kendall';
      minCorrelation?: number;
      lagAnalysis?: boolean;
    } = {}
  ): Promise<
    Array<{
      series1: string;
      series2: string;
      correlation: number;
      significance: number;
      lag?: number;
    }>
  > {
    return await this.makeRequest('/patterns/correlations', {
      method: 'POST',
      body: JSON.stringify({ datasets, options }),
    });
  }

  // Model Performance and Evaluation
  async evaluateModel(
    modelId: string,
    testData?: any,
    metrics?: string[]
  ): Promise<ModelPerformance> {
    const performance = await this.makeRequest<ModelPerformance>(`/models/${modelId}/evaluate`, {
      method: 'POST',
      body: JSON.stringify({ testData, metrics }),
    });

    return {
      ...performance,
      evaluatedAt: new Date(performance.evaluatedAt),
    };
  }

  async getModelPerformanceHistory(modelId: string): Promise<ModelPerformance[]> {
    const history = await this.makeRequest<ModelPerformance[]>(
      `/models/${modelId}/performance-history`
    );

    return history.map((p) => ({
      ...p,
      evaluatedAt: new Date(p.evaluatedAt),
    }));
  }

  async compareModels(modelIds: string[]): Promise<{
    models: MLModel[];
    comparison: Record<string, ModelPerformance>;
    recommendation: {
      bestModel: string;
      reason: string;
      confidenceLevel: number;
    };
  }> {
    return await this.makeRequest('/models/compare', {
      method: 'POST',
      body: JSON.stringify({ modelIds }),
    });
  }

  // AutoML
  async startAutoMLExperiment(config: AutoMLConfig): Promise<string> {
    const response = await this.makeRequest<{ experimentId: string }>('/automl/experiments', {
      method: 'POST',
      body: JSON.stringify(config),
    });

    return response.experimentId;
  }

  async getAutoMLExperiment(experimentId: string): Promise<AutoMLExperiment> {
    const experiment = await this.makeRequest<AutoMLExperiment>(
      `/automl/experiments/${experimentId}`
    );

    return {
      ...experiment,
      startedAt: new Date(experiment.startedAt),
      completedAt: experiment.completedAt ? new Date(experiment.completedAt) : undefined,
    };
  }

  async stopAutoMLExperiment(experimentId: string): Promise<void> {
    await this.makeRequest(`/automl/experiments/${experimentId}/stop`, {
      method: 'POST',
    });
  }

  // Data Drift Detection
  async detectDataDrift(
    modelId: string,
    referenceData: any[],
    currentData: any[],
    options: {
      features?: string[];
      method?: 'psi' | 'ks_test' | 'js_divergence';
      threshold?: number;
    } = {}
  ): Promise<DataDriftReport> {
    const report = await this.makeRequest<DataDriftReport>(`/models/${modelId}/drift-detection`, {
      method: 'POST',
      body: JSON.stringify({ referenceData, currentData, options }),
    });

    return {
      ...report,
      generatedAt: new Date(report.generatedAt),
      period: {
        start: new Date(report.period.start),
        end: new Date(report.period.end),
      },
    };
  }

  async getDataDriftReports(modelId: string): Promise<DataDriftReport[]> {
    const reports = await this.makeRequest<DataDriftReport[]>(`/models/${modelId}/drift-reports`);

    return reports.map((r) => ({
      ...r,
      generatedAt: new Date(r.generatedAt),
      period: {
        start: new Date(r.period.start),
        end: new Date(r.period.end),
      },
    }));
  }

  // ML-Powered Insights
  async generateInsights(
    dataSource: string,
    options: {
      insightTypes?: MLInsight['type'][];
      lookbackDays?: number;
      minConfidence?: number;
    } = {}
  ): Promise<MLInsight[]> {
    const insights = await this.makeRequest<MLInsight[]>('/insights/generate', {
      method: 'POST',
      body: JSON.stringify({ dataSource, options }),
    });

    return insights.map((insight) => ({
      ...insight,
      generatedAt: new Date(insight.generatedAt),
      expiresAt: insight.expiresAt ? new Date(insight.expiresAt) : undefined,
    }));
  }

  async getInsights(filters?: {
    category?: string;
    severity?: string;
    type?: string;
    isActive?: boolean;
  }): Promise<MLInsight[]> {
    const cacheKey = this.getCacheKey('getInsights', filters || {});
    const cached = this.getFromCache<MLInsight[]>(cacheKey);
    if (cached) return cached;

    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined) {
          params.append(key, String(value));
        }
      });
    }

    const insights = await this.makeRequest<MLInsight[]>(`/insights?${params}`);

    const result = insights.map((insight) => ({
      ...insight,
      generatedAt: new Date(insight.generatedAt),
      expiresAt: insight.expiresAt ? new Date(insight.expiresAt) : undefined,
    }));

    this.setCache(cacheKey, result, 120000); // Cache for 2 minutes
    return result;
  }

  async dismissInsight(insightId: string): Promise<void> {
    await this.makeRequest(`/insights/${insightId}/dismiss`, {
      method: 'POST',
    });

    // Invalidate insights cache
    this.cache.forEach((_, key) => {
      if (key.startsWith('getInsights:')) {
        this.cache.delete(key);
      }
    });
  }

  // Feature Engineering
  async generateFeatures(
    data: any[],
    config: {
      targetColumn?: string;
      categoricalColumns?: string[];
      numericalColumns?: string[];
      dateColumns?: string[];
      transformations?: string[];
    }
  ): Promise<{
    features: any[];
    featureInfo: Array<{
      name: string;
      type: string;
      importance?: number;
      description: string;
    }>;
    statistics: Record<string, any>;
  }> {
    return await this.makeRequest('/features/generate', {
      method: 'POST',
      body: JSON.stringify({ data, config }),
    });
  }

  async selectFeatures(
    data: any[],
    target: any[],
    method: 'correlation' | 'mutual_info' | 'chi2' | 'recursive' = 'correlation',
    maxFeatures?: number
  ): Promise<{
    selectedFeatures: string[];
    scores: Record<string, number>;
    methodology: string;
  }> {
    return await this.makeRequest('/features/select', {
      method: 'POST',
      body: JSON.stringify({ data, target, method, maxFeatures }),
    });
  }

  // Utility methods
  async getSystemHealth(): Promise<{
    status: 'healthy' | 'degraded' | 'down';
    services: Record<string, 'up' | 'down'>;
    metrics: {
      activeModels: number;
      runningJobs: number;
      queuedJobs: number;
      systemLoad: number;
      memoryUsage: number;
    };
    lastCheck: Date;
  }> {
    const health = await this.makeRequest<any>('/health');
    return {
      ...health,
      lastCheck: new Date(health.lastCheck),
    };
  }

  clearCache(): void {
    this.cache.clear();
  }

  getCacheStats(): {
    size: number;
    maxSize: number;
    hitRate: number;
    entries: number;
  } {
    return {
      size: this.cache.size,
      maxSize: this.config.caching.maxSize,
      hitRate: 0, // Would need to track hits/misses for real implementation
      entries: this.cache.size,
    };
  }
}

export default new MLAnalyticsService();
