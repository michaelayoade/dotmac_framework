#!/usr/bin/env node

/**
 * Generate SRI hashes for external resources at build time
 * This script should be run during the build process
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const https = require('https');

// External resources to generate SRI hashes for
const EXTERNAL_RESOURCES = [
  {
    name: 'googleFontsInter',
    url: 'https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;400;500;600;700;800;900&display=swap',
    type: 'stylesheet',
  },
  // Add more external resources as needed
];

/**
 * Fetch content from URL
 */
function fetchContent(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          resolve(data);
        });
      })
      .on('error', (err) => {
        reject(err);
      });
  });
}

/**
 * Generate SRI hash for content
 */
function generateSRIHash(content, algorithm = 'sha384') {
  const hash = crypto.createHash(algorithm);
  hash.update(content);
  const digest = hash.digest('base64');
  return `${algorithm}-${digest}`;
}

/**
 * Generate SRI manifest
 */
async function generateSRIManifest() {
  const manifest = {};

  console.log('🔐 Generating SRI hashes for external resources...\n');

  for (const resource of EXTERNAL_RESOURCES) {
    try {
      console.log(`Fetching: ${resource.name}`);
      console.log(`  URL: ${resource.url}`);

      const content = await fetchContent(resource.url);
      const hash = generateSRIHash(content);

      manifest[resource.name] = {
        url: resource.url,
        type: resource.type,
        integrity: hash,
        crossorigin: 'anonymous',
      };

      console.log(`  ✅ Hash: ${hash.substring(0, 50)}...`);
      console.log('');
    } catch (error) {
      console.error(`  ❌ Failed to generate SRI for ${resource.name}:`, error.message);
      manifest[resource.name] = {
        url: resource.url,
        type: resource.type,
        integrity: null,
        error: error.message,
      };
    }
  }

  return manifest;
}

/**
 * Write manifest to file
 */
function writeManifest(manifest, outputPath) {
  const content = `/**
 * Auto-generated SRI hashes for external resources
 * Generated at: ${new Date().toISOString()}
 * DO NOT EDIT MANUALLY - Run 'pnpm generate:sri' to update
 */

export const SRI_MANIFEST = ${JSON.stringify(manifest, null, 2)} as const;

export type SRIResource = keyof typeof SRI_MANIFEST;
`;

  fs.writeFileSync(outputPath, content, 'utf-8');
  console.log(`\n✅ SRI manifest written to: ${outputPath}`);
}

/**
 * Main function
 */
async function main() {
  try {
    const manifest = await generateSRIManifest();

    // Write to multiple locations for different packages
    const outputPaths = [path.join(__dirname, '../packages/headless/src/utils/sri-manifest.ts')];

    for (const outputPath of outputPaths) {
      // Ensure directory exists
      const dir = path.dirname(outputPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      writeManifest(manifest, outputPath);
    }

    // Also write a JSON version for build tools
    const jsonPath = path.join(__dirname, '../sri-manifest.json');
    fs.writeFileSync(jsonPath, JSON.stringify(manifest, null, 2), 'utf-8');
    console.log(`✅ JSON manifest written to: ${jsonPath}`);

    console.log('\n🎉 SRI hash generation complete!');

    // Show summary
    const validCount = Object.values(manifest).filter((r) => r.integrity).length;
    const errorCount = Object.values(manifest).filter((r) => r.error).length;

    console.log(`\nSummary:`);
    console.log(`  Total resources: ${Object.keys(manifest).length}`);
    console.log(`  Valid hashes: ${validCount}`);
    if (errorCount > 0) {
      console.log(`  Errors: ${errorCount}`);
    }
  } catch (error) {
    console.error('Failed to generate SRI manifest:', error);
    process.exit(1);
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}

module.exports = { generateSRIManifest, generateSRIHash };
