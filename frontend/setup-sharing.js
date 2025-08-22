#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

/**
 * Quick setup script for sharing the app with colleagues
 */

async function getPublicIP() {
  try {
    const { default: fetch } = await import('node-fetch');
    const response = await fetch('http://ifconfig.me/ip');
    return (await response.text()).trim();
  } catch (error) {
    console.log('⚠️  Could not fetch public IP automatically.');
    console.log('Please check your internet connection or use ngrok instead.');
    return null;
  }
}

function updateSharedEnv(ip) {
  const envPath = path.join(__dirname, '.env.shared');
  const content = `# Shared development configuration for port forwarding
VITE_API_URL=http://${ip}:8000
VITE_WS_URL=ws://${ip}:8000
`;
  
  fs.writeFileSync(envPath, content);
  console.log(`✅ Updated .env.shared with IP: ${ip}`);
}

function printInstructions(ip) {
  console.log('\n🚀 Setup Complete!\n');
  console.log('📋 Next Steps:');
  console.log('1. Make sure your router forwards ports 3000 and 8000 to this machine');
  console.log('2. Start your backend server (should be accessible on port 8000)');
  console.log('3. Run: npm run dev:shared');
  console.log(`4. Share this URL with your colleague: http://${ip}:3000`);
  console.log('\n🔧 Alternative: Use ngrok for easier setup');
  console.log('   npx ngrok http 8000  # Backend');
  console.log('   npx ngrok http 3000  # Frontend');
  console.log('   Then update .env.shared with the ngrok URLs');
  console.log('\n📚 For more details, see DEVELOPMENT.md');
}

async function main() {
  console.log('🔧 Setting up app sharing...\n');
  
  const ip = await getPublicIP();
  
  if (ip) {
    updateSharedEnv(ip);
    printInstructions(ip);
  } else {
    console.log('\n❌ Could not setup automatically.');
    console.log('Please manually update .env.shared with your public IP or use ngrok.');
    console.log('See DEVELOPMENT.md for detailed instructions.');
  }
}

if (require.main === module) {
  main().catch(console.error);
}
