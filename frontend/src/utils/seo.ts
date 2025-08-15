/**
 * SEO and Meta Tag Management Utilities
 * Provides comprehensive SEO optimization and meta tag management
 */

export interface MetaTag {
  name?: string;
  property?: string;
  content: string;
  httpEquiv?: string;
}

export interface SEOConfig {
  title: string;
  description: string;
  keywords?: string[];
  author?: string;
  canonical?: string;
  robots?: string;
  viewport?: string;
  themeColor?: string;
  ogTitle?: string;
  ogDescription?: string;
  ogImage?: string;
  ogUrl?: string;
  ogType?: string;
  ogSiteName?: string;
  twitterCard?: string;
  twitterSite?: string;
  twitterCreator?: string;
  twitterTitle?: string;
  twitterDescription?: string;
  twitterImage?: string;
  jsonLd?: Record<string, any>;
  customMeta?: MetaTag[];
}

export class SEOManager {
  private static instance: SEOManager;
  private defaultConfig: Partial<SEOConfig> = {};

  private constructor() {
    this.initializeDefaults();
  }

  public static getInstance(): SEOManager {
    if (!SEOManager.instance) {
      SEOManager.instance = new SEOManager();
    }
    return SEOManager.instance;
  }

  private initializeDefaults(): void {
    this.defaultConfig = {
      title: 'Multi-Bot RAG Platform',
      description: 'Advanced multi-bot RAG platform for intelligent conversations and document analysis',
      keywords: ['RAG', 'AI', 'chatbot', 'document analysis', 'machine learning'],
      author: 'Multi-Bot RAG Platform Team',
      robots: 'index, follow',
      viewport: 'width=device-width, initial-scale=1.0',
      themeColor: '#000000',
      ogType: 'website',
      ogSiteName: 'Multi-Bot RAG Platform',
      twitterCard: 'summary_large_image',
    };
  }

  /**
   * Set default SEO configuration
   */
  public setDefaults(config: Partial<SEOConfig>): void {
    this.defaultConfig = { ...this.defaultConfig, ...config };
  }

  /**
   * Update page SEO configuration
   */
  public updateSEO(config: Partial<SEOConfig>): void {
    const finalConfig = { ...this.defaultConfig, ...config } as SEOConfig;
    
    this.updateTitle(finalConfig.title);
    this.updateMetaTags(finalConfig);
    this.updateOpenGraph(finalConfig);
    this.updateTwitterCard(finalConfig);
    this.updateJsonLd(finalConfig.jsonLd);
    this.updateCanonical(finalConfig.canonical);
  }

  /**
   * Update page title
   */
  private updateTitle(title: string): void {
    document.title = title;
    
    // Update og:title if not explicitly set
    this.updateMetaTag('property', 'og:title', title);
  }

  /**
   * Update basic meta tags
   */
  private updateMetaTags(config: Partial<SEOConfig>): void {
    const metaTags = [
      { name: 'description', content: config.description || '' },
      { name: 'keywords', content: config.keywords?.join(', ') || '' },
      { name: 'author', content: config.author || '' },
      { name: 'robots', content: config.robots || 'index, follow' },
      { name: 'viewport', content: config.viewport || 'width=device-width, initial-scale=1.0' },
      { name: 'theme-color', content: config.themeColor || '#000000' },
    ];

    metaTags.forEach(tag => {
      if (tag.content) {
        this.updateMetaTag('name', tag.name, tag.content);
      }
    });

    // Add custom meta tags
    if (config.customMeta) {
      config.customMeta.forEach(meta => {
        if (meta.name) {
          this.updateMetaTag('name', meta.name, meta.content);
        } else if (meta.property) {
          this.updateMetaTag('property', meta.property, meta.content);
        } else if (meta.httpEquiv) {
          this.updateMetaTag('http-equiv', meta.httpEquiv, meta.content);
        }
      });
    }
  }

  /**
   * Update Open Graph meta tags
   */
  private updateOpenGraph(config: Partial<SEOConfig>): void {
    const ogTags = [
      { property: 'og:title', content: config.ogTitle || config.title || '' },
      { property: 'og:description', content: config.ogDescription || config.description || '' },
      { property: 'og:image', content: config.ogImage || '' },
      { property: 'og:url', content: config.ogUrl || window.location.href },
      { property: 'og:type', content: config.ogType || 'website' },
      { property: 'og:site_name', content: config.ogSiteName || 'Multi-Bot RAG Platform' },
    ];

    ogTags.forEach(tag => {
      if (tag.content) {
        this.updateMetaTag('property', tag.property, tag.content);
      }
    });
  }

  /**
   * Update Twitter Card meta tags
   */
  private updateTwitterCard(config: Partial<SEOConfig>): void {
    const twitterTags = [
      { name: 'twitter:card', content: config.twitterCard || 'summary_large_image' },
      { name: 'twitter:site', content: config.twitterSite || '' },
      { name: 'twitter:creator', content: config.twitterCreator || '' },
      { name: 'twitter:title', content: config.twitterTitle || config.title || '' },
      { name: 'twitter:description', content: config.twitterDescription || config.description || '' },
      { name: 'twitter:image', content: config.twitterImage || config.ogImage || '' },
    ];

    twitterTags.forEach(tag => {
      if (tag.content) {
        this.updateMetaTag('name', tag.name, tag.content);
      }
    });
  }

  /**
   * Update JSON-LD structured data
   */
  private updateJsonLd(jsonLd?: Record<string, any>): void {
    // Remove existing JSON-LD
    const existingScript = document.querySelector('script[type="application/ld+json"]');
    if (existingScript) {
      existingScript.remove();
    }

    if (jsonLd) {
      const script = document.createElement('script');
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(jsonLd);
      document.head.appendChild(script);
    }
  }

  /**
   * Update canonical URL
   */
  private updateCanonical(canonical?: string): void {
    let canonicalLink = document.querySelector('link[rel="canonical"]') as HTMLLinkElement;
    
    if (canonical) {
      if (!canonicalLink) {
        canonicalLink = document.createElement('link');
        canonicalLink.rel = 'canonical';
        document.head.appendChild(canonicalLink);
      }
      canonicalLink.href = canonical;
    } else if (canonicalLink) {
      canonicalLink.remove();
    }
  }

  /**
   * Update a specific meta tag
   */
  private updateMetaTag(attribute: string, value: string, content: string): void {
    let metaTag = document.querySelector(`meta[${attribute}="${value}"]`) as HTMLMetaElement;
    
    if (!metaTag) {
      metaTag = document.createElement('meta');
      metaTag.setAttribute(attribute, value);
      document.head.appendChild(metaTag);
    }
    
    metaTag.content = content;
  }

  /**
   * Generate breadcrumb JSON-LD
   */
  public generateBreadcrumbJsonLd(breadcrumbs: Array<{ name: string; url: string }>): Record<string, any> {
    return {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: breadcrumbs.map((crumb, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: crumb.name,
        item: crumb.url,
      })),
    };
  }

  /**
   * Generate organization JSON-LD
   */
  public generateOrganizationJsonLd(org: {
    name: string;
    url: string;
    logo?: string;
    description?: string;
    contactPoint?: {
      telephone: string;
      contactType: string;
    };
  }): Record<string, any> {
    const jsonLd: Record<string, any> = {
      '@context': 'https://schema.org',
      '@type': 'Organization',
      name: org.name,
      url: org.url,
    };

    if (org.logo) {
      jsonLd.logo = org.logo;
    }

    if (org.description) {
      jsonLd.description = org.description;
    }

    if (org.contactPoint) {
      jsonLd.contactPoint = {
        '@type': 'ContactPoint',
        telephone: org.contactPoint.telephone,
        contactType: org.contactPoint.contactType,
      };
    }

    return jsonLd;
  }

  /**
   * Generate FAQ JSON-LD
   */
  public generateFAQJsonLd(faqs: Array<{ question: string; answer: string }>): Record<string, any> {
    return {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: faqs.map(faq => ({
        '@type': 'Question',
        name: faq.question,
        acceptedAnswer: {
          '@type': 'Answer',
          text: faq.answer,
        },
      })),
    };
  }

  /**
   * Generate article JSON-LD
   */
  public generateArticleJsonLd(article: {
    headline: string;
    description: string;
    author: string;
    datePublished: string;
    dateModified?: string;
    image?: string;
    url: string;
  }): Record<string, any> {
    const jsonLd: Record<string, any> = {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: article.headline,
      description: article.description,
      author: {
        '@type': 'Person',
        name: article.author,
      },
      datePublished: article.datePublished,
      url: article.url,
    };

    if (article.dateModified) {
      jsonLd.dateModified = article.dateModified;
    }

    if (article.image) {
      jsonLd.image = article.image;
    }

    return jsonLd;
  }

  /**
   * Get current page SEO score (basic analysis)
   */
  public getSEOScore(): {
    score: number;
    issues: string[];
    recommendations: string[];
  } {
    const issues: string[] = [];
    const recommendations: string[] = [];
    let score = 100;

    // Check title
    const title = document.title;
    if (!title) {
      issues.push('Missing page title');
      score -= 20;
    } else if (title.length < 30 || title.length > 60) {
      recommendations.push('Title should be between 30-60 characters');
      score -= 5;
    }

    // Check description
    const description = document.querySelector('meta[name="description"]')?.getAttribute('content');
    if (!description) {
      issues.push('Missing meta description');
      score -= 15;
    } else if (description.length < 120 || description.length > 160) {
      recommendations.push('Meta description should be between 120-160 characters');
      score -= 5;
    }

    // Check canonical URL
    const canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      recommendations.push('Consider adding canonical URL');
      score -= 5;
    }

    // Check Open Graph
    const ogTitle = document.querySelector('meta[property="og:title"]');
    const ogDescription = document.querySelector('meta[property="og:description"]');
    const ogImage = document.querySelector('meta[property="og:image"]');
    
    if (!ogTitle || !ogDescription) {
      recommendations.push('Add Open Graph meta tags for better social sharing');
      score -= 10;
    }

    if (!ogImage) {
      recommendations.push('Add Open Graph image for better social sharing');
      score -= 5;
    }

    // Check structured data
    const jsonLd = document.querySelector('script[type="application/ld+json"]');
    if (!jsonLd) {
      recommendations.push('Consider adding structured data (JSON-LD)');
      score -= 10;
    }

    return {
      score: Math.max(0, score),
      issues,
      recommendations,
    };
  }

  /**
   * Reset all SEO tags to defaults
   */
  public reset(): void {
    this.updateSEO(this.defaultConfig);
  }
}

// Export singleton instance
export const seoManager = SEOManager.getInstance();

// Utility functions
export const updatePageSEO = (config: Partial<SEOConfig>) => {
  seoManager.updateSEO(config);
};

export const setDefaultSEO = (config: Partial<SEOConfig>) => {
  seoManager.setDefaults(config);
};

export const getSEOScore = () => {
  return seoManager.getSEOScore();
};