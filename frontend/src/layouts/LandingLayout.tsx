/**
 * LandingLayout component
 * 
 * This layout is used for the landing page and other marketing pages.
 * It provides a clean layout with a simplified navigation.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import BaseLayout from './BaseLayout';
import { useTheme } from '../hooks/useTheme';

export interface LandingLayoutProps {
  children: React.ReactNode;
  className?: string;
  showNavigation?: boolean;
  showFooter?: boolean;
}

export const LandingLayout: React.FC<LandingLayoutProps> = ({
  children,
  className = '',
  showNavigation = true,
  showFooter = true,
}) => {
  const { isDark, toggleTheme } = useTheme();

  return (
    <BaseLayout className={`flex flex-col min-h-screen ${className}`}>
      {/* Simplified Navigation */}
      {showNavigation && (
        <header className="bg-white/80 dark:bg-neutral-900/70 backdrop-blur supports-[backdrop-filter]:bg-white/60 shadow transition-colors duration-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              {/* Logo and Brand */}
              <div className="flex items-center">
                <Link to="/" className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                      Multi-Bot RAG Platform
                    </h1>
                  </div>
                </Link>
              </div>

              {/* Navigation Links */}
              <div className="hidden md:flex md:items-center md:space-x-6">
                <Link
                  to="/features"
                  className="text-neutral-600 hover:text-neutral-900 dark:text-neutral-300 dark:hover:text-neutral-100 px-3 py-2 text-sm font-medium"
                >
                  Features
                </Link>
                <Link
                  to="/pricing"
                  className="text-neutral-600 hover:text-neutral-900 dark:text-neutral-300 dark:hover:text-neutral-100 px-3 py-2 text-sm font-medium"
                >
                  Pricing
                </Link>
                <Link
                  to="/docs"
                  className="text-neutral-600 hover:text-neutral-900 dark:text-neutral-300 dark:hover:text-neutral-100 px-3 py-2 text-sm font-medium"
                >
                  Documentation
                </Link>
                
                {/* Theme toggle */}
                <button
                  onClick={toggleTheme}
                  className="rounded-md p-2 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800"
                  aria-label="Toggle theme"
                  title="Toggle theme"
                >
                  {isDark ? (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path d="M17.293 13.293A8 8 0 016.707 2.707 8.001 8.001 0 1017.293 13.293z"/></svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-4 7a1 1 0 011-1h0a1 1 0 110 2h0a1 1 0 01-1-1zM4.222 4.222a1 1 0 011.415 0l.707.707a1 1 0 01-1.414 1.415l-.708-.708a1 1 0 010-1.414zM16.97 16.97a1 1 0 01-1.415 0l-.707-.707a1 1 0 011.414-1.415l.708.708a1 1 0 010 1.414zM2 11a1 1 0 100-2h-1a1 1 0 100 2h1zm18 0a1 1 0 100-2h-1a1 1 0 100 2h1zM4.222 15.778a1 1 0 010-1.415l.708-.707a1 1 0 111.414 1.414l-.707.708a1 1 0 01-1.415 0zM15.778 4.222a1 1 0 00-1.415 0l-.707.708a1 1 0 101.414 1.414l.708-.707a1 1 0 000-1.415z" clipRule="evenodd"/></svg>
                  )}
                </button>

                {/* Auth Buttons */}
                <div className="flex items-center space-x-2">
                  <Link
                    to="/login"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-primary-700 bg-primary-50 hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:bg-primary-900/30 dark:text-primary-300 dark:hover:bg-primary-900/50"
                  >
                    Sign in
                  </Link>
                  <Link
                    to="/register"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    Sign up
                  </Link>
                </div>
              </div>

              {/* Mobile menu button */}
              <div className="md:hidden flex items-center">
                <button
                  className="inline-flex items-center justify-center p-2 rounded-md text-neutral-400 hover:text-neutral-500 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800"
                >
                  <span className="sr-only">Open main menu</span>
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </header>
      )}

      {/* Main Content */}
      <main className="flex-grow">
        {children}
      </main>

      {/* Footer */}
      {showFooter && (
        <footer className="bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800">
          <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
              <div className="col-span-1 md:col-span-2">
                <div className="flex items-center">
                  <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  <h2 className="ml-3 text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                    Multi-Bot RAG Platform
                  </h2>
                </div>
                <p className="mt-4 text-neutral-600 dark:text-neutral-400">
                  Build powerful AI assistants with Retrieval Augmented Generation.
                </p>
              </div>
              
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 tracking-wider uppercase">
                  Product
                </h3>
                <ul className="mt-4 space-y-4">
                  <li>
                    <Link to="/features" className="text-base text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
                      Features
                    </Link>
                  </li>
                  <li>
                    <Link to="/pricing" className="text-base text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
                      Pricing
                    </Link>
                  </li>
                  <li>
                    <Link to="/docs" className="text-base text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
                      Documentation
                    </Link>
                  </li>
                </ul>
              </div>
              
              <div>
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100 tracking-wider uppercase">
                  Company
                </h3>
                <ul className="mt-4 space-y-4">
                  <li>
                    <Link to="/about" className="text-base text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
                      About
                    </Link>
                  </li>
                  <li>
                    <Link to="/contact" className="text-base text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
                      Contact
                    </Link>
                  </li>
                  <li>
                    <Link to="/privacy" className="text-base text-neutral-600 hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100">
                      Privacy
                    </Link>
                  </li>
                </ul>
              </div>
            </div>
            
            <div className="mt-12 border-t border-neutral-200 dark:border-neutral-800 pt-8">
              <p className="text-base text-neutral-500 dark:text-neutral-400">
                &copy; {new Date().getFullYear()} Multi-Bot RAG Platform. All rights reserved.
              </p>
            </div>
          </div>
        </footer>
      )}
    </BaseLayout>
  );
};

export default LandingLayout;