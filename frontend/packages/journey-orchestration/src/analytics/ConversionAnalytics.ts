import type {
  ConversionFunnel,
  JourneyMetrics,
  CustomerJourney,
  ConversionEvent,
  TouchpointRecord,
  JourneyStage
} from '../types';

/**
 * Conversion Analytics Engine
 * Provides funnel analysis, drop-off tracking, and ROI calculations
 */
export class ConversionAnalytics {
  private tenantId: string;

  constructor(tenantId: string) {
    this.tenantId = tenantId;
  }

  /**
   * Generate conversion funnel analysis
   */
  async generateConversionFunnel(
    journeys: CustomerJourney[],
    funnelType: 'acquisition' | 'onboarding' | 'support' | 'retention' = 'acquisition'
  ): Promise<ConversionFunnel> {
    const stages = this.getFunnelStages(funnelType);
    const stageData = new Map<JourneyStage, CustomerJourney[]>();

    // Group journeys by stage
    stages.forEach(stage => {
      stageData.set(stage, journeys.filter(j => j.stage === stage));
    });

    // Calculate conversion rates and durations
    const funnelStages = [];
    let previousCount = journeys.length;

    for (let i = 0; i < stages.length; i++) {
      const stage = stages[i];
      const stageJourneys = stageData.get(stage) || [];
      const count = stageJourneys.length;

      // Calculate conversion rate from previous stage
      const conversionRate = previousCount > 0 ? (count / previousCount) * 100 : 0;

      // Calculate average duration to reach this stage
      const averageDuration = this.calculateAverageDuration(stageJourneys, stage);

      // Analyze drop-off reasons
      const dropOffReasons = await this.analyzeDropOffReasons(
        journeys.filter(j => {
          const stageIndex = stages.indexOf(j.stage);
          const currentIndex = stages.indexOf(stage);
          return stageIndex < currentIndex;
        }),
        stage
      );

      funnelStages.push({
        stage,
        count,
        conversionRate: i === 0 ? 100 : conversionRate, // First stage is always 100%
        averageDuration,
        dropOffReasons
      });

      previousCount = count;
    }

    const completedJourneys = journeys.filter(j => j.status === 'completed');
    const overallConversionRate = journeys.length > 0 ?
      (completedJourneys.length / journeys.length) * 100 : 0;

    return {
      name: `${funnelType} Conversion Funnel`,
      stages: funnelStages,
      totalConversions: completedJourneys.length,
      overallConversionRate,
      averageJourneyDuration: this.calculateOverallAverageDuration(completedJourneys)
    };
  }

  /**
   * Generate comprehensive journey metrics
   */
  async generateJourneyMetrics(journeys: CustomerJourney[]): Promise<JourneyMetrics> {
    const totalJourneys = journeys.length;
    const activeJourneys = journeys.filter(j => j.status === 'active').length;
    const completedJourneys = journeys.filter(j => j.status === 'completed').length;
    const abandonedJourneys = journeys.filter(j => j.status === 'abandoned').length;

    // Calculate conversion rates by journey type
    const conversionRates = this.calculateConversionRates(journeys);

    // Calculate average journey duration
    const averageJourneyDuration = this.calculateOverallAverageDuration(
      journeys.filter(j => j.status === 'completed')
    );

    // Generate stage metrics
    const stageMetrics = await this.generateStageMetrics(journeys);

    // Calculate performance metrics
    const slaCompliance = this.calculateSLACompliance(journeys);
    const handoffSuccessRate = await this.calculateHandoffSuccessRate(journeys);
    const automationRate = this.calculateAutomationRate(journeys);

    // Calculate revenue metrics (if available)
    const revenueMetrics = await this.calculateRevenueMetrics(journeys);

    return {
      totalJourneys,
      activeJourneys,
      completedJourneys,
      abandonedJourneys,
      conversionRates,
      averageJourneyDuration,
      stageMetrics,
      slaCompliance,
      handoffSuccessRate,
      automationRate,
      ...revenueMetrics
    };
  }

  /**
   * Analyze conversion attribution
   */
  async analyzeAttribution(journeys: CustomerJourney[]): Promise<{
    sourceAttribution: Record<string, number>;
    channelAttribution: Record<string, number>;
    campaignAttribution: Record<string, number>;
    touchpointInfluence: Array<{
      type: string;
      influence: number;
      conversions: number;
    }>;
  }> {
    const sourceAttribution: Record<string, number> = {};
    const channelAttribution: Record<string, number> = {};
    const campaignAttribution: Record<string, number> = {};
    const touchpointInfluence = new Map<string, { influence: number; conversions: number }>();

    journeys.forEach(journey => {
      // Source attribution
      const source = journey.context.source || 'unknown';
      sourceAttribution[source] = (sourceAttribution[source] || 0) + 1;

      // Channel attribution
      const channel = journey.context.channel || 'unknown';
      channelAttribution[channel] = (channelAttribution[channel] || 0) + 1;

      // Campaign attribution
      const campaign = journey.context.campaign || 'unknown';
      campaignAttribution[campaign] = (campaignAttribution[campaign] || 0) + 1;

      // Touchpoint influence
      if (journey.touchpoints && journey.touchpoints.length > 0) {
        journey.touchpoints.forEach(touchpoint => {
          const existing = touchpointInfluence.get(touchpoint.type) || { influence: 0, conversions: 0 };
          const influence = this.calculateTouchpointInfluence(touchpoint, journey);
          touchpointInfluence.set(touchpoint.type, {
            influence: existing.influence + influence,
            conversions: existing.conversions + (journey.status === 'completed' ? 1 : 0)
          });
        });
      }
    });

    return {
      sourceAttribution,
      channelAttribution,
      campaignAttribution,
      touchpointInfluence: Array.from(touchpointInfluence.entries()).map(([type, data]) => ({
        type,
        ...data
      }))
    };
  }

  /**
   * Generate drop-off analysis for specific stage
   */
  async analyzeDropOffs(
    journeys: CustomerJourney[],
    stage: JourneyStage
  ): Promise<{
    dropOffRate: number;
    commonReasons: Array<{ reason: string; count: number; percentage: number }>;
    timeToDropOff: number; // average days
    recoveryRate: number; // percentage who returned
  }> {
    const journeysAtStage = journeys.filter(j => {
      const stages = this.getAllStages();
      const currentStageIndex = stages.indexOf(j.stage);
      const targetStageIndex = stages.indexOf(stage);
      return currentStageIndex >= targetStageIndex;
    });

    const droppedOffJourneys = journeys.filter(j => {
      const stages = this.getAllStages();
      const currentStageIndex = stages.indexOf(j.stage);
      const targetStageIndex = stages.indexOf(stage);
      return currentStageIndex < targetStageIndex && (j.status === 'abandoned' || j.status === 'failed');
    });

    const dropOffRate = journeysAtStage.length > 0 ?
      (droppedOffJourneys.length / journeysAtStage.length) * 100 : 0;

    // Analyze reasons for drop-off
    const reasonCounts = new Map<string, number>();
    let totalTimeToDropOff = 0;
    let recoveredCount = 0;

    droppedOffJourneys.forEach(journey => {
      const reason = journey.metadata.dropOffReason || 'unknown';
      reasonCounts.set(reason, (reasonCounts.get(reason) || 0) + 1);

      // Calculate time to drop off
      if (journey.startedAt && journey.completedAt) {
        const duration = new Date(journey.completedAt).getTime() - new Date(journey.startedAt).getTime();
        totalTimeToDropOff += duration / (1000 * 60 * 60 * 24); // Convert to days
      }

      // Check if journey was recovered
      if (journey.metadata.recovered) {
        recoveredCount++;
      }
    });

    const commonReasons = Array.from(reasonCounts.entries())
      .map(([reason, count]) => ({
        reason,
        count,
        percentage: (count / droppedOffJourneys.length) * 100
      }))
      .sort((a, b) => b.count - a.count);

    return {
      dropOffRate,
      commonReasons,
      timeToDropOff: droppedOffJourneys.length > 0 ? totalTimeToDropOff / droppedOffJourneys.length : 0,
      recoveryRate: droppedOffJourneys.length > 0 ? (recoveredCount / droppedOffJourneys.length) * 100 : 0
    };
  }

  /**
   * Generate cohort analysis
   */
  async generateCohortAnalysis(
    journeys: CustomerJourney[],
    periodType: 'week' | 'month' | 'quarter' = 'month'
  ): Promise<Array<{
    cohort: string;
    size: number;
    conversionRate: number;
    averageDuration: number;
    retentionRates: number[]; // retention at 1, 2, 3... periods
  }>> {
    // Group journeys by cohort (start period)
    const cohorts = new Map<string, CustomerJourney[]>();

    journeys.forEach(journey => {
      const cohortPeriod = this.getCohortPeriod(journey.startedAt, periodType);
      if (!cohorts.has(cohortPeriod)) {
        cohorts.set(cohortPeriod, []);
      }
      cohorts.get(cohortPeriod)!.push(journey);
    });

    // Analyze each cohort
    const cohortAnalysis = [];
    for (const [cohort, cohortJourneys] of cohorts.entries()) {
      const size = cohortJourneys.length;
      const completedCount = cohortJourneys.filter(j => j.status === 'completed').length;
      const conversionRate = (completedCount / size) * 100;

      const averageDuration = this.calculateOverallAverageDuration(
        cohortJourneys.filter(j => j.status === 'completed')
      );

      // Calculate retention rates for subsequent periods
      const retentionRates = this.calculateCohortRetention(cohortJourneys, cohort, periodType);

      cohortAnalysis.push({
        cohort,
        size,
        conversionRate,
        averageDuration,
        retentionRates
      });
    }

    return cohortAnalysis.sort((a, b) => a.cohort.localeCompare(b.cohort));
  }

  /**
   * Export analytics data
   */
  async exportAnalytics(
    journeys: CustomerJourney[],
    format: 'csv' | 'json'
  ): Promise<string> {
    const metrics = await this.generateJourneyMetrics(journeys);
    const funnels = await Promise.all([
      this.generateConversionFunnel(journeys, 'acquisition'),
      this.generateConversionFunnel(journeys, 'onboarding'),
      this.generateConversionFunnel(journeys, 'retention')
    ]);
    const attribution = await this.analyzeAttribution(journeys);

    const exportData = {
      summary: {
        generated_at: new Date().toISOString(),
        tenant_id: this.tenantId,
        total_journeys: journeys.length
      },
      metrics,
      funnels,
      attribution,
      journeys: journeys.map(j => ({
        id: j.id,
        type: j.type,
        stage: j.stage,
        status: j.status,
        progress: j.progress,
        duration: j.completedAt && j.startedAt ?
          new Date(j.completedAt).getTime() - new Date(j.startedAt).getTime() : null,
        touchpoints_count: j.touchpoints?.length || 0,
        conversion_events_count: j.conversionEvents?.length || 0
      }))
    };

    if (format === 'json') {
      return JSON.stringify(exportData, null, 2);
    } else {
      // Convert to CSV format
      return this.convertToCSV(exportData);
    }
  }

  // Private helper methods

  private getFunnelStages(funnelType: string): JourneyStage[] {
    const stageMap = {
      acquisition: ['prospect', 'lead', 'qualified', 'customer'],
      onboarding: ['customer', 'active_service'],
      support: ['support'],
      retention: ['active_service', 'renewal']
    };
    return stageMap[funnelType as keyof typeof stageMap] || ['prospect', 'lead', 'customer'];
  }

  private getAllStages(): JourneyStage[] {
    return ['prospect', 'lead', 'qualified', 'customer', 'active_service', 'support', 'renewal', 'churn', 'win_back'];
  }

  private calculateAverageDuration(journeys: CustomerJourney[], stage: JourneyStage): number {
    const relevantJourneys = journeys.filter(j => j.stage === stage && j.startedAt);
    if (relevantJourneys.length === 0) return 0;

    const totalDuration = relevantJourneys.reduce((sum, journey) => {
      const endTime = journey.completedAt || new Date().toISOString();
      const duration = new Date(endTime).getTime() - new Date(journey.startedAt).getTime();
      return sum + (duration / (1000 * 60 * 60 * 24)); // Convert to days
    }, 0);

    return totalDuration / relevantJourneys.length;
  }

  private calculateOverallAverageDuration(journeys: CustomerJourney[]): number {
    const completedJourneys = journeys.filter(j => j.completedAt);
    if (completedJourneys.length === 0) return 0;

    const totalDuration = completedJourneys.reduce((sum, journey) => {
      const duration = new Date(journey.completedAt!).getTime() - new Date(journey.startedAt).getTime();
      return sum + (duration / (1000 * 60 * 60 * 24)); // Convert to days
    }, 0);

    return totalDuration / completedJourneys.length;
  }

  private async analyzeDropOffReasons(
    droppedJourneys: CustomerJourney[],
    targetStage: JourneyStage
  ): Promise<Array<{ reason: string; count: number }>> {
    const reasonCounts = new Map<string, number>();

    droppedJourneys.forEach(journey => {
      const reason = journey.metadata.dropOffReason || 'unknown';
      reasonCounts.set(reason, (reasonCounts.get(reason) || 0) + 1);
    });

    return Array.from(reasonCounts.entries())
      .map(([reason, count]) => ({ reason, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5); // Top 5 reasons
  }

  private calculateConversionRates(journeys: CustomerJourney[]): Record<string, number> {
    const typeGroups = new Map<string, { total: number; completed: number }>();

    journeys.forEach(journey => {
      const type = journey.type;
      if (!typeGroups.has(type)) {
        typeGroups.set(type, { total: 0, completed: 0 });
      }
      const group = typeGroups.get(type)!;
      group.total++;
      if (journey.status === 'completed') {
        group.completed++;
      }
    });

    const rates: Record<string, number> = {};
    typeGroups.forEach(({ total, completed }, type) => {
      rates[type] = total > 0 ? (completed / total) * 100 : 0;
    });

    return rates;
  }

  private async generateStageMetrics(journeys: CustomerJourney[]): Promise<Record<JourneyStage, {
    count: number;
    averageDuration: number;
    completionRate: number;
  }>> {
    const stages = this.getAllStages();
    const stageMetrics: Record<JourneyStage, { count: number; averageDuration: number; completionRate: number }> = {} as any;

    stages.forEach(stage => {
      const stageJourneys = journeys.filter(j => j.stage === stage);
      const completedStageJourneys = stageJourneys.filter(j => j.status === 'completed');

      stageMetrics[stage] = {
        count: stageJourneys.length,
        averageDuration: this.calculateAverageDuration(stageJourneys, stage),
        completionRate: stageJourneys.length > 0 ?
          (completedStageJourneys.length / stageJourneys.length) * 100 : 0
      };
    });

    return stageMetrics;
  }

  private calculateSLACompliance(journeys: CustomerJourney[]): number {
    const journeysWithSLA = journeys.filter(j => j.estimatedCompletion);
    if (journeysWithSLA.length === 0) return 100;

    const compliantJourneys = journeysWithSLA.filter(j => {
      if (!j.completedAt || !j.estimatedCompletion) return false;
      return new Date(j.completedAt).getTime() <= new Date(j.estimatedCompletion).getTime();
    });

    return (compliantJourneys.length / journeysWithSLA.length) * 100;
  }

  private async calculateHandoffSuccessRate(journeys: CustomerJourney[]): Promise<number> {
    const allHandoffs = journeys.flatMap(j => j.activeHandoffs || []);
    if (allHandoffs.length === 0) return 100;

    const successfulHandoffs = allHandoffs.filter(h => h.status === 'completed' && h.result === 'success');
    return (successfulHandoffs.length / allHandoffs.length) * 100;
  }

  private calculateAutomationRate(journeys: CustomerJourney[]): number {
    const totalSteps = journeys.reduce((sum, j) => sum + j.totalSteps, 0);
    if (totalSteps === 0) return 0;

    // This would be calculated based on step types in a full implementation
    // For now, return a placeholder
    return 75; // Assume 75% automation rate
  }

  private async calculateRevenueMetrics(journeys: CustomerJourney[]): Promise<{
    totalRevenue?: number;
    revenuePerJourney?: number;
    lifetimeValue?: number;
  }> {
    // Revenue calculation would integrate with billing system
    // Placeholder implementation
    const completedJourneys = journeys.filter(j => j.status === 'completed');
    const estimatedRevenuePerJourney = 500; // Placeholder value

    return {
      totalRevenue: completedJourneys.length * estimatedRevenuePerJourney,
      revenuePerJourney: estimatedRevenuePerJourney,
      lifetimeValue: estimatedRevenuePerJourney * 24 // 2 years worth
    };
  }

  private calculateTouchpointInfluence(touchpoint: TouchpointRecord, journey: CustomerJourney): number {
    // Calculate influence based on touchpoint type, timing, and outcome
    let influence = 1;

    // Type-based influence
    const typeInfluence = {
      'email': 1,
      'sms': 1.2,
      'call': 2,
      'meeting': 3,
      'web_visit': 0.5,
      'app_usage': 0.8,
      'support_ticket': 1.5,
      'billing_interaction': 1.1
    };
    influence *= typeInfluence[touchpoint.type as keyof typeof typeInfluence] || 1;

    // Outcome-based influence
    if (touchpoint.outcome === 'positive') influence *= 1.5;
    else if (touchpoint.outcome === 'negative') influence *= 0.5;

    // Timing influence (earlier touchpoints have more influence)
    const touchpointTime = new Date(touchpoint.timestamp).getTime();
    const journeyStart = new Date(journey.startedAt).getTime();
    const journeyDuration = journey.completedAt ?
      new Date(journey.completedAt).getTime() - journeyStart :
      Date.now() - journeyStart;

    const timePosition = (touchpointTime - journeyStart) / journeyDuration;
    influence *= (1 - timePosition * 0.5); // Earlier touchpoints get higher influence

    return influence;
  }

  private getCohortPeriod(dateString: string, periodType: 'week' | 'month' | 'quarter'): string {
    const date = new Date(dateString);

    switch (periodType) {
      case 'week':
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        return weekStart.toISOString().split('T')[0];
      case 'month':
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      case 'quarter':
        const quarter = Math.floor(date.getMonth() / 3) + 1;
        return `${date.getFullYear()}-Q${quarter}`;
      default:
        return date.toISOString().split('T')[0];
    }
  }

  private calculateCohortRetention(
    cohortJourneys: CustomerJourney[],
    cohort: string,
    periodType: 'week' | 'month' | 'quarter'
  ): number[] {
    // Placeholder implementation - would calculate actual retention in production
    const retentionRates = [100]; // Start at 100% for period 0

    for (let period = 1; period <= 12; period++) {
      // Simulate retention decay
      const baseRetention = Math.max(20, 100 - (period * 8));
      const randomVariation = (Math.random() - 0.5) * 10;
      retentionRates.push(Math.max(0, baseRetention + randomVariation));
    }

    return retentionRates;
  }

  private convertToCSV(data: any): string {
    // Basic CSV conversion - would be more sophisticated in production
    const headers = ['Journey ID', 'Type', 'Stage', 'Status', 'Progress', 'Duration (ms)', 'Touchpoints', 'Conversions'];
    const rows = data.journeys.map((j: any) => [
      j.id,
      j.type,
      j.stage,
      j.status,
      j.progress,
      j.duration || '',
      j.touchpoints_count,
      j.conversion_events_count
    ]);

    return [headers, ...rows]
      .map(row => row.map(cell => `"${cell}"`).join(','))
      .join('\n');
  }
}
