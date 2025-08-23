#!/usr/bin/env node
/**
 * Mutation Testing for Frontend Code Quality
 * 
 * Validates test quality by introducing mutations and checking if tests catch them
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// Mutation operators
const MUTATIONS = {
  // Arithmetic operators
  arithmetic: [
    { from: '+', to: '-', description: 'Addition to subtraction' },
    { from: '-', to: '+', description: 'Subtraction to addition' },
    { from: '*', to: '/', description: 'Multiplication to division' },
    { from: '/', to: '*', description: 'Division to multiplication' },
    { from: '%', to: '*', description: 'Modulo to multiplication' }
  ],
  
  // Comparison operators
  comparison: [
    { from: '===', to: '!==', description: 'Strict equality to inequality' },
    { from: '!==', to: '===', description: 'Strict inequality to equality' },
    { from: '==', to: '!=', description: 'Equality to inequality' },
    { from: '!=', to: '==', description: 'Inequality to equality' },
    { from: '>', to: '<', description: 'Greater than to less than' },
    { from: '<', to: '>', description: 'Less than to greater than' },
    { from: '>=', to: '<=', description: 'Greater than or equal to less than or equal' },
    { from: '<=', to: '>=', description: 'Less than or equal to greater than or equal' }
  ],
  
  // Logical operators
  logical: [
    { from: '&&', to: '||', description: 'Logical AND to OR' },
    { from: '||', to: '&&', description: 'Logical OR to AND' },
    { from: '!', to: '', description: 'Logical NOT removal' }
  ],
  
  // Boolean literals
  boolean: [
    { from: 'true', to: 'false', description: 'True to false' },
    { from: 'false', to: 'true', description: 'False to true' }
  ],
  
  // React-specific mutations
  react: [
    { from: 'onClick', to: 'onDoubleClick', description: 'onClick to onDoubleClick' },
    { from: 'onChange', to: 'onInput', description: 'onChange to onInput' },
    { from: 'disabled={true}', to: 'disabled={false}', description: 'Disable to enable' },
    { from: 'disabled={false}', to: 'disabled={true}', description: 'Enable to disable' },
    { from: 'required={true}', to: 'required={false}', description: 'Required to optional' },
    { from: 'required={false}', to: 'required={true}', description: 'Optional to required' }
  ],
  
  // String literals
  string: [
    { from: '""', to: '"mutated"', description: 'Empty string to "mutated"' },
    { from: "''", to: "'mutated'", description: "Empty string to 'mutated'" }
  ],
  
  // Numeric literals
  numeric: [
    { from: '0', to: '1', description: 'Zero to one' },
    { from: '1', to: '0', description: 'One to zero' },
    { from: '-1', to: '1', description: 'Negative one to positive one' }
  ]
};

// Files to mutate (focus on critical components)
const MUTATION_TARGETS = [
  'packages/primitives/src/forms/Button.tsx',
  'packages/primitives/src/forms/Form.tsx',
  'packages/styled-components/src/shared/Badge.tsx',
  'packages/headless/src/hooks/useAuth.ts',
  'packages/headless/src/api/clients/BaseApiClient.ts'
];

class MutationTester {
  constructor() {
    this.results = {
      totalMutations: 0,
      killedMutations: 0, // Mutations caught by tests
      survivedMutations: 0, // Mutations not caught by tests
      timeoutMutations: 0, // Tests that timed out
      errorMutations: 0, // Mutations that caused compilation errors
      mutationScore: 0,
      details: []
    };
    this.workingDir = path.join(__dirname, '../mutation-testing');
    this.backupDir = path.join(this.workingDir, 'backups');
  }

  async setup() {
    // Create working directories
    if (!fs.existsSync(this.workingDir)) {
      fs.mkdirSync(this.workingDir, { recursive: true });
    }
    if (!fs.existsSync(this.backupDir)) {
      fs.mkdirSync(this.backupDir, { recursive: true });
    }
    
    console.log('🧬 Setting up mutation testing environment...');
  }

  async runMutationTesting() {
    console.log('🎯 Starting mutation testing...');
    
    for (const targetFile of MUTATION_TARGETS) {
      console.log(`\n📁 Processing: ${targetFile}`);
      await this.mutateFile(targetFile);
    }
    
    this.calculateMutationScore();
    this.generateReport();
  }

  async mutateFile(filePath) {
    const fullPath = path.join(__dirname, '..', filePath);
    
    if (!fs.existsSync(fullPath)) {
      console.log(`⚠️  File not found: ${filePath}`);
      return;
    }

    // Read original file
    const originalContent = fs.readFileSync(fullPath, 'utf-8');
    const backupPath = path.join(this.backupDir, path.basename(filePath));
    fs.writeFileSync(backupPath, originalContent);

    console.log(`  📝 Creating mutations for ${path.basename(filePath)}`);
    
    // Apply each mutation type
    for (const [mutationType, mutations] of Object.entries(MUTATIONS)) {
      for (const mutation of mutations) {
        if (originalContent.includes(mutation.from)) {
          await this.testMutation(filePath, originalContent, mutation, mutationType);
        }
      }
    }

    // Restore original file
    fs.writeFileSync(fullPath, originalContent);
  }

  async testMutation(filePath, originalContent, mutation, mutationType) {
    const fullPath = path.join(__dirname, '..', filePath);
    this.results.totalMutations++;

    try {
      // Apply mutation
      let mutatedContent = originalContent.replace(
        new RegExp(this.escapeRegExp(mutation.from), 'g'), 
        mutation.to
      );

      // Write mutated file
      fs.writeFileSync(fullPath, mutatedContent);

      // Run tests
      const testResult = await this.runTests(filePath);
      
      if (testResult.success) {
        // Mutation survived - tests didn't catch it
        this.results.survivedMutations++;
        console.log(`  ❌ SURVIVED: ${mutation.description} in ${path.basename(filePath)}`);
        
        this.results.details.push({
          file: filePath,
          mutation: mutation.description,
          type: mutationType,
          status: 'survived',
          line: this.findMutationLine(originalContent, mutation.from),
          impact: 'Test gap detected - mutation not caught'
        });
      } else if (testResult.timeout) {
        this.results.timeoutMutations++;
        console.log(`  ⏱️  TIMEOUT: ${mutation.description} in ${path.basename(filePath)}`);
        
        this.results.details.push({
          file: filePath,
          mutation: mutation.description,
          type: mutationType,
          status: 'timeout',
          impact: 'Mutation caused infinite loop or severe performance regression'
        });
      } else {
        // Mutation killed - tests caught it
        this.results.killedMutations++;
        console.log(`  ✅ KILLED: ${mutation.description} in ${path.basename(filePath)}`);
        
        this.results.details.push({
          file: filePath,
          mutation: mutation.description,
          type: mutationType,
          status: 'killed',
          impact: 'Test successfully caught mutation'
        });
      }

    } catch (error) {
      this.results.errorMutations++;
      console.log(`  💥 ERROR: ${mutation.description} in ${path.basename(filePath)} - ${error.message}`);
      
      this.results.details.push({
        file: filePath,
        mutation: mutation.description,
        type: mutationType,
        status: 'error',
        impact: 'Mutation caused compilation/runtime error'
      });
    }
  }

  async runTests(filePath) {
    return new Promise((resolve) => {
      const testCommand = 'pnpm';
      const testArgs = ['test:unit', '--passWithNoTests', '--silent'];
      
      // Add specific test file if it exists
      const testFile = filePath.replace('/src/', '/__tests__/').replace('.tsx', '.test.tsx').replace('.ts', '.test.ts');
      if (fs.existsSync(path.join(__dirname, '..', testFile))) {
        testArgs.push(testFile);
      }

      const testProcess = spawn(testCommand, testArgs, {
        stdio: 'pipe',
        timeout: 30000, // 30 second timeout
        cwd: path.join(__dirname, '..')
      });

      let output = '';
      let errorOutput = '';

      testProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      testProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
      });

      testProcess.on('close', (code) => {
        resolve({
          success: code === 0,
          timeout: false,
          output,
          error: errorOutput
        });
      });

      testProcess.on('error', (error) => {
        if (error.code === 'ETIMEDOUT') {
          resolve({
            success: false,
            timeout: true,
            error: 'Test execution timed out'
          });
        } else {
          resolve({
            success: false,
            timeout: false,
            error: error.message
          });
        }
      });
    });
  }

  calculateMutationScore() {
    const validMutations = this.results.totalMutations - this.results.errorMutations;
    this.results.mutationScore = validMutations > 0 
      ? (this.results.killedMutations / validMutations) * 100 
      : 0;
  }

  generateReport() {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalMutations: this.results.totalMutations,
        killedMutations: this.results.killedMutations,
        survivedMutations: this.results.survivedMutations,
        timeoutMutations: this.results.timeoutMutations,
        errorMutations: this.results.errorMutations,
        mutationScore: Math.round(this.results.mutationScore * 100) / 100
      },
      thresholds: {
        excellent: 80,
        good: 60,
        acceptable: 40,
        poor: 0
      },
      details: this.results.details,
      recommendations: this.generateRecommendations()
    };

    // Write detailed report
    fs.writeFileSync(
      path.join(this.workingDir, 'mutation-report.json'),
      JSON.stringify(report, null, 2)
    );

    // Generate HTML report
    this.generateHtmlReport(report);

    // Console summary
    console.log('\n🧬 MUTATION TESTING RESULTS');
    console.log('=====================================');
    console.log(`📊 Mutation Score: ${report.summary.mutationScore}%`);
    console.log(`✅ Killed: ${report.summary.killedMutations}`);
    console.log(`❌ Survived: ${report.summary.survivedMutations}`);
    console.log(`⏱️  Timeout: ${report.summary.timeoutMutations}`);
    console.log(`💥 Errors: ${report.summary.errorMutations}`);
    console.log(`📁 Report: ${path.join(this.workingDir, 'mutation-report.html')}`);

    // Quality assessment
    if (report.summary.mutationScore >= 80) {
      console.log('🎉 EXCELLENT test quality!');
    } else if (report.summary.mutationScore >= 60) {
      console.log('👍 GOOD test quality');
    } else if (report.summary.mutationScore >= 40) {
      console.log('⚠️  ACCEPTABLE test quality - room for improvement');
    } else {
      console.log('🚨 POOR test quality - significant gaps detected');
    }
  }

  generateRecommendations() {
    const recommendations = [];
    
    if (this.results.survivedMutations > 0) {
      recommendations.push({
        type: 'test_gaps',
        priority: 'high',
        message: `${this.results.survivedMutations} mutations survived. Add tests for uncovered edge cases.`
      });
    }

    if (this.results.mutationScore < 60) {
      recommendations.push({
        type: 'coverage',
        priority: 'high',
        message: 'Mutation score below 60%. Focus on testing critical business logic and error conditions.'
      });
    }

    if (this.results.timeoutMutations > 0) {
      recommendations.push({
        type: 'performance',
        priority: 'medium',
        message: `${this.results.timeoutMutations} mutations caused timeouts. Review performance-critical code paths.`
      });
    }

    return recommendations;
  }

  generateHtmlReport(report) {
    const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Mutation Testing Report - DotMac Frontend</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
    h1 { color: #333; border-bottom: 3px solid #007acc; padding-bottom: 10px; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
    .metric { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007acc; }
    .metric-value { font-size: 2em; font-weight: bold; color: #007acc; }
    .metric-label { color: #666; margin-top: 5px; }
    .mutation-score { font-size: 3em; margin: 20px 0; text-align: center; }
    .excellent { color: #28a745; }
    .good { color: #17a2b8; }
    .acceptable { color: #ffc107; }
    .poor { color: #dc3545; }
    .details { margin-top: 40px; }
    .mutation-item { background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 4px solid #ddd; }
    .killed { border-left-color: #28a745; }
    .survived { border-left-color: #dc3545; }
    .timeout { border-left-color: #ffc107; }
    .error { border-left-color: #6c757d; }
    .recommendations { background: #e7f3ff; padding: 20px; border-radius: 8px; margin: 30px 0; }
    .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
    .killed-badge { background: #d4edda; color: #155724; }
    .survived-badge { background: #f8d7da; color: #721c24; }
    .timeout-badge { background: #fff3cd; color: #856404; }
    .error-badge { background: #d1ecf1; color: #0c5460; }
  </style>
</head>
<body>
  <div class="container">
    <h1>🧬 Mutation Testing Report</h1>
    <p><strong>Generated:</strong> ${report.timestamp}</p>
    
    <div class="mutation-score ${this.getScoreClass(report.summary.mutationScore)}">
      ${report.summary.mutationScore}%
    </div>
    <p style="text-align: center; color: #666; margin-top: -10px;">Mutation Score</p>
    
    <div class="summary">
      <div class="metric">
        <div class="metric-value">${report.summary.totalMutations}</div>
        <div class="metric-label">Total Mutations</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color: #28a745">${report.summary.killedMutations}</div>
        <div class="metric-label">Killed (Good)</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color: #dc3545">${report.summary.survivedMutations}</div>
        <div class="metric-label">Survived (Bad)</div>
      </div>
      <div class="metric">
        <div class="metric-value" style="color: #ffc107">${report.summary.timeoutMutations}</div>
        <div class="metric-label">Timeouts</div>
      </div>
    </div>

    ${report.recommendations.length > 0 ? `
    <div class="recommendations">
      <h3>🎯 Recommendations</h3>
      ${report.recommendations.map(rec => `
        <p><strong>${rec.priority.toUpperCase()}:</strong> ${rec.message}</p>
      `).join('')}
    </div>
    ` : ''}

    <div class="details">
      <h3>📋 Mutation Details</h3>
      ${report.details.map(detail => `
        <div class="mutation-item ${detail.status}">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong>${detail.file.split('/').pop()}</strong> - ${detail.mutation}
              <div style="color: #666; font-size: 0.9em;">${detail.impact}</div>
            </div>
            <span class="status-badge ${detail.status}-badge">${detail.status.toUpperCase()}</span>
          </div>
        </div>
      `).join('')}
    </div>
  </div>
</body>
</html>`;

    fs.writeFileSync(path.join(this.workingDir, 'mutation-report.html'), html);
  }

  getScoreClass(score) {
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'acceptable';
    return 'poor';
  }

  findMutationLine(content, searchText) {
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes(searchText)) {
        return i + 1;
      }
    }
    return null;
  }

  escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  async cleanup() {
    // Restore all original files from backups
    const backupFiles = fs.readdirSync(this.backupDir);
    for (const backupFile of backupFiles) {
      const backupPath = path.join(this.backupDir, backupFile);
      const originalPath = MUTATION_TARGETS.find(target => 
        target.includes(backupFile)
      );
      
      if (originalPath) {
        const fullOriginalPath = path.join(__dirname, '..', originalPath);
        const backupContent = fs.readFileSync(backupPath, 'utf-8');
        fs.writeFileSync(fullOriginalPath, backupContent);
      }
    }
    
    console.log('🧹 Cleanup completed - all files restored');
  }
}

// Main execution
async function main() {
  const mutationTester = new MutationTester();
  
  try {
    await mutationTester.setup();
    await mutationTester.runMutationTesting();
  } catch (error) {
    console.error('❌ Mutation testing failed:', error);
    process.exit(1);
  } finally {
    await mutationTester.cleanup();
  }
}

// Handle script termination
process.on('SIGINT', async () => {
  console.log('\n⚠️  Mutation testing interrupted. Cleaning up...');
  const mutationTester = new MutationTester();
  await mutationTester.cleanup();
  process.exit(0);
});

if (require.main === module) {
  main();
}

module.exports = { MutationTester };