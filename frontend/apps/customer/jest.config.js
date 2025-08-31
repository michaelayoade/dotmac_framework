/**
 * Customer Portal Jest Configuration
 * Uses unified config with customer-specific overrides
 */

const { portalConfigs } = require('../../testing/jest.config.unified.js');

module.exports = {
  ...portalConfigs.customer(),
  
  // App-specific setup files
  setupFilesAfterEnv: [
    '<rootDir>/../../testing/setup/jest.setup.ts',
    '<rootDir>/jest-setup.js'
  ],
  
  // Next.js specific patterns
  testPathIgnorePatterns: [
    '<rootDir>/.next/',
    '<rootDir>/node_modules/',
    '<rootDir>/build/'
  ]
};
