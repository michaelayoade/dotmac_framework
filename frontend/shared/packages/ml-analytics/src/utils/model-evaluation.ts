import { mean, standardDeviation } from 'simple-statistics';

export interface ModelMetrics {
  mae: number; // Mean Absolute Error
  mse: number; // Mean Squared Error
  rmse: number; // Root Mean Squared Error
  mape: number; // Mean Absolute Percentage Error
  r2: number; // R-squared
  accuracy: number; // Custom accuracy metric
}

export interface ClassificationMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  confusionMatrix: number[][];
  auc?: number;
}

export interface CrossValidationResult {
  meanScore: number;
  stdScore: number;
  scores: number[];
  bestFold: number;
  worstFold: number;
}

// Regression metrics
export function calculateRegressionMetrics(actual: number[], predicted: number[]): ModelMetrics {
  if (actual.length !== predicted.length) {
    throw new Error('Actual and predicted arrays must have the same length');
  }

  const n = actual.length;
  if (n === 0) {
    return { mae: 0, mse: 0, rmse: 0, mape: 0, r2: 0, accuracy: 0 };
  }

  // Mean Absolute Error
  const mae = mean(actual.map((a, i) => Math.abs(a - predicted[i])));

  // Mean Squared Error
  const mse = mean(actual.map((a, i) => Math.pow(a - predicted[i], 2)));

  // Root Mean Squared Error
  const rmse = Math.sqrt(mse);

  // Mean Absolute Percentage Error
  const mape = mean(
    actual
      .filter((a) => a !== 0) // Avoid division by zero
      .map((a, i) => Math.abs((a - predicted[actual.indexOf(a)]) / a) * 100)
  );

  // R-squared
  const actualMean = mean(actual);
  const totalSumSquares = actual.reduce((sum, a) => sum + Math.pow(a - actualMean, 2), 0);
  const residualSumSquares = actual.reduce((sum, a, i) => sum + Math.pow(a - predicted[i], 2), 0);
  const r2 = totalSumSquares !== 0 ? 1 - residualSumSquares / totalSumSquares : 0;

  // Custom accuracy (percentage of predictions within acceptable range)
  const tolerance = standardDeviation(actual) * 0.1; // 10% of standard deviation
  const withinTolerance = actual.filter((a, i) => Math.abs(a - predicted[i]) <= tolerance).length;
  const accuracy = withinTolerance / n;

  return { mae, mse, rmse, mape, r2, accuracy };
}

// Classification metrics
export function calculateClassificationMetrics(
  actualLabels: number[],
  predictedLabels: number[],
  numClasses?: number
): ClassificationMetrics {
  if (actualLabels.length !== predictedLabels.length) {
    throw new Error('Actual and predicted arrays must have the same length');
  }

  const n = actualLabels.length;
  if (n === 0) {
    return {
      accuracy: 0,
      precision: 0,
      recall: 0,
      f1Score: 0,
      confusionMatrix: [],
    };
  }

  // Determine number of classes
  const classes = numClasses || Math.max(...actualLabels, ...predictedLabels) + 1;

  // Create confusion matrix
  const confusionMatrix = Array(classes)
    .fill(null)
    .map(() => Array(classes).fill(0));

  actualLabels.forEach((actual, i) => {
    const predicted = predictedLabels[i];
    if (actual < classes && predicted < classes) {
      confusionMatrix[actual][predicted]++;
    }
  });

  // Calculate accuracy
  const correct = actualLabels.filter((actual, i) => actual === predictedLabels[i]).length;
  const accuracy = correct / n;

  // Calculate precision, recall, and F1-score (macro-averaged)
  let totalPrecision = 0;
  let totalRecall = 0;
  let validClasses = 0;

  for (let classIdx = 0; classIdx < classes; classIdx++) {
    const truePositive = confusionMatrix[classIdx][classIdx];
    const falsePositive = confusionMatrix.reduce(
      (sum, row, i) => (i !== classIdx ? sum + row[classIdx] : sum),
      0
    );
    const falseNegative = confusionMatrix[classIdx].reduce(
      (sum, val, j) => (j !== classIdx ? sum + val : sum),
      0
    );

    if (truePositive + falsePositive > 0) {
      const precision = truePositive / (truePositive + falsePositive);
      totalPrecision += precision;
      validClasses++;
    }

    if (truePositive + falseNegative > 0) {
      const recall = truePositive / (truePositive + falseNegative);
      totalRecall += recall;
    }
  }

  const avgPrecision = validClasses > 0 ? totalPrecision / validClasses : 0;
  const avgRecall = validClasses > 0 ? totalRecall / validClasses : 0;
  const f1Score =
    avgPrecision + avgRecall > 0
      ? (2 * (avgPrecision * avgRecall)) / (avgPrecision + avgRecall)
      : 0;

  return {
    accuracy,
    precision: avgPrecision,
    recall: avgRecall,
    f1Score,
    confusionMatrix,
  };
}

// Cross-validation
export function performCrossValidation(
  features: number[][],
  targets: number[],
  modelTrainer: (trainFeatures: number[][], trainTargets: number[]) => any,
  modelPredictor: (model: any, testFeatures: number[][]) => number[],
  folds: number = 5,
  metric: 'mae' | 'mse' | 'accuracy' = 'mae'
): CrossValidationResult {
  if (features.length !== targets.length) {
    throw new Error('Features and targets must have the same length');
  }

  const n = features.length;
  const foldSize = Math.floor(n / folds);
  const scores: number[] = [];

  for (let fold = 0; fold < folds; fold++) {
    const testStart = fold * foldSize;
    const testEnd = fold === folds - 1 ? n : testStart + foldSize;

    // Split data
    const testFeatures = features.slice(testStart, testEnd);
    const testTargets = targets.slice(testStart, testEnd);

    const trainFeatures = [...features.slice(0, testStart), ...features.slice(testEnd)];
    const trainTargets = [...targets.slice(0, testStart), ...targets.slice(testEnd)];

    // Train model
    const model = modelTrainer(trainFeatures, trainTargets);

    // Make predictions
    const predictions = modelPredictor(model, testFeatures);

    // Calculate score
    let score: number;
    switch (metric) {
      case 'mae':
        score = mean(testTargets.map((actual, i) => Math.abs(actual - predictions[i])));
        break;
      case 'mse':
        score = mean(testTargets.map((actual, i) => Math.pow(actual - predictions[i], 2)));
        break;
      case 'accuracy':
        score =
          testTargets.filter((actual, i) => actual === Math.round(predictions[i])).length /
          testTargets.length;
        break;
      default:
        score = mean(testTargets.map((actual, i) => Math.abs(actual - predictions[i])));
    }

    scores.push(score);
  }

  const meanScore = mean(scores);
  const stdScore = standardDeviation(scores);
  const bestFold = scores.indexOf(Math.min(...scores));
  const worstFold = scores.indexOf(Math.max(...scores));

  return {
    meanScore,
    stdScore,
    scores,
    bestFold,
    worstFold,
  };
}

// Model comparison
export function compareModels(
  results: Array<{
    name: string;
    predictions: number[];
    actual: number[];
  }>
): Array<{
  name: string;
  metrics: ModelMetrics;
  rank: number;
}> {
  const modelResults = results.map((result) => ({
    name: result.name,
    metrics: calculateRegressionMetrics(result.actual, result.predictions),
  }));

  // Rank by R-squared (higher is better)
  const ranked = modelResults
    .map((result, index) => ({ ...result, originalIndex: index }))
    .sort((a, b) => b.metrics.r2 - a.metrics.r2)
    .map((result, index) => ({
      name: result.name,
      metrics: result.metrics,
      rank: index + 1,
    }));

  return ranked;
}

// Learning curve analysis
export function generateLearningCurve(
  features: number[][],
  targets: number[],
  modelTrainer: (trainFeatures: number[][], trainTargets: number[]) => any,
  modelPredictor: (model: any, testFeatures: number[][]) => number[],
  trainSizes: number[] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
): Array<{
  trainSize: number;
  trainScore: number;
  validationScore: number;
}> {
  const n = features.length;
  const testSize = Math.floor(n * 0.2); // 20% for testing
  const maxTrainSize = n - testSize;

  // Split off test set
  const testFeatures = features.slice(-testSize);
  const testTargets = targets.slice(-testSize);
  const availableFeatures = features.slice(0, -testSize);
  const availableTargets = targets.slice(0, -testSize);

  return trainSizes.map((ratio) => {
    const currentTrainSize = Math.floor(maxTrainSize * ratio);

    const trainFeatures = availableFeatures.slice(0, currentTrainSize);
    const trainTargets = availableTargets.slice(0, currentTrainSize);

    // Train model
    const model = modelTrainer(trainFeatures, trainTargets);

    // Calculate training score
    const trainPredictions = modelPredictor(model, trainFeatures);
    const trainMetrics = calculateRegressionMetrics(trainTargets, trainPredictions);

    // Calculate validation score
    const validationPredictions = modelPredictor(model, testFeatures);
    const validationMetrics = calculateRegressionMetrics(testTargets, validationPredictions);

    return {
      trainSize: currentTrainSize,
      trainScore: trainMetrics.r2,
      validationScore: validationMetrics.r2,
    };
  });
}

// Feature importance (simplified permutation importance)
export function calculateFeatureImportance(
  features: number[][],
  targets: number[],
  featureNames: string[],
  modelTrainer: (trainFeatures: number[][], trainTargets: number[]) => any,
  modelPredictor: (model: any, testFeatures: number[][]) => number[],
  metric: 'mae' | 'mse' = 'mae'
): Array<{
  feature: string;
  importance: number;
  rank: number;
}> {
  // Train baseline model
  const baselineModel = modelTrainer(features, targets);
  const baselinePredictions = modelPredictor(baselineModel, features);
  const baselineMetrics = calculateRegressionMetrics(targets, baselinePredictions);
  const baselineScore = metric === 'mae' ? baselineMetrics.mae : baselineMetrics.mse;

  const importances = featureNames.map((featureName, featureIndex) => {
    // Create permuted features
    const permutedFeatures = features.map((row) => [...row]);

    // Shuffle the specific feature column
    const featureValues = permutedFeatures.map((row) => row[featureIndex]);
    const shuffledValues = shuffleArray([...featureValues]);

    permutedFeatures.forEach((row, i) => {
      row[featureIndex] = shuffledValues[i];
    });

    // Train model with permuted feature
    const permutedModel = modelTrainer(permutedFeatures, targets);
    const permutedPredictions = modelPredictor(permutedModel, permutedFeatures);
    const permutedMetrics = calculateRegressionMetrics(targets, permutedPredictions);
    const permutedScore = metric === 'mae' ? permutedMetrics.mae : permutedMetrics.mse;

    // Importance is the increase in error when feature is shuffled
    const importance = permutedScore - baselineScore;

    return {
      feature: featureName,
      importance,
    };
  });

  // Sort by importance and add ranks
  return importances
    .sort((a, b) => b.importance - a.importance)
    .map((item, index) => ({
      ...item,
      rank: index + 1,
    }));
}

// Residual analysis
export function analyzeResiduals(
  actual: number[],
  predicted: number[]
): {
  residuals: number[];
  meanResidual: number;
  stdResidual: number;
  isNormallyDistributed: boolean;
  hasHomoscedasticity: boolean;
  outlierIndices: number[];
} {
  const residuals = actual.map((a, i) => a - predicted[i]);
  const meanResidual = mean(residuals);
  const stdResidual = standardDeviation(residuals);

  // Simple normality test (Shapiro-Wilk approximation)
  const sortedResiduals = [...residuals].sort((a, b) => a - b);
  const n = residuals.length;

  // Very simplified normality check
  const expectedNormal = sortedResiduals.map((_, i) => {
    const p = (i + 0.5) / n;
    // Approximate inverse normal CDF
    return Math.sqrt(2) * Math.sign(p - 0.5) * Math.sqrt(-Math.log(Math.min(p, 1 - p)));
  });

  const normalityCorrelation = calculateCorrelation(sortedResiduals, expectedNormal);
  const isNormallyDistributed = normalityCorrelation > 0.95;

  // Homoscedasticity check (constant variance)
  const firstHalfVar = standardDeviation(residuals.slice(0, Math.floor(n / 2)));
  const secondHalfVar = standardDeviation(residuals.slice(Math.floor(n / 2)));
  const varianceRatio =
    Math.max(firstHalfVar, secondHalfVar) / Math.min(firstHalfVar, secondHalfVar);
  const hasHomoscedasticity = varianceRatio < 2.0; // Reasonable threshold

  // Identify outliers (residuals > 2 standard deviations)
  const outlierIndices: number[] = [];
  residuals.forEach((residual, index) => {
    if (Math.abs(residual) > 2 * stdResidual) {
      outlierIndices.push(index);
    }
  });

  return {
    residuals,
    meanResidual,
    stdResidual,
    isNormallyDistributed,
    hasHomoscedasticity,
    outlierIndices,
  };
}

// Helper functions
function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
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
