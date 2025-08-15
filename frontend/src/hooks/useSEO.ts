import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { seoManager, SEOConfig } from '../utils/seo';
import { logger } from '../utils/logger';

/**
 * Hook for managing SEO configuration for a page or component
 */
export function useSEO(config: Partial<SEOConfig>) {
  const location = useLocation();
  const previousConfig = useRef<Partial<SEOConfig> | null>(null);

  useEffect(() => {
    try {
      // Update SEO configuration
      seoManager.updateSEO(config);
      previousConfig.current = config;

      logger.debug('SEO updated', 'SEO', {
        path: location.pathname,
        title: config.title,
        description: config.description,
      });
    } catch (error) {
      logger.error('Failed to update SEO', 'SEO', error);
    }

    // Cleanup function to reset to defaults when component unmounts
    return () => {
      if (previousConfig.current) {
        try {
          seoManager.reset();
          logger.debug('SEO reset to defaults');
        } catch (error) {
          logger.error('Failed to reset SEO', 'SEO', error);
        }
      }
    };
  }, [config, location.pathname]);
}

/**
 * Hook for managing dynamic SEO based on data
 */
export function useDynamicSEO<T>(
  data: T | undefined,
  configGenerator: (data: T) => Partial<SEOConfig>,
  fallbackConfig?: Partial<SEOConfig>
) {
  const location = useLocation();

  useEffect(() => {
    try {
      if (data) {
        const config = configGenerator(data);
        seoManager.updateSEO(config);
        
        logger.debug('Dynamic SEO updated', 'SEO', {
          path: location.pathname,
          title: config.title,
          hasData: true,
        });
      } else if (fallbackConfig) {
        seoManager.updateSEO(fallbackConfig);
        
        logger.debug('Fallback SEO applied', 'SEO', {
          path: location.pathname,
          title: fallbackConfig.title,
          hasData: false,
        });
      }
    } catch (error) {
      logger.error('Failed to update dynamic SEO', 'SEO', error);
    }
  }, [data, configGenerator, fallbackConfig, location.pathname]);
}

/**
 * Hook for managing breadcrumb SEO
 */
export function useBreadcrumbSEO(breadcrumbs: Array<{ name: string; url: string }>) {
  useEffect(() => {
    try {
      if (breadcrumbs.length > 0) {
        const jsonLd = seoManager.generateBreadcrumbJsonLd(breadcrumbs);
        seoManager.updateSEO({ jsonLd });
        
        logger.debug('Breadcrumb SEO updated', 'SEO', {
          breadcrumbCount: breadcrumbs.length,
        });
      }
    } catch (error) {
      logger.error('Failed to update breadcrumb SEO', 'SEO', error);
    }
  }, [breadcrumbs]);
}

/**
 * Hook for managing article SEO
 */
export function useArticleSEO(article: {
  title: string;
  description: string;
  author: string;
  publishedDate: string;
  modifiedDate?: string;
  image?: string;
  tags?: string[];
}) {
  const location = useLocation();

  useEffect(() => {
    try {
      const articleJsonLd = seoManager.generateArticleJsonLd({
        headline: article.title,
        description: article.description,
        author: article.author,
        datePublished: article.publishedDate,
        ...(article.modifiedDate && { dateModified: article.modifiedDate }),
        ...(article.image && { image: article.image }),
        url: window.location.href,
      });

      const seoConfig: Partial<SEOConfig> = {
        title: article.title,
        description: article.description,
        ...(article.tags && { keywords: article.tags }),
        ogTitle: article.title,
        ogDescription: article.description,
        ...(article.image && { ogImage: article.image }),
        ogType: 'article',
        twitterTitle: article.title,
        twitterDescription: article.description,
        ...(article.image && { twitterImage: article.image }),
        jsonLd: articleJsonLd,
        canonical: window.location.href,
      };

      seoManager.updateSEO(seoConfig);
      
      logger.debug('Article SEO updated', 'SEO', {
        title: article.title,
        author: article.author,
        publishedDate: article.publishedDate,
      });
    } catch (error) {
      logger.error('Failed to update article SEO', 'SEO', error);
    }
  }, [article, location.pathname]);
}

/**
 * Hook for managing FAQ SEO
 */
export function useFAQSEO(
  faqs: Array<{ question: string; answer: string }>,
  pageConfig?: Partial<SEOConfig>
) {
  useEffect(() => {
    try {
      if (faqs.length > 0) {
        const faqJsonLd = seoManager.generateFAQJsonLd(faqs);
        
        const seoConfig: Partial<SEOConfig> = {
          ...pageConfig,
          jsonLd: faqJsonLd,
        };

        seoManager.updateSEO(seoConfig);
        
        logger.debug('FAQ SEO updated', 'SEO', {
          faqCount: faqs.length,
        });
      }
    } catch (error) {
      logger.error('Failed to update FAQ SEO', 'SEO', error);
    }
  }, [faqs, pageConfig]);
}

/**
 * Hook for managing organization SEO
 */
export function useOrganizationSEO(organization: {
  name: string;
  url: string;
  logo?: string;
  description?: string;
  contactPhone?: string;
  contactType?: string;
}) {
  useEffect(() => {
    try {
      const orgJsonLd = seoManager.generateOrganizationJsonLd({
        name: organization.name,
        url: organization.url,
        ...(organization.logo && { logo: organization.logo }),
        ...(organization.description && { description: organization.description }),
        ...(organization.contactPhone && {
          contactPoint: {
            telephone: organization.contactPhone,
            contactType: organization.contactType || 'customer service',
          }
        }),
      });

      seoManager.updateSEO({ jsonLd: orgJsonLd });
      
      logger.debug('Organization SEO updated', 'SEO', {
        name: organization.name,
        url: organization.url,
      });
    } catch (error) {
      logger.error('Failed to update organization SEO', 'SEO', error);
    }
  }, [organization]);
}

/**
 * Hook for getting SEO score and recommendations
 */
export function useSEOAnalysis() {
  const location = useLocation();

  useEffect(() => {
    // Analyze SEO after a short delay to allow DOM updates
    const timer = setTimeout(() => {
      try {
        const analysis = seoManager.getSEOScore();
        
        if (analysis.issues.length > 0) {
          logger.warn('SEO issues detected', 'SEO', {
            path: location.pathname,
            score: analysis.score,
            issues: analysis.issues,
          });
        }

        if (analysis.recommendations.length > 0) {
          logger.info('SEO recommendations', 'SEO', {
            path: location.pathname,
            recommendations: analysis.recommendations,
          });
        }

        logger.debug('SEO analysis completed', 'SEO', {
          path: location.pathname,
          score: analysis.score,
          issueCount: analysis.issues.length,
          recommendationCount: analysis.recommendations.length,
        });
      } catch (error) {
        logger.error('Failed to analyze SEO', 'SEO', error);
      }
    }, 1000);

    return () => clearTimeout(timer);
  }, [location.pathname]);
}

/**
 * Hook for managing route-based SEO
 */
export function useRouteSEO(routeConfigs: Record<string, Partial<SEOConfig>>) {
  const location = useLocation();

  useEffect(() => {
    try {
      const config = routeConfigs[location.pathname];
      if (config) {
        seoManager.updateSEO(config);
        
        logger.debug('Route SEO updated', 'SEO', {
          path: location.pathname,
          title: config.title,
        });
      }
    } catch (error) {
      logger.error('Failed to update route SEO', 'SEO', error);
    }
  }, [location.pathname, routeConfigs]);
}

/**
 * Hook for managing search result SEO
 */
export function useSearchResultSEO(
  query: string,
  resultCount: number,
  page: number = 1
) {
  const location = useLocation();

  useEffect(() => {
    try {
      if (query) {
        const title = page > 1 
          ? `Search results for "${query}" - Page ${page}`
          : `Search results for "${query}"`;
        
        const description = `Found ${resultCount} results for "${query}". Explore our comprehensive search results.`;

        const seoConfig: Partial<SEOConfig> = {
          title,
          description,
          robots: 'noindex, follow', // Don't index search result pages
          canonical: `${window.location.origin}${location.pathname}?q=${encodeURIComponent(query)}`,
        };

        seoManager.updateSEO(seoConfig);
        
        logger.debug('Search result SEO updated', 'SEO', {
          query,
          resultCount,
          page,
        });
      }
    } catch (error) {
      logger.error('Failed to update search result SEO', 'SEO', error);
    }
  }, [query, resultCount, page, location.pathname]);
}

/**
 * Hook for managing pagination SEO
 */
export function usePaginationSEO(
  baseTitle: string,
  currentPage: number,
  totalPages: number,
  baseUrl: string
) {
  useEffect(() => {
    try {
      const title = currentPage > 1 
        ? `${baseTitle} - Page ${currentPage} of ${totalPages}`
        : baseTitle;

      const canonical = currentPage > 1 
        ? `${baseUrl}?page=${currentPage}`
        : baseUrl;

      const customMeta = [];

      // Add prev/next link relations
      if (currentPage > 1) {
        customMeta.push({
          name: 'prev',
          content: currentPage === 2 ? baseUrl : `${baseUrl}?page=${currentPage - 1}`,
        });
      }

      if (currentPage < totalPages) {
        customMeta.push({
          name: 'next',
          content: `${baseUrl}?page=${currentPage + 1}`,
        });
      }

      const seoConfig: Partial<SEOConfig> = {
        title,
        canonical,
        customMeta,
      };

      seoManager.updateSEO(seoConfig);
      
      logger.debug('Pagination SEO updated', 'SEO', {
        currentPage,
        totalPages,
        title,
      });
    } catch (error) {
      logger.error('Failed to update pagination SEO', 'SEO', error);
    }
  }, [baseTitle, currentPage, totalPages, baseUrl]);
}