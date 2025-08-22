/**
 * Documentation Page Component
 * 
 * Comprehensive documentation and guides for the platform
 */
import React from 'react';
import { LandingLayout } from '../layouts/LandingLayout';
import { BookOpenIcon, CodeBracketIcon, RocketLaunchIcon, CogIcon } from '@heroicons/react/24/outline';

export const DocumentationPage: React.FC = () => {
  return (
    <LandingLayout>
      {/* Hero Section */}
      <section className="py-24 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-neutral-900 dark:via-neutral-800 dark:to-purple-900/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-neutral-900 dark:text-white mb-6">
            Documentation
            <br />
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              & Guides
            </span>
          </h1>
          <p className="text-xl text-neutral-600 dark:text-neutral-300 max-w-3xl mx-auto mb-12">
            Everything you need to build, integrate, and deploy intelligent AI assistants with our platform.
          </p>
        </div>
      </section>

      {/* Quick Start Guide */}
      <section className="py-24 bg-white dark:bg-neutral-900">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
              Quick Start Guide
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Get up and running in minutes with our step-by-step guide
            </p>
          </div>

          <div className="space-y-12">
            {/* Step 1 */}
            <div className="flex items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center text-white font-bold text-lg mr-6">
                1
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                  Create Your Account
                </h3>
                <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                  Sign up for a free account to get started. No credit card required for the starter plan.
                </p>
                <div className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-4">
                  <code className="text-sm text-neutral-700 dark:text-neutral-300">
                    Visit /register and create your account
                  </code>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-lg mr-6">
                2
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                  Create Your First Bot
                </h3>
                <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                  Set up your first AI assistant by choosing a name, description, and AI provider.
                </p>
                <div className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-4">
                  <code className="text-sm text-neutral-700 dark:text-neutral-300">
                    Dashboard → Create Bot → Configure settings
                  </code>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center text-white font-bold text-lg mr-6">
                3
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                  Upload Documents
                </h3>
                <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                  Upload your knowledge base documents (PDFs, Word docs, text files) to train your bot.
                </p>
                <div className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-4">
                  <code className="text-sm text-neutral-700 dark:text-neutral-300">
                    Bot Settings → Documents → Upload Files
                  </code>
                </div>
              </div>
            </div>

            {/* Step 4 */}
            <div className="flex items-start">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center text-white font-bold text-lg mr-6">
                4
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                  Start Chatting
                </h3>
                <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                  Test your bot by starting a conversation and see how it responds to questions about your documents.
                </p>
                <div className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-4">
                  <code className="text-sm text-neutral-700 dark:text-neutral-300">
                    Bot Dashboard → Chat → Start conversation
                  </code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Documentation Categories */}
      <section className="py-24 bg-neutral-50 dark:bg-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
              Explore Documentation
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Find detailed guides and references for every aspect of the platform
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm hover:shadow-lg transition-all duration-300 group cursor-pointer">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <BookOpenIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                Getting Started
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Learn the basics and get your first bot up and running quickly.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li>• Account setup</li>
                <li>• Bot creation</li>
                <li>• Document upload</li>
                <li>• Basic configuration</li>
              </ul>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm hover:shadow-lg transition-all duration-300 group cursor-pointer">
              <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <CodeBracketIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                API Reference
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Complete API documentation with examples and code samples.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li>• REST API endpoints</li>
                <li>• Authentication</li>
                <li>• Request/Response formats</li>
                <li>• Rate limits</li>
              </ul>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm hover:shadow-lg transition-all duration-300 group cursor-pointer">
              <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <RocketLaunchIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                Integration Guides
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Learn how to integrate bots into your applications and workflows.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li>• JavaScript SDK</li>
                <li>• Embed widgets</li>
                <li>• Webhook setup</li>
                <li>• Platform integrations</li>
              </ul>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm hover:shadow-lg transition-all duration-300 group cursor-pointer">
              <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <CogIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-3">
                Advanced Features
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Explore advanced configuration options and customization features.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li>• Custom workflows</li>
                <li>• Team collaboration</li>
                <li>• Analytics setup</li>
                <li>• Security settings</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Code Example */}
      <section className="py-24 bg-white dark:bg-neutral-900">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
              Quick Integration Example
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Get started with just a few lines of code
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h3 className="text-2xl font-semibold text-neutral-900 dark:text-white mb-6">
                JavaScript SDK
              </h3>
              <div className="space-y-4">
                <div className="flex items-start">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mr-4">
                    <span className="text-blue-600 dark:text-blue-400 text-sm font-semibold">1</span>
                  </div>
                  <div>
                    <p className="text-neutral-700 dark:text-neutral-300 font-medium">Install the SDK</p>
                    <code className="text-sm text-neutral-600 dark:text-neutral-400">npm install @multirag/sdk</code>
                  </div>
                </div>
                <div className="flex items-start">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mr-4">
                    <span className="text-blue-600 dark:text-blue-400 text-sm font-semibold">2</span>
                  </div>
                  <div>
                    <p className="text-neutral-700 dark:text-neutral-300 font-medium">Initialize your bot</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Create a bot instance with your API key</p>
                  </div>
                </div>
                <div className="flex items-start">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center mr-4">
                    <span className="text-blue-600 dark:text-blue-400 text-sm font-semibold">3</span>
                  </div>
                  <div>
                    <p className="text-neutral-700 dark:text-neutral-300 font-medium">Start chatting</p>
                    <p className="text-sm text-neutral-600 dark:text-neutral-400">Send messages and receive responses</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-neutral-900 dark:bg-neutral-800 rounded-2xl p-8 shadow-xl">
              <div className="flex items-center mb-6">
                <div className="flex space-x-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                </div>
                <span className="ml-4 text-neutral-400 text-sm">example.js</span>
              </div>
              <pre className="text-green-400 text-sm overflow-x-auto">
                <code>{`import { MultiRAGBot } from '@multirag/sdk';

// Initialize the bot
const bot = new MultiRAGBot({
  apiKey: 'your-api-key',
  botId: 'your-bot-id'
});

// Send a message
const response = await bot.chat({
  message: "What's in my knowledge base?",
  sessionId: "user-123"
});

console.log(response.message);
// Bot's response based on your documents

// Stream responses for real-time chat
bot.streamChat({
  message: "Tell me more about...",
  sessionId: "user-123",
  onMessage: (chunk) => {
    console.log(chunk.content);
  }
});`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Support Section */}
      <section className="py-24 bg-gradient-to-br from-blue-600 via-purple-600 to-blue-800 text-white">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Need Help?
          </h2>
          <p className="text-xl text-blue-100 mb-12 max-w-2xl mx-auto">
            Our team is here to help you succeed. Get support, ask questions, or request new features.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-3">Community Forum</h3>
              <p className="text-blue-100 mb-4">Join our community to ask questions and share knowledge</p>
              <a href="#" className="text-white hover:text-blue-200 underline">Visit Forum</a>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-3">Email Support</h3>
              <p className="text-blue-100 mb-4">Get direct help from our support team</p>
              <a href="mailto:support@multirag.com" className="text-white hover:text-blue-200 underline">support@multirag.com</a>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-3">Video Tutorials</h3>
              <p className="text-blue-100 mb-4">Watch step-by-step video guides and tutorials</p>
              <a href="#" className="text-white hover:text-blue-200 underline">Watch Videos</a>
            </div>
          </div>
        </div>
      </section>
    </LandingLayout>
  );
};

export default DocumentationPage;
