import { mean, median, standardDeviation, mode } from 'simple-statistics';
import type { PatternRecognition, TimeSeriesData, DataPattern } from '../types';

export interface PatternRecognitionOptions {
  windowSize: number;
  sensitivity: number; // 0-1
  minPatternLength: number;
  maxPatternLength: number;
  includeSeasonality: boolean;
  includeTrends: boolean;
  includeRepeats: boolean;
}

export interface RecognizedPattern {
  id: string;
  type: 'trend' | 'seasonal' | 'cyclic' | 'spike' | 'dip' | 'outlier' | 'repeat';
  startIndex: number;
  endIndex: number;
  confidence: number;
  strength: number;
  description: string;
  parameters: Record<string, any>;
  frequency?: number;
  period?: number;
  amplitude?: number;
  phase?: number;
}

// Trend Pattern Recognition
export function detectTrendPatterns(
  data: number[],
  minLength: number = 5,
  threshold: number = 0.6
): RecognizedPattern[] {
  const patterns: RecognizedPattern[] = [];

  for (let start = 0; start <= data.length - minLength; start++) {
    for (let length = minLength; length <= Math.min(data.length - start, 50); length++) {
      const segment = data.slice(start, start + length);
      const trend = calculateTrendStrength(segment);

      if (Math.abs(trend) > threshold) {
        patterns.push({
          id: `trend-${start}-${start + length}`,
          type: 'trend',
          startIndex: start,
          endIndex: start + length - 1,
          confidence: Math.abs(trend),
          strength: Math.abs(trend),
          description: `${trend > 0 ? 'Upward' : 'Downward'} trend over ${length} data points`,
          parameters: {
            slope: trend,
            length,
            direction: trend > 0 ? 'up' : 'down'
          }
        });
      }
    }
  }

  // Remove overlapping patterns, keep strongest
  return removeOverlappingPatterns(patterns, 'strength');
}

// Seasonal Pattern Recognition
export function detectSeasonalPatterns(
  data: number[],
  testPeriods: number[] = [7, 12, 24, 30, 365]
): RecognizedPattern[] {
  const patterns: RecognizedPattern[] = [];

  for (const period of testPeriods) {
    if (data.length < period * 3) continue; // Need at least 3 complete cycles

    const seasonality = analyzeSeasonality(data, period);

    if (seasonality.strength > 0.4) {
      patterns.push({
        id: `seasonal-${period}`,
        type: 'seasonal',
        startIndex: 0,
        endIndex: data.length - 1,
        confidence: seasonality.strength,
        strength: seasonality.strength,
        description: `Seasonal pattern with period of ${period}`,
        parameters: {
          period,
          amplitude: seasonality.amplitude,
          phase: seasonality.phase,
          cycles: Math.floor(data.length / period)
        },
        period,
        amplitude: seasonality.amplitude,
        phase: seasonality.phase,
        frequency: 1 / period
      });
    }
  }

  return patterns.sort((a, b) => b.strength - a.strength);
}

// Spike and Dip Detection
export function detectSpikesAndDips(
  data: number[],
  sensitivity: number = 0.8
): RecognizedPattern[] {
  const patterns: RecognizedPattern[] = [];

  if (data.length < 3) return patterns;

  const dataMean = mean(data);
  const dataStd = standardDeviation(data);
  const threshold = dataMean + sensitivity * 3 * dataStd;
  const dipThreshold = dataMean - sensitivity * 3 * dataStd;

  for (let i = 1; i < data.length - 1; i++) {
    const current = data[i];
    const prev = data[i - 1];
    const next = data[i + 1];

    // Spike detection (local maximum significantly above normal)
    if (current > threshold && current > prev && current > next) {
      const strength = (current - dataMean) / dataStd;
      patterns.push({
        id: `spike-${i}`,
        type: 'spike',
        startIndex: i,
        endIndex: i,
        confidence: Math.min(strength / 3, 1),
        strength: strength,
        description: `Spike detected at position ${i}`,
        parameters: {
          value: current,
          expectedValue: dataMean,
          deviation: current - dataMean,
          magnitude: strength
        },
        amplitude: current - dataMean
      });
    }

    // Dip detection (local minimum significantly below normal)
    if (current < dipThreshold && current < prev && current < next) {
      const strength = Math.abs(current - dataMean) / dataStd;
      patterns.push({
        id: `dip-${i}`,
        type: 'dip',
        startIndex: i,
        endIndex: i,
        confidence: Math.min(strength / 3, 1),
        strength: strength,
        description: `Dip detected at position ${i}`,
        parameters: {
          value: current,
          expectedValue: dataMean,
          deviation: dataMean - current,
          magnitude: strength
        },
        amplitude: dataMean - current
      });
    }
  }

  return patterns;
}

// Repeating Pattern Detection
export function detectRepeatingPatterns(
  data: number[],
  minPatternLength: number = 3,
  maxPatternLength: number = 20,
  similarity: number = 0.8
): RecognizedPattern[] {
  const patterns: RecognizedPattern[] = [];

  for (let patternLength = minPatternLength; patternLength <= maxPatternLength; patternLength++) {
    for (let start = 0; start <= data.length - patternLength * 2; start++) {
      const pattern = data.slice(start, start + patternLength);
      const repeats = findPatternRepeats(data, pattern, start + patternLength, similarity);

      if (repeats.length >= 1) { // At least one repeat found
        const totalLength = repeats[repeats.length - 1].end - start;
        const frequency = (repeats.length + 1) / totalLength * patternLength;

        patterns.push({
          id: `repeat-${start}-${patternLength}`,
          type: 'repeat',
          startIndex: start,
          endIndex: repeats[repeats.length - 1].end,
          confidence: calculatePatternConfidence(data, pattern, repeats, similarity),
          strength: repeats.length / Math.floor(totalLength / patternLength),
          description: `Repeating pattern of length ${patternLength} found ${repeats.length + 1} times`,
          parameters: {
            patternLength,
            repeatCount: repeats.length + 1,
            repeats: repeats,
            averageSimilarity: repeats.reduce((sum, r) => sum + r.similarity, 0) / repeats.length
          },
          frequency,
          period: patternLength
        });
      }
    }
  }

  // Remove overlapping patterns, keep those with highest confidence
  return removeOverlappingPatterns(patterns, 'confidence').slice(0, 10); // Limit results
}

// Cyclic Pattern Detection
export function detectCyclicPatterns(
  data: number[],
  minCycleLength: number = 10,
  maxCycleLength: number = Math.floor(data.length / 3)
): RecognizedPattern[] {
  const patterns: RecognizedPattern[] = [];

  // Use autocorrelation to find cyclic patterns
  for (let lag = minCycleLength; lag <= maxCycleLength; lag++) {
    const correlation = calculateAutocorrelation(data, lag);

    if (correlation > 0.5) {
      const cycleCount = Math.floor(data.length / lag);

      patterns.push({
        id: `cycle-${lag}`,
        type: 'cyclic',
        startIndex: 0,
        endIndex: data.length - 1,
        confidence: correlation,
        strength: correlation,
        description: `Cyclic pattern with ${lag}-point cycles`,
        parameters: {
          cycleLength: lag,
          cycleCount,
          autocorrelation: correlation,
          phase: calculatePhase(data, lag)
        },
        period: lag,
        frequency: 1 / lag
      });
    }
  }

  return patterns.sort((a, b) => b.confidence - a.confidence);
}

// Comprehensive Pattern Recognition
export function recognizePatterns(
  data: TimeSeriesData[],
  options: Partial<PatternRecognitionOptions> = {}
): PatternRecognition {
  const config: PatternRecognitionOptions = {
    windowSize: Math.min(50, Math.floor(data.length / 4)),
    sensitivity: 0.8,
    minPatternLength: 3,
    maxPatternLength: Math.min(20, Math.floor(data.length / 10)),
    includeSeasonality: true,
    includeTrends: true,
    includeRepeats: true,
    ...options
  };

  const values = data.map(d => d.value);
  let allPatterns: RecognizedPattern[] = [];

  // Detect different types of patterns
  if (config.includeTrends) {
    const trendPatterns = detectTrendPatterns(values, config.minPatternLength, config.sensitivity);
    allPatterns.push(...trendPatterns);
  }

  if (config.includeSeasonality) {
    const seasonalPatterns = detectSeasonalPatterns(values);
    allPatterns.push(...seasonalPatterns);
  }

  const spikePatterns = detectSpikesAndDips(values, config.sensitivity);
  allPatterns.push(...spikePatterns);

  const cyclicPatterns = detectCyclicPatterns(values);
  allPatterns.push(...cyclicPatterns);

  if (config.includeRepeats) {
    const repeatingPatterns = detectRepeatingPatterns(
      values,
      config.minPatternLength,
      config.maxPatternLength,
      config.sensitivity
    );
    allPatterns.push(...repeatingPatterns);
  }

  // Convert to DataPattern format
  const patterns: DataPattern[] = allPatterns.map(p => ({
    id: p.id,
    type: p.type,
    startTime: data[p.startIndex]?.timestamp || new Date(),
    endTime: data[p.endIndex]?.timestamp || new Date(),
    confidence: p.confidence,
    strength: p.strength,
    description: p.description,
    metadata: {
      startIndex: p.startIndex,
      endIndex: p.endIndex,
      ...p.parameters,
      frequency: p.frequency,
      period: p.period,
      amplitude: p.amplitude,
      phase: p.phase
    }
  }));

  // Calculate summary statistics
  const patternTypes = patterns.reduce((counts, p) => {
    counts[p.type] = (counts[p.type] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const avgConfidence = patterns.length > 0
    ? patterns.reduce((sum, p) => sum + p.confidence, 0) / patterns.length
    : 0;

  const strongPatterns = patterns.filter(p => p.confidence > 0.7);

  return {
    id: `pattern-recognition-${Date.now()}`,
    modelId: 'pattern-recognizer-v1',
    analyzedAt: new Date(),
    dataPoints: data.length,
    patterns: patterns.sort((a, b) => b.confidence - a.confidence),
    summary: {
      totalPatterns: patterns.length,
      strongPatterns: strongPatterns.length,
      patternTypes,
      averageConfidence: avgConfidence,
      coveragePercent: calculateCoverage(patterns, data.length)
    },
    parameters: config
  };
}

// Helper functions
function calculateTrendStrength(data: number[]): number {
  if (data.length < 2) return 0;

  const n = data.length;
  const indices = Array.from({ length: n }, (_, i) => i);

  const meanX = mean(indices);
  const meanY = mean(data);

  let numerator = 0;
  let sumXSquared = 0;
  let sumYSquared = 0;

  for (let i = 0; i < n; i++) {
    const xDiff = indices[i] - meanX;
    const yDiff = data[i] - meanY;

    numerator += xDiff * yDiff;
    sumXSquared += xDiff * xDiff;
    sumYSquared += yDiff * yDiff;
  }

  const denominator = Math.sqrt(sumXSquared * sumYSquared);
  return denominator > 0 ? numerator / denominator : 0;
}

function analyzeSeasonality(data: number[], period: number) {
  const seasons = Math.floor(data.length / period);
  const seasonalComponents: number[] = Array(period).fill(0);
  const seasonalCounts: number[] = Array(period).fill(0);

  // Calculate seasonal averages
  for (let i = 0; i < data.length; i++) {
    const seasonIndex = i % period;
    seasonalComponents[seasonIndex] += data[i];
    seasonalCounts[seasonIndex]++;
  }

  for (let i = 0; i < period; i++) {
    if (seasonalCounts[i] > 0) {
      seasonalComponents[i] /= seasonalCounts[i];
    }
  }

  const overallMean = mean(data);
  let seasonalVariance = 0;
  let totalVariance = 0;

  for (let i = 0; i < data.length; i++) {
    const seasonIndex = i % period;
    seasonalVariance += Math.pow(seasonalComponents[seasonIndex] - overallMean, 2);
    totalVariance += Math.pow(data[i] - overallMean, 2);
  }

  const strength = totalVariance > 0 ? seasonalVariance / totalVariance : 0;
  const amplitude = Math.max(...seasonalComponents) - Math.min(...seasonalComponents);
  const phase = seasonalComponents.indexOf(Math.max(...seasonalComponents));

  return { strength, amplitude, phase };
}

function findPatternRepeats(
  data: number[],
  pattern: number[],
  startFrom: number,
  similarity: number
): Array<{ start: number; end: number; similarity: number }> {
  const repeats: Array<{ start: number; end: number; similarity: number }> = [];
  const patternLength = pattern.length;

  for (let i = startFrom; i <= data.length - patternLength; i++) {
    const candidate = data.slice(i, i + patternLength);
    const sim = calculateSimilarity(pattern, candidate);

    if (sim >= similarity) {
      repeats.push({
        start: i,
        end: i + patternLength - 1,
        similarity: sim
      });
      i += patternLength - 1; // Skip to avoid overlapping matches
    }
  }

  return repeats;
}

function calculateSimilarity(pattern1: number[], pattern2: number[]): number {
  if (pattern1.length !== pattern2.length) return 0;

  const correlation = calculateCorrelation(pattern1, pattern2);
  return Math.max(0, correlation); // Ensure non-negative similarity
}

function calculateCorrelation(x: number[], y: number[]): number {
  if (x.length !== y.length) return 0;

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

function calculateAutocorrelation(data: number[], lag: number): number {
  if (lag >= data.length) return 0;

  const x = data.slice(0, -lag);
  const y = data.slice(lag);

  return calculateCorrelation(x, y);
}

function calculatePhase(data: number[], period: number): number {
  const seasonalAvgs = Array(period).fill(0);
  const counts = Array(period).fill(0);

  for (let i = 0; i < data.length; i++) {
    const seasonIndex = i % period;
    seasonalAvgs[seasonIndex] += data[i];
    counts[seasonIndex]++;
  }

  for (let i = 0; i < period; i++) {
    if (counts[i] > 0) {
      seasonalAvgs[i] /= counts[i];
    }
  }

  return seasonalAvgs.indexOf(Math.max(...seasonalAvgs));
}

function calculatePatternConfidence(
  data: number[],
  pattern: number[],
  repeats: Array<{ start: number; end: number; similarity: number }>,
  threshold: number
): number {
  const avgSimilarity = repeats.reduce((sum, r) => sum + r.similarity, 0) / repeats.length;
  const lengthFactor = Math.min(pattern.length / 5, 1); // Longer patterns are more significant
  const repeatFactor = Math.min(repeats.length / 3, 1); // More repeats increase confidence

  return avgSimilarity * lengthFactor * repeatFactor;
}

function removeOverlappingPatterns(
  patterns: RecognizedPattern[],
  priorityKey: 'strength' | 'confidence'
): RecognizedPattern[] {
  const sorted = [...patterns].sort((a, b) => b[priorityKey] - a[priorityKey]);
  const result: RecognizedPattern[] = [];

  for (const pattern of sorted) {
    const hasOverlap = result.some(existing =>
      patternsOverlap(pattern, existing)
    );

    if (!hasOverlap) {
      result.push(pattern);
    }
  }

  return result;
}

function patternsOverlap(p1: RecognizedPattern, p2: RecognizedPattern): boolean {
  return !(p1.endIndex < p2.startIndex || p2.endIndex < p1.startIndex);
}

function calculateCoverage(patterns: DataPattern[], dataLength: number): number {
  const coveredIndices = new Set<number>();

  patterns.forEach(pattern => {
    const startIndex = pattern.metadata?.startIndex || 0;
    const endIndex = pattern.metadata?.endIndex || 0;

    for (let i = startIndex; i <= endIndex; i++) {
      coveredIndices.add(i);
    }
  });

  return (coveredIndices.size / dataLength) * 100;
}
