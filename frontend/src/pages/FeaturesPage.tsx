/**
 * Features Page Component
 * 
 * Comprehensive page showcasing platform features and capabilities
 */
import React from 'react';
import { LandingLayout } from '../layouts/LandingLayout';
import { 
  DocumentTextIcon, 
  ChatBubbleLeftRightIcon, 
  UserGroupIcon, 
  ShieldCheckIcon, 
  BoltIcon, 
  SparklesIcon,
  CloudArrowUpIcon,
  CogIcon,
  ChartBarIcon,
  GlobeAltIcon,
  CodeBracketIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

export const FeaturesPage: React.FC = () => {
  return (
    <LandingLayout>
      {/* Hero Section */}
      <section className="py-24 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-neutral-900 dark:via-neutral-800 dark:to-purple-900/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-neutral-900 dark:text-white mb-6">
            Powerful Features for
            <br />
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Intelligent AI Assistants
            </span>
          </h1>
          <p className="text-xl text-neutral-600 dark:text-neutral-300 max-w-3xl mx-auto mb-12">
            Everything you need to build, deploy, and scale AI-powered chatbots that understand your content and deliver exceptional user experiences.
          </p>
        </div>
      </section>

      {/* Core Features Grid */}
      <section className="py-24 bg-white dark:bg-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
              Core Features
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
              Built with cutting-edge technology to provide the most advanced RAG capabilities
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Document Intelligence */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl hover:border-blue-200 dark:hover:border-blue-800 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <DocumentTextIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Smart Document Processing
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Upload PDFs, Word docs, text files, and more. Our AI automatically extracts, chunks, and indexes content for optimal retrieval.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />PDF text extraction</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />OCR for scanned documents</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Smart chunking algorithms</li>
              </ul>
            </div>

            {/* Natural Conversations */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl hover:border-purple-200 dark:hover:border-purple-800 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <ChatBubbleLeftRightIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Context-Aware Conversations
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Build chatbots that maintain context, understand intent, and provide accurate responses based on your knowledge base.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Multi-turn conversations</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Context preservation</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Intent recognition</li>
              </ul>
            </div>

            {/* Multiple AI Providers */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl hover:border-orange-200 dark:hover:border-orange-800 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <BoltIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Multiple AI Providers
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Choose from leading AI providers including OpenAI, Anthropic, Google, and OpenRouter. Switch models with ease.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />OpenAI GPT models</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Anthropic Claude</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Google Gemini</li>
              </ul>
            </div>

            {/* Team Collaboration */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl hover:border-green-200 dark:hover:border-green-800 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <UserGroupIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Team Collaboration
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Share bots with team members, manage permissions, and collaborate on building the perfect AI assistant.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Role-based permissions</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Team workspaces</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Collaborative editing</li>
              </ul>
            </div>

            {/* Security & Privacy */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl hover:border-red-200 dark:hover:border-red-800 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <ShieldCheckIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Enterprise Security
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Your data stays secure with enterprise-grade encryption, access controls, and compliance features.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />End-to-end encryption</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />SOC 2 compliance</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />GDPR compliant</li>
              </ul>
            </div>

            {/* Easy Integration */}
            <div className="group relative p-8 rounded-2xl bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl hover:border-indigo-200 dark:hover:border-indigo-800 transition-all duration-300">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <SparklesIcon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Easy Integration
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">
                Deploy your bots anywhere with our REST API, JavaScript SDK, or embed widgets for popular platforms.
              </p>
              <ul className="space-y-2 text-sm text-neutral-600 dark:text-neutral-400">
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />REST API</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />JavaScript SDK</li>
                <li className="flex items-center"><CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />Embed widgets</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Advanced Features */}
      <section className="py-24 bg-neutral-50 dark:bg-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
              Advanced Capabilities
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400 max-w-2xl mx-auto">
              Professional features for enterprise-grade AI applications
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mx-auto mb-6">
                <CloudArrowUpIcon className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">
                Auto-scaling Infrastructure
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Handle millions of conversations with automatic scaling and load balancing.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mx-auto mb-6">
                <CogIcon className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">
                Custom Workflows
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Build complex conversation flows with conditional logic and integrations.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center mx-auto mb-6">
                <ChartBarIcon className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">
                Analytics & Insights
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Track performance, user satisfaction, and optimize your AI assistants.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center mx-auto mb-6">
                <GlobeAltIcon className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-3">
                Multi-language Support
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Build bots that understand and respond in 50+ languages worldwide.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Developer Features */}
      <section className="py-24 bg-white dark:bg-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
                Built for Developers
              </h2>
              <p className="text-lg text-neutral-600 dark:text-neutral-400 mb-8">
                Powerful APIs, SDKs, and tools to integrate AI capabilities into any application.
              </p>
              
              <div className="space-y-6">
                <div className="flex items-start">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                    <CodeBracketIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
                      Comprehensive API
                    </h3>
                    <p className="text-neutral-600 dark:text-neutral-400">
                      RESTful API with detailed documentation, rate limiting, and webhook support.
                    </p>
                  </div>
                </div>

                <div className="flex items-start">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                    <SparklesIcon className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
                      JavaScript SDK
                    </h3>
                    <p className="text-neutral-600 dark:text-neutral-400">
                      Easy-to-use SDK for web applications with TypeScript support and React components.
                    </p>
                  </div>
                </div>

                <div className="flex items-start">
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                    <GlobeAltIcon className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
                      Embed Anywhere
                    </h3>
                    <p className="text-neutral-600 dark:text-neutral-400">
                      Pre-built widgets and components for websites, mobile apps, and popular platforms.
                    </p>
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
                <span className="ml-4 text-neutral-400 text-sm">main.js</span>
              </div>
              <pre className="text-green-400 text-sm overflow-x-auto">
                <code>{`import { MultiRAGBot } from '@multirag/sdk';

const bot = new MultiRAGBot({
  apiKey: 'your-api-key',
  botId: 'your-bot-id'
});

// Start a conversation
const response = await bot.chat({
  message: "How do I integrate this API?",
  sessionId: "user-session-123"
});

console.log(response.message);
// "You can integrate using our REST API..."`}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>
    </LandingLayout>
  );
};

export default FeaturesPage;
