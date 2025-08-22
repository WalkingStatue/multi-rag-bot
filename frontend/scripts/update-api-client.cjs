#!/usr/bin/env node

/**
 * Script to replace apiClient with enhancedApiClient across the frontend codebase
 */

const fs = require('fs');
const path = require('path');

// Files to update - services that import apiClient
const filesToUpdate = [
  'src/services/authService.ts',
  'src/services/notificationService.ts',
  'src/services/chatService.ts',
  'src/services/botService.ts',
  'src/services/permissionService.ts',
  'src/services/apiKeyService.ts',
  'src/services/documentService.ts',
];

function updateFile(filePath) {
  try {
    console.log(`Updating ${filePath}...`);
    
    const fullPath = path.resolve(filePath);
    const content = fs.readFileSync(fullPath, 'utf8');
    
    let updatedContent = content;
    
    // Replace import statement
    updatedContent = updatedContent.replace(
      /import\s*{\s*apiClient\s*}\s*from\s*['"]\.\/(api|enhancedApi)['"];?/g,
      "import { enhancedApiClient } from './enhancedApi';"
    );
    
    // Replace usage - apiClient.method() -> enhancedApiClient.method()
    updatedContent = updatedContent.replace(/apiClient\./g, 'enhancedApiClient.');
    
    // Check if anything was changed
    if (content !== updatedContent) {
      fs.writeFileSync(fullPath, updatedContent);
      console.log(`✓ Updated ${filePath}`);
      return true;
    } else {
      console.log(`- No changes needed for ${filePath}`);
      return false;
    }
  } catch (error) {
    console.error(`✗ Failed to update ${filePath}:`, error.message);
    return false;
  }
}

// Update offlineAwareApi.ts to import enhancedApiClient instead
function updateOfflineAwareApi() {
  try {
    const filePath = 'src/services/offlineAwareApi.ts';
    console.log(`Updating ${filePath}...`);
    
    const fullPath = path.resolve(filePath);
    const content = fs.readFileSync(fullPath, 'utf8');
    
    let updatedContent = content;
    
    // Update the import and the client usage
    updatedContent = updatedContent.replace(
      /import\s*{\s*apiClient\s*}\s*from\s*['"]\.\/(api|enhancedApi)['"];?/g,
      "import { enhancedApiClient } from './enhancedApi';"
    );
    
    // Update the export lines to use enhancedApiClient 
    updatedContent = updatedContent.replace(
      /export\s*{\s*apiClient.*$/gm,
      '// Offline-aware enhanced API client exports\nexport const get = enhancedApiClient.get.bind(enhancedApiClient);\nexport const post = enhancedApiClient.post.bind(enhancedApiClient);\nexport const put = enhancedApiClient.put.bind(enhancedApiClient);\nexport const patch = enhancedApiClient.patch.bind(enhancedApiClient);\nexport const del = enhancedApiClient.delete.bind(enhancedApiClient);'
    );
    
    if (content !== updatedContent) {
      fs.writeFileSync(fullPath, updatedContent);
      console.log(`✓ Updated ${filePath}`);
      return true;
    } else {
      console.log(`- No changes needed for ${filePath}`);
      return false;
    }
  } catch (error) {
    console.error(`✗ Failed to update offlineAwareApi.ts:`, error.message);
    return false;
  }
}

// Main execution
console.log('🔄 Starting API client standardization...\n');

let totalUpdated = 0;

// Update service files
for (const file of filesToUpdate) {
  if (updateFile(file)) {
    totalUpdated++;
  }
}

// Update offlineAwareApi.ts
if (updateOfflineAwareApi()) {
  totalUpdated++;
}

console.log(`\n✅ API client standardization complete!`);
console.log(`📊 Updated ${totalUpdated} files`);
console.log(`\n📝 Summary of changes:`);
console.log(`  - Replaced 'apiClient' imports with 'enhancedApiClient'`);
console.log(`  - Updated all method calls to use enhancedApiClient`);
console.log(`  - Enhanced error handling and logging now active`);
console.log(`  - Retry logic now available for failed requests`);
console.log(`  - Request context tracking enabled`);
