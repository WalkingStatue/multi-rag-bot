/**
 * Pricing Page Component
 * 
 * Pricing tiers and plans for the platform
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { LandingLayout } from '../layouts/LandingLayout';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';

export const PricingPage: React.FC = () => {
  const plans = [
    {
      name: 'Starter',
      price: 'Free',
      description: 'Perfect for getting started with AI assistants',
      features: [
        '1 AI Bot',
        '100 messages/month',
        '10MB document storage',
        'Basic integrations',
        'Community support',
        'Standard AI models'
      ],
      limitations: [
        'Advanced analytics',
        'Team collaboration',
        'Custom branding',
        'Priority support',
        'Premium AI models'
      ],
      ctaText: 'Get Started Free',
      ctaLink: '/register',
      popular: false,
      color: 'gray'
    },
    {
      name: 'Pro',
      price: '$29',
      period: '/month',
      description: 'For professionals and small teams',
      features: [
        '10 AI Bots',
        '10,000 messages/month',
        '1GB document storage',
        'Advanced integrations',
        'Email support',
        'All AI models',
        'Basic analytics',
        'Team collaboration (5 members)',
        'Custom branding'
      ],
      limitations: [
        'Advanced workflows',
        'Priority support',
        'Dedicated account manager'
      ],
      ctaText: 'Start Pro Trial',
      ctaLink: '/register?plan=pro',
      popular: true,
      color: 'blue'
    },
    {
      name: 'Enterprise',
      price: '$99',
      period: '/month',
      description: 'For large teams and organizations',
      features: [
        'Unlimited AI Bots',
        '100,000 messages/month',
        '10GB document storage',
        'All integrations',
        'Priority support',
        'All AI models',
        'Advanced analytics',
        'Unlimited team members',
        'Custom branding',
        'Advanced workflows',
        'Dedicated account manager',
        'SLA guarantee',
        'Custom integrations'
      ],
      limitations: [],
      ctaText: 'Contact Sales',
      ctaLink: '/contact',
      popular: false,
      color: 'purple'
    }
  ];

  return (
    <LandingLayout>
      {/* Hero Section */}
      <section className="py-24 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-neutral-900 dark:via-neutral-800 dark:to-purple-900/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-neutral-900 dark:text-white mb-6">
            Simple, Transparent
            <br />
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Pricing
            </span>
          </h1>
          <p className="text-xl text-neutral-600 dark:text-neutral-300 max-w-3xl mx-auto mb-12">
            Choose the perfect plan for your needs. Start free, upgrade as you grow. No hidden fees, no surprises.
          </p>
          
          {/* Billing Toggle */}
          <div className="flex items-center justify-center mb-16">
            <span className="text-neutral-600 dark:text-neutral-400 mr-3">Monthly</span>
            <div className="relative">
              <input type="checkbox" id="billing-toggle" className="sr-only" />
              <label htmlFor="billing-toggle" className="flex items-center cursor-pointer">
                <div className="w-14 h-8 bg-neutral-200 dark:bg-neutral-700 rounded-full shadow-inner"></div>
                <div className="absolute left-1 top-1 bg-white w-6 h-6 rounded-full shadow transform transition-transform duration-300"></div>
              </label>
            </div>
            <span className="text-neutral-600 dark:text-neutral-400 ml-3">
              Yearly 
              <span className="ml-2 px-2 py-1 text-xs font-semibold bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                Save 20%
              </span>
            </span>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 bg-white dark:bg-neutral-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
            {plans.map((plan, index) => (
              <div 
                key={plan.name}
                className={`relative rounded-3xl p-8 shadow-lg border-2 transition-all duration-300 hover:shadow-xl ${
                  plan.popular 
                    ? 'border-blue-500 dark:border-blue-400 scale-105 bg-gradient-to-b from-blue-50 to-white dark:from-blue-900/20 dark:to-neutral-900' 
                    : 'border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 hover:border-neutral-300 dark:hover:border-neutral-700'
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-2 rounded-full text-sm font-semibold shadow-lg">
                      Most Popular
                    </span>
                  </div>
                )}
                
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-neutral-900 dark:text-white mb-2">
                    {plan.name}
                  </h3>
                  <p className="text-neutral-600 dark:text-neutral-400 mb-6">
                    {plan.description}
                  </p>
                  <div className="flex items-baseline justify-center">
                    <span className="text-5xl font-bold text-neutral-900 dark:text-white">
                      {plan.price}
                    </span>
                    {plan.period && (
                      <span className="text-neutral-600 dark:text-neutral-400 ml-1">
                        {plan.period}
                      </span>
                    )}
                  </div>
                </div>

                <div className="space-y-4 mb-8">
                  {plan.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className="flex items-center">
                      <CheckIcon className="w-5 h-5 text-green-500 flex-shrink-0 mr-3" />
                      <span className="text-neutral-700 dark:text-neutral-300">
                        {feature}
                      </span>
                    </div>
                  ))}
                  {plan.limitations.map((limitation, limitationIndex) => (
                    <div key={limitationIndex} className="flex items-center opacity-50">
                      <XMarkIcon className="w-5 h-5 text-neutral-400 flex-shrink-0 mr-3" />
                      <span className="text-neutral-600 dark:text-neutral-400">
                        {limitation}
                      </span>
                    </div>
                  ))}
                </div>

                <Link
                  to={plan.ctaLink}
                  className={`block w-full text-center px-8 py-4 rounded-xl font-semibold transition-all duration-200 transform hover:-translate-y-0.5 ${
                    plan.popular
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl'
                      : 'bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 hover:bg-neutral-800 dark:hover:bg-neutral-100 shadow-md hover:shadow-lg'
                  }`}
                >
                  {plan.ctaText}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-24 bg-neutral-50 dark:bg-neutral-800">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-neutral-900 dark:text-white mb-6">
              Frequently Asked Questions
            </h2>
            <p className="text-lg text-neutral-600 dark:text-neutral-400">
              Got questions? We've got answers.
            </p>
          </div>

          <div className="space-y-8">
            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Can I change my plan at any time?
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Yes! You can upgrade, downgrade, or cancel your plan at any time. Changes take effect at your next billing cycle, and we'll prorate any differences.
              </p>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                What happens if I exceed my message limit?
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                We'll notify you when you're approaching your limit. You can upgrade your plan or purchase additional message credits. Your bots won't stop working, but additional usage will be billed at standard overage rates.
              </p>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Is there a free trial for paid plans?
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Yes! All paid plans come with a 14-day free trial. No credit card required to start. You can explore all features and decide if it's right for you.
              </p>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                Do you offer enterprise discounts?
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                Yes! We offer volume discounts for large organizations and custom pricing for enterprise needs. Contact our sales team to discuss your requirements.
              </p>
            </div>

            <div className="bg-white dark:bg-neutral-900 rounded-2xl p-8 shadow-sm">
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-white mb-4">
                What payment methods do you accept?
              </h3>
              <p className="text-neutral-600 dark:text-neutral-400">
                We accept all major credit cards (Visa, MasterCard, American Express), PayPal, and for enterprise customers, we can arrange invoice-based billing.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-blue-600 via-purple-600 to-blue-800 text-white">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Ready to get started?
          </h2>
          <p className="text-xl text-blue-100 mb-12 max-w-2xl mx-auto">
            Join thousands of developers and teams building intelligent AI assistants. Start your free trial today.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
              to="/register"
              className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-blue-600 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200"
            >
              Start Free Trial
            </Link>
            <Link
              to="/contact"
              className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-white border-2 border-white/20 hover:border-white/40 hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white transition-all duration-200"
            >
              Contact Sales
            </Link>
          </div>
        </div>
      </section>
    </LandingLayout>
  );
};

export default PricingPage;
