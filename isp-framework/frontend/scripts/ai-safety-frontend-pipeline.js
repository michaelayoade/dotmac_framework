#!/usr/bin/env node

/**
 * Frontend AI Safety Validation Pipeline
 * 
 * This pipeline extends the backend AI safety approach to frontend code,
 * ensuring that frontend components handling sensitive data (payments, PII, etc.)
 * follow the same AI-first safety principles as the backend.
 */

const fs = require('fs').promises;
const path = require('path');
const { execSync } = require('child_process');

class FrontendAISafetyPipeline {
  constructor() {
    this.results = {
      componentSafety: [],
      paymentSecurity: [],
      dataSanitization: [],
      inputValidation: [],
      errors: [],
      warnings: []
    };
    
    this.criticalPatterns = {
      // Revenue-critical patterns that must be validated
      paymentProcessing: [
        /payment.*amount/i,
        /total.*calculate/i,
        /tax.*rate/i,
        /discount.*percent/i,
        /currency.*format/i,
        /billing.*total/i
      ],
      
      // Data exposure risks
      sensitiveData: [
        /credit.*card/i,
        /social.*security/i,
        /bank.*account/i,
        /routing.*number/i,
        /cvv/i,
        /password/i
      ],
      
      // Input validation patterns
      userInput: [
        /useState.*input/i,
        /onChange.*value/i,
        /form.*data/i,
        /user.*input/i,
        /\.value/,
        /e\.target\.value/
      ],
      
      // Dangerous patterns that indicate security risks
      dangerous: [
        /eval\(/,
        /innerHTML.*=.*[^"']/,
        /dangerouslySetInnerHTML/,
        /document\.write/,
        /\.exec\(/,
        /new Function\(/
      ]
    };
  }

  async run() {
    console.log('🤖 Starting Frontend AI Safety Validation Pipeline');
    console.log('=' .repeat(60));
    
    try {
      await this.scanComponents();
      await this.validatePaymentSecurity();
      await this.checkInputSanitization();
      await this.runPropertyBasedTests();
      await this.generateReport();
      
      return this.results;
    } catch (error) {
      console.error('❌ Pipeline failed:', error);
      throw error;
    }
  }

  async scanComponents() {
    console.log('🔍 Scanning React components for AI safety violations...');
    
    const componentDirs = [
      'packages/headless/src/components',
      'packages/headless/src/hooks', 
      'apps/admin/src/components',
      'apps/customer/src/components',
      'apps/reseller/src/components'
    ];
    
    for (const dir of componentDirs) {
      const fullPath = path.join(process.cwd(), dir);
      try {
        await this.scanDirectory(fullPath, dir);
      } catch (error) {
        if (error.code !== 'ENOENT') {
          this.results.errors.push(`Failed to scan ${dir}: ${error.message}`);
        }
      }
    }
    
    console.log(`   Found ${this.results.componentSafety.length} components with safety concerns`);
  }

  async scanDirectory(dirPath, relativePath) {
    try {
      const entries = await fs.readdir(dirPath, { withFileTypes: true });
      
      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);
        const relativeFilePath = path.join(relativePath, entry.name);
        
        if (entry.isDirectory()) {
          await this.scanDirectory(fullPath, relativeFilePath);
        } else if (entry.name.match(/\.(tsx?|jsx?)$/)) {
          await this.analyzeComponent(fullPath, relativeFilePath);
        }
      }
    } catch (error) {
      // Directory might not exist, skip silently
      if (error.code !== 'ENOENT') {
        throw error;
      }
    }
  }

  async analyzeComponent(filePath, relativePath) {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const lines = content.split('\n');
      
      const issues = [];
      
      // Check for payment processing without validation
      this.criticalPatterns.paymentProcessing.forEach((pattern, idx) => {
        lines.forEach((line, lineNum) => {
          if (pattern.test(line)) {
            // Check if there's proper validation nearby
            const context = lines.slice(Math.max(0, lineNum - 3), lineNum + 4);
            const hasValidation = context.some(contextLine => 
              /validate|assert|check|verify/i.test(contextLine)
            );
            
            if (!hasValidation) {
              issues.push({
                type: 'payment_without_validation',
                line: lineNum + 1,
                content: line.trim(),
                severity: 'critical',
                message: 'Payment processing without proper validation'
              });
            }
          }
        });
      });
      
      // Check for sensitive data exposure
      this.criticalPatterns.sensitiveData.forEach(pattern => {
        lines.forEach((line, lineNum) => {
          if (pattern.test(line) && !/\*\*\*|\[REDACTED\]|\.mask\(/.test(line)) {
            issues.push({
              type: 'sensitive_data_exposure',
              line: lineNum + 1, 
              content: line.trim(),
              severity: 'high',
              message: 'Potential sensitive data exposure without masking'
            });
          }
        });
      });
      
      // Check for dangerous patterns
      this.criticalPatterns.dangerous.forEach(pattern => {
        lines.forEach((line, lineNum) => {
          if (pattern.test(line)) {
            issues.push({
              type: 'dangerous_pattern',
              line: lineNum + 1,
              content: line.trim(),
              severity: 'critical',
              message: 'Dangerous code pattern that could enable code injection'
            });
          }
        });
      });
      
      // Check for unvalidated user input
      this.criticalPatterns.userInput.forEach(pattern => {
        lines.forEach((line, lineNum) => {
          if (pattern.test(line)) {
            // Look for validation in surrounding lines
            const context = lines.slice(Math.max(0, lineNum - 2), lineNum + 3);
            const hasInputValidation = context.some(contextLine =>
              /\.trim\(\)|\.replace\(|sanitize|validate|escape|length\s*[><=]/i.test(contextLine)
            );
            
            if (!hasInputValidation) {
              issues.push({
                type: 'unvalidated_input',
                line: lineNum + 1,
                content: line.trim(),
                severity: 'medium',
                message: 'User input without apparent validation'
              });
            }
          }
        });
      });
      
      if (issues.length > 0) {
        this.results.componentSafety.push({
          file: relativePath,
          issues: issues
        });
      }
    } catch (error) {
      this.results.errors.push(`Failed to analyze ${relativePath}: ${error.message}`);
    }
  }

  async validatePaymentSecurity() {
    console.log('💳 Validating payment processing security...');
    
    // Look for payment-related components and hooks
    const paymentFiles = this.results.componentSafety
      .filter(result => result.file.toLowerCase().includes('payment') || 
                       result.file.toLowerCase().includes('billing'))
      .map(result => result.file);
    
    for (const file of paymentFiles) {
      const issues = [];
      
      try {
        const content = await fs.readFile(path.join(process.cwd(), file), 'utf-8');
        
        // Check for hardcoded payment amounts
        if (/amount\s*=\s*\d+/.test(content)) {
          issues.push({
            type: 'hardcoded_amount',
            severity: 'high',
            message: 'Hardcoded payment amounts detected'
          });
        }
        
        // Check for client-side total calculations without server validation
        if (/total.*=.*amount.*\*|calculate.*total/i.test(content) && 
            !/server.*validate|api.*confirm/i.test(content)) {
          issues.push({
            type: 'client_side_calculation',
            severity: 'critical',
            message: 'Client-side payment calculations without server validation'
          });
        }
        
        // Check for payment data in localStorage/sessionStorage
        if (/localStorage|sessionStorage/.test(content) && 
            /payment|card|billing/i.test(content)) {
          issues.push({
            type: 'payment_data_storage',
            severity: 'critical',
            message: 'Payment data stored in browser storage'
          });
        }
        
        if (issues.length > 0) {
          this.results.paymentSecurity.push({
            file: file,
            issues: issues
          });
        }
      } catch (error) {
        this.results.errors.push(`Failed to validate payment security in ${file}: ${error.message}`);
      }
    }
    
    console.log(`   Found ${this.results.paymentSecurity.length} files with payment security issues`);
  }

  async checkInputSanitization() {
    console.log('🧹 Checking input sanitization patterns...');
    
    // This would be expanded to check all form components
    const formComponents = this.results.componentSafety
      .filter(result => 
        result.file.toLowerCase().includes('form') ||
        result.issues.some(issue => issue.type === 'unvalidated_input')
      );
    
    for (const component of formComponents) {
      const sanitizationIssues = component.issues.filter(issue => 
        issue.type === 'unvalidated_input'
      );
      
      if (sanitizationIssues.length > 0) {
        this.results.dataSanitization.push({
          file: component.file,
          unvalidatedInputs: sanitizationIssues.length,
          issues: sanitizationIssues
        });
      }
    }
    
    console.log(`   Found ${this.results.dataSanitization.length} components with input sanitization issues`);
  }

  async runPropertyBasedTests() {
    console.log('🎲 Running property-based tests...');
    
    try {
      // Run the property-based tests we created
      const testResults = execSync(
        'npm test -- --testNamePattern="AI-First|AI-Generated" --verbose --passWithNoTests',
        { 
          encoding: 'utf-8',
          cwd: process.cwd(),
          timeout: 120000 
        }
      );
      
      console.log('   ✅ Property-based tests passed');
      this.results.propertyTests = {
        status: 'passed',
        output: testResults
      };
    } catch (error) {
      console.log('   ❌ Property-based tests failed');
      this.results.propertyTests = {
        status: 'failed',
        error: error.message,
        output: error.stdout
      };
      this.results.errors.push(`Property-based tests failed: ${error.message}`);
    }
  }

  async generateReport() {
    console.log('📊 Generating AI Safety Report...');
    
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalComponents: this.results.componentSafety.length,
        criticalIssues: this.getAllIssues().filter(i => i.severity === 'critical').length,
        highIssues: this.getAllIssues().filter(i => i.severity === 'high').length,
        mediumIssues: this.getAllIssues().filter(i => i.severity === 'medium').length,
        paymentSecurityIssues: this.results.paymentSecurity.length,
        inputValidationIssues: this.results.dataSanitization.length
      },
      details: this.results,
      recommendations: this.generateRecommendations()
    };
    
    await fs.writeFile(
      path.join(process.cwd(), 'frontend-ai-safety-report.json'),
      JSON.stringify(report, null, 2)
    );
    
    // Print summary
    console.log('\n📋 AI Safety Summary:');
    console.log(`   🔍 Components scanned: ${report.summary.totalComponents}`);
    console.log(`   🚨 Critical issues: ${report.summary.criticalIssues}`);
    console.log(`   ⚠️  High priority: ${report.summary.highIssues}`);
    console.log(`   📝 Medium priority: ${report.summary.mediumIssues}`);
    console.log(`   💳 Payment security issues: ${report.summary.paymentSecurityIssues}`);
    console.log(`   🧹 Input validation issues: ${report.summary.inputValidationIssues}`);
    
    if (this.results.errors.length > 0) {
      console.log(`   ❌ Errors encountered: ${this.results.errors.length}`);
      this.results.errors.forEach(error => console.log(`      - ${error}`));
    }
    
    const totalIssues = report.summary.criticalIssues + report.summary.highIssues;
    if (totalIssues > 0) {
      console.log('\n🚨 AI Safety Pipeline FAILED - Critical or High severity issues found');
      process.exit(1);
    } else {
      console.log('\n✅ AI Safety Pipeline PASSED - No critical issues found');
    }
  }

  getAllIssues() {
    const allIssues = [];
    this.results.componentSafety.forEach(component => {
      component.issues.forEach(issue => allIssues.push(issue));
    });
    this.results.paymentSecurity.forEach(payment => {
      payment.issues.forEach(issue => allIssues.push(issue));
    });
    this.results.dataSanitization.forEach(data => {
      data.issues.forEach(issue => allIssues.push(issue));
    });
    return allIssues;
  }

  generateRecommendations() {
    const recommendations = [];
    
    if (this.results.paymentSecurity.length > 0) {
      recommendations.push({
        category: 'Payment Security',
        priority: 'critical',
        action: 'Implement server-side validation for all payment calculations',
        rationale: 'Client-side payment calculations can be manipulated to reduce payment amounts'
      });
    }
    
    if (this.results.dataSanitization.length > 0) {
      recommendations.push({
        category: 'Input Validation',
        priority: 'high',
        action: 'Add input sanitization and validation to all form components',
        rationale: 'Unvalidated input can lead to XSS, injection attacks, and data corruption'
      });
    }
    
    const criticalCount = this.getAllIssues().filter(i => i.severity === 'critical').length;
    if (criticalCount > 0) {
      recommendations.push({
        category: 'AI Safety',
        priority: 'critical',
        action: 'Implement comprehensive property-based testing for all revenue-critical components',
        rationale: 'Property-based testing catches edge cases that traditional unit tests miss'
      });
    }
    
    return recommendations;
  }
}

// CLI execution
if (require.main === module) {
  const pipeline = new FrontendAISafetyPipeline();
  pipeline.run().catch(error => {
    console.error('Pipeline execution failed:', error);
    process.exit(1);
  });
}

module.exports = FrontendAISafetyPipeline;