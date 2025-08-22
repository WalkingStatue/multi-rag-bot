/**
 * Landing Page Component
 * 
 * Modern, attractive landing page with hero section, features, and call-to-action
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { LandingLayout } from '../layouts/LandingLayout';
import { ArrowRightIcon, SparklesIcon, ChatBubbleLeftRightIcon, DocumentTextIcon, UserGroupIcon, ShieldCheckIcon, BoltIcon } from '@heroicons/react/24/outline';

export const LandingPage: React.FC = () => {
  return (
    <LandingLayout>
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-neutral-900 dark:via-neutral-800 dark:to-purple-900/20">
        <div className="absolute inset-0 bg-grid-neutral-100 dark:bg-grid-neutral-800 [mask-image:linear-gradient(0deg,transparent,black)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-24 sm:pt-24 sm:pb-32">
          <div className="text-center">
            {/* Badge */}
            <div className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 mb-8">
              <SparklesIcon className="w-4 h-4 mr-2" />
              Powered by Advanced AI Technology
            </div>
            
            {/* Main Heading */}
            <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold tracking-tight mb-6">
              <span className="text-neutral-900 dark:text-white">Build Intelligent</span>
              <br />
              <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent">
                AI Assistants
              </span>
            </h1>
            
            {/* Subtitle */}
            <p className="text-xl sm:text-2xl text-neutral-600 dark:text-neutral-300 max-w-4xl mx-auto mb-12 leading-relaxed">
              Create powerful chatbots with Retrieval Augmented Generation (RAG). 
              Upload documents, train custom models, and deploy intelligent assistants that understand your data.
            </p>
            
            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/register"
                className="group inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
              >
                Start Building Free
                <ArrowRightIcon className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border-2 border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-md hover:shadow-lg transform hover:-translate-y-0.5 transition-all duration-200"
              >
                Sign In
              </Link>
            </div>
            
            {/* Trust Indicators */}
            <div className="mt-16 pt-8 border-t border-neutral-200 dark:border-neutral-700">
              <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
                Trusted by developers and teams worldwide
              </p>
              <div className="flex items-center justify-center gap-8 opacity-60 dark:opacity-40">
                <div className="text-2xl font-bold text-neutral-400">OpenAI</div>
                <div className="text-2xl font-bold text-neutral-400">Anthropic</div>
                <div className="text-2xl font-bold text-neutral-400">Google</div>
                <div className="text-2xl font-bold text-neutral-400">OpenRouter</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white dark:bg-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-neutral-900 dark:text-white mb-6">
              Everything you need to build
              <br />
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                powerful AI assistants
              </span>
            </h2>
            <p className="text-xl text-neutral-600 dark:text-neutral-400 max-w-3xl mx-auto">
              Our platform provides all the tools and features you need to create, train, and deploy intelligent chatbots that understand your specific content.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="group relative p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 hover:shadow-xl hover:border-blue-200 dark:hover:border-blue-800 transition-all duration-300">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <DocumentTextIcon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Document Intelligence
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                Upload PDFs, documents, and text files. Our AI automatically extracts, processes, and indexes your content for intelligent retrieval.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group relative p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 hover:shadow-xl hover:border-purple-200 dark:hover:border-purple-800 transition-all duration-300">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <ChatBubbleLeftRightIcon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Natural Conversations
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                Create chatbots that understand context and provide accurate, relevant responses based on your specific knowledge base.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group relative p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 hover:shadow-xl hover:border-green-200 dark:hover:border-green-800 transition-all duration-300">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <UserGroupIcon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Team Collaboration
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                Share bots with team members, manage permissions, and collaborate on building the perfect AI assistant for your needs.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="group relative p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 hover:shadow-xl hover:border-orange-200 dark:hover:border-orange-800 transition-all duration-300">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <BoltIcon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Multiple AI Providers
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                Choose from OpenAI, Anthropic, Google, and more. Switch between models and find the perfect AI for your use case.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="group relative p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 hover:shadow-xl hover:border-red-200 dark:hover:border-red-800 transition-all duration-300">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <ShieldCheckIcon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Secure & Private
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                Your data stays secure with enterprise-grade encryption. Control access and maintain privacy while building powerful AI tools.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="group relative p-8 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-gradient-to-b from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-800 hover:shadow-xl hover:border-indigo-200 dark:hover:border-indigo-800 transition-all duration-300">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                <SparklesIcon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Easy Integration
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                Deploy your bots anywhere with our simple API, embed widgets, or use our pre-built integrations for popular platforms.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-blue-600 via-purple-600 to-blue-800 text-white">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to build your first AI assistant?
          </h2>
          <p className="text-xl text-blue-100 mb-12 max-w-2xl mx-auto">
            Join thousands of developers and teams who are already building intelligent chatbots with our platform. Start your free trial today.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
              to="/register"
              className="group inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-blue-600 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              Start Free Trial
              <ArrowRightIcon className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
            </Link>
            <Link
              to="/docs"
              className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-white border-2 border-white/20 hover:border-white/40 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white transition-all duration-200"
            >
              View Documentation
            </Link>
          </div>
        </div>
      </section>
    </LandingLayout>
  );
};

export default LandingPage;
