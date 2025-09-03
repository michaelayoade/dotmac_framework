import type { BusinessRule, RuleContext, RuleEngineConfig, RuleExecutionResult } from '../types';
import { RuleEngine } from './RuleEngine';

/**
 * High-level rule management system
 */
export class RuleManager {
  private engine: RuleEngine;
  private rules: Map<string, BusinessRule> = new Map();
  private rulesByCategory: Map<string, BusinessRule[]> = new Map();

  constructor(config?: RuleEngineConfig) {
    this.engine = new RuleEngine(config);
  }

  /**
   * Add a rule to the manager
   */
  addRule(rule: BusinessRule): void {
    this.rules.set(rule.id, rule);
    this.updateCategoryIndex(rule);
  }

  /**
   * Add multiple rules
   */
  addRules(rules: BusinessRule[]): void {
    rules.forEach((rule) => this.addRule(rule));
  }

  /**
   * Update an existing rule
   */
  updateRule(ruleId: string, updates: Partial<BusinessRule>): boolean {
    const existingRule = this.rules.get(ruleId);
    if (!existingRule) return false;

    const updatedRule = {
      ...existingRule,
      ...updates,
      updatedAt: new Date(),
    };

    this.rules.set(ruleId, updatedRule);
    this.updateCategoryIndex(updatedRule);
    return true;
  }

  /**
   * Remove a rule
   */
  removeRule(ruleId: string): boolean {
    const rule = this.rules.get(ruleId);
    if (!rule) return false;

    this.rules.delete(ruleId);
    this.removeCategoryIndex(rule);
    return true;
  }

  /**
   * Get a rule by ID
   */
  getRule(ruleId: string): BusinessRule | undefined {
    return this.rules.get(ruleId);
  }

  /**
   * Get all rules
   */
  getAllRules(): BusinessRule[] {
    return Array.from(this.rules.values());
  }

  /**
   * Get rules by category
   */
  getRulesByCategory(category: string): BusinessRule[] {
    return this.rulesByCategory.get(category) || [];
  }

  /**
   * Get rules by portal scope
   */
  getRulesByPortal(portal: string): BusinessRule[] {
    return Array.from(this.rules.values()).filter(
      (rule) => rule.portalScope.length === 0 || rule.portalScope.includes(portal as any)
    );
  }

  /**
   * Get active rules only
   */
  getActiveRules(): BusinessRule[] {
    return Array.from(this.rules.values()).filter((rule) => rule.status === 'active');
  }

  /**
   * Execute rules for a given context
   */
  async executeRules(
    context: RuleContext,
    filters?: {
      category?: string;
      portal?: string;
      tags?: string[];
    }
  ): Promise<RuleExecutionResult[]> {
    let rulesToExecute = this.getActiveRules();

    // Apply filters
    if (filters?.category) {
      rulesToExecute = rulesToExecute.filter((rule) => rule.category === filters.category);
    }

    if (filters?.portal) {
      rulesToExecute = rulesToExecute.filter(
        (rule) => rule.portalScope.length === 0 || rule.portalScope.includes(filters.portal as any)
      );
    }

    if (filters?.tags && filters.tags.length > 0) {
      rulesToExecute = rulesToExecute.filter((rule) =>
        filters.tags!.some((tag) => rule.tags.includes(tag))
      );
    }

    return await this.engine.executeRules(rulesToExecute, context);
  }

  /**
   * Test a single rule without executing actions
   */
  async testRule(ruleId: string, context: RuleContext): Promise<RuleExecutionResult | null> {
    const rule = this.rules.get(ruleId);
    if (!rule) return null;

    // Create a test version of the rule with no actions
    const testRule = { ...rule, actions: [] };
    const results = await this.engine.executeRules([testRule], context);
    return results[0] || null;
  }

  /**
   * Validate a rule
   */
  validateRule(rule: BusinessRule): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Basic validation
    if (!rule.id) errors.push('Rule ID is required');
    if (!rule.name) errors.push('Rule name is required');
    if (!rule.category) errors.push('Rule category is required');
    if (rule.conditions.length === 0) errors.push('At least one condition is required');
    if (rule.actions.length === 0) errors.push('At least one action is required');

    // Condition validation
    rule.conditions.forEach((condition, index) => {
      if (!condition.field) errors.push(`Condition ${index + 1}: field is required`);
      if (!condition.operator) errors.push(`Condition ${index + 1}: operator is required`);
      if (condition.value === undefined && !['exists', 'not_exists'].includes(condition.operator)) {
        errors.push(`Condition ${index + 1}: value is required for operator ${condition.operator}`);
      }
    });

    // Action validation
    rule.actions.forEach((action, index) => {
      if (!action.type) errors.push(`Action ${index + 1}: type is required`);

      // Validate action-specific requirements
      switch (action.type) {
        case 'set_value':
          if (!action.target) errors.push(`Action ${index + 1}: target is required for set_value`);
          break;
        case 'send_notification':
          if (!action.parameters?.message)
            errors.push(`Action ${index + 1}: message parameter is required for send_notification`);
          break;
        case 'apply_discount':
          if (!action.value && !action.parameters?.percent) {
            errors.push(`Action ${index + 1}: discount value or percent parameter is required`);
          }
          break;
      }
    });

    // Custom logic validation
    if (rule.conditionLogic === 'custom' && rule.customLogic) {
      try {
        JSON.parse(rule.customLogic);
      } catch (e) {
        errors.push('Custom logic must be valid JSON');
      }
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Get rule statistics
   */
  getRuleStatistics(): {
    total: number;
    active: number;
    inactive: number;
    draft: number;
    archived: number;
    byCategory: Record<string, number>;
    byPortal: Record<string, number>;
  } {
    const rules = Array.from(this.rules.values());

    const stats = {
      total: rules.length,
      active: 0,
      inactive: 0,
      draft: 0,
      archived: 0,
      byCategory: {} as Record<string, number>,
      byPortal: {} as Record<string, number>,
    };

    rules.forEach((rule) => {
      // Count by status
      stats[rule.status]++;

      // Count by category
      stats.byCategory[rule.category] = (stats.byCategory[rule.category] || 0) + 1;

      // Count by portal
      rule.portalScope.forEach((portal) => {
        stats.byPortal[portal] = (stats.byPortal[portal] || 0) + 1;
      });
    });

    return stats;
  }

  /**
   * Export rules to JSON
   */
  exportRules(filters?: { category?: string; status?: string }): string {
    let rules = Array.from(this.rules.values());

    if (filters?.category) {
      rules = rules.filter((rule) => rule.category === filters.category);
    }

    if (filters?.status) {
      rules = rules.filter((rule) => rule.status === filters.status);
    }

    return JSON.stringify(rules, null, 2);
  }

  /**
   * Import rules from JSON
   */
  importRules(
    jsonData: string,
    options?: { overwrite?: boolean }
  ): {
    imported: number;
    skipped: number;
    errors: string[];
  } {
    const result = { imported: 0, skipped: 0, errors: [] as string[] };

    try {
      const rules = JSON.parse(jsonData) as BusinessRule[];

      rules.forEach((rule, index) => {
        const validation = this.validateRule(rule);

        if (!validation.valid) {
          result.errors.push(`Rule ${index + 1}: ${validation.errors.join(', ')}`);
          result.skipped++;
          return;
        }

        const exists = this.rules.has(rule.id);

        if (exists && !options?.overwrite) {
          result.skipped++;
          return;
        }

        this.addRule(rule);
        result.imported++;
      });
    } catch (error) {
      result.errors.push('Invalid JSON format');
    }

    return result;
  }

  /**
   * Get execution audit log
   */
  getExecutionAuditLog(): RuleExecutionResult[] {
    return this.engine.getAuditLog();
  }

  /**
   * Clear execution audit log
   */
  clearExecutionAuditLog(): void {
    this.engine.clearAuditLog();
  }

  // Private helper methods
  private updateCategoryIndex(rule: BusinessRule): void {
    const categoryRules = this.rulesByCategory.get(rule.category) || [];
    const filtered = categoryRules.filter((r) => r.id !== rule.id);
    filtered.push(rule);
    this.rulesByCategory.set(rule.category, filtered);
  }

  private removeCategoryIndex(rule: BusinessRule): void {
    const categoryRules = this.rulesByCategory.get(rule.category) || [];
    const filtered = categoryRules.filter((r) => r.id !== rule.id);
    if (filtered.length > 0) {
      this.rulesByCategory.set(rule.category, filtered);
    } else {
      this.rulesByCategory.delete(rule.category);
    }
  }
}
