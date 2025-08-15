import React, { useEffect } from 'react';
import { SEOConfig } from '../../utils/seo';

interface SEOHeadProps extends Partial<SEOConfig> {
  children?: React.ReactNode;
}

/**
 * SEO Head component for managing document head elements
 * This provides a React-friendly way to manage SEO meta tags without external dependencies
 */
export const SEOHead: React.FC<SEOHeadProps> = ({
  title,
  description,
  keywords,
  author,
  canonical,
  robots = 'index, follow',
  viewport = 'width=device-width, initial-scale=1.0',
  themeColor = '#000000',
  ogTitle,
  ogDescription,
  ogImage,
  ogUrl,
  ogType = 'website',
  ogSiteName = 'Multi-Bot RAG Platform',
  twitterCard = 'summary_large_image',
  twitterSite,
  twitterCreator,
  twitterTitle,
  twitterDescription,
  twitterImage,
  jsonLd,
  customMeta = [],
}) => {
  useEffect(() => {
    // Update document title
    if (title) {
      document.title = title;
    }

    // Update or create meta tags
    const updateMetaTag = (attribute: string, value: string, content: string) => {
      let metaTag = document.querySelector(`meta[${attribute}="${value}"]`) as HTMLMetaElement;
      if (!metaTag) {
        metaTag = document.createElement('meta');
        metaTag.setAttribute(attribute, value);
        document.head.appendChild(metaTag);
      }
      metaTag.content = content;
    };

    // Basic meta tags
    if (description) updateMetaTag('name', 'description', description);
    if (keywords && keywords.length > 0) updateMetaTag('name', 'keywords', keywords.join(', '));
    if (author) updateMetaTag('name', 'author', author);
    updateMetaTag('name', 'robots', robots);
    updateMetaTag('name', 'viewport', viewport);
    updateMetaTag('name', 'theme-color', themeColor);

    // Open Graph meta tags
    if (ogTitle || title) updateMetaTag('property', 'og:title', ogTitle || title || '');
    if (ogDescription || description) updateMetaTag('property', 'og:description', ogDescription || description || '');
    if (ogImage) updateMetaTag('property', 'og:image', ogImage);
    if (ogUrl || canonical) updateMetaTag('property', 'og:url', ogUrl || canonical || window.location.href);
    updateMetaTag('property', 'og:type', ogType);
    updateMetaTag('property', 'og:site_name', ogSiteName);

    // Twitter Card meta tags
    updateMetaTag('name', 'twitter:card', twitterCard);
    if (twitterSite) updateMetaTag('name', 'twitter:site', twitterSite);
    if (twitterCreator) updateMetaTag('name', 'twitter:creator', twitterCreator);
    if (twitterTitle || title) updateMetaTag('name', 'twitter:title', twitterTitle || title || '');
    if (twitterDescription || description) updateMetaTag('name', 'twitter:description', twitterDescription || description || '');
    if (twitterImage || ogImage) updateMetaTag('name', 'twitter:image', twitterImage || ogImage || '');

    // Custom meta tags
    customMeta.forEach((meta) => {
      if (meta.name) {
        updateMetaTag('name', meta.name, meta.content);
      } else if (meta.property) {
        updateMetaTag('property', meta.property, meta.content);
      } else if (meta.httpEquiv) {
        updateMetaTag('http-equiv', meta.httpEquiv, meta.content);
      }
    });

    // Canonical URL
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

    // Structured data (JSON-LD)
    let existingScript = document.querySelector('script[type="application/ld+json"]');
    if (existingScript) {
      existingScript.remove();
    }

    if (jsonLd) {
      const script = document.createElement('script');
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(jsonLd);
      document.head.appendChild(script);
    }
  }, [
    title,
    description,
    keywords,
    author,
    canonical,
    robots,
    viewport,
    themeColor,
    ogTitle,
    ogDescription,
    ogImage,
    ogUrl,
    ogType,
    ogSiteName,
    twitterCard,
    twitterSite,
    twitterCreator,
    twitterTitle,
    twitterDescription,
    twitterImage,
    jsonLd,
    customMeta,
  ]);

  return null; // This component doesn't render anything
};

/**
 * Default SEO configuration for the application
 */
export const DefaultSEO: React.FC = () => {
  return (
    <SEOHead
      title="Multi-Bot RAG Platform"
      description="Advanced multi-bot RAG platform for intelligent conversations and document analysis"
      keywords={['RAG', 'AI', 'chatbot', 'document analysis', 'machine learning']}
      author="Multi-Bot RAG Platform Team"
      ogType="website"
      ogSiteName="Multi-Bot RAG Platform"
      twitterCard="summary_large_image"
    />
  );
};

/**
 * SEO component for article pages
 */
export const ArticleSEO: React.FC<{
  title: string;
  description: string;
  author: string;
  publishedDate: string;
  modifiedDate?: string;
  image?: string;
  tags?: string[];
}> = ({ title, description, author, publishedDate, modifiedDate, image, tags }) => {
  const articleJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description,
    author: {
      '@type': 'Person',
      name: author,
    },
    datePublished: publishedDate,
    ...(modifiedDate && { dateModified: modifiedDate }),
    ...(image && { image }),
    url: window.location.href,
  };

  return (
    <SEOHead
      title={title}
      description={description}
      {...(tags && { keywords: tags })}
      ogTitle={title}
      ogDescription={description}
      {...(image && { ogImage: image })}
      ogType="article"
      twitterTitle={title}
      twitterDescription={description}
      {...(image && { twitterImage: image })}
      jsonLd={articleJsonLd}
      canonical={window.location.href}
    />
  );
};

/**
 * SEO component for FAQ pages
 */
export const FAQSEO: React.FC<{
  title?: string;
  description?: string;
  faqs: Array<{ question: string; answer: string }>;
}> = ({ title, description, faqs }) => {
  const faqJsonLd = {
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

  return (
    <SEOHead
      {...(title && { title })}
      {...(description && { description })}
      jsonLd={faqJsonLd}
    />
  );
};

/**
 * SEO component for search result pages
 */
export const SearchResultSEO: React.FC<{
  query: string;
  resultCount: number;
  page?: number;
}> = ({ query, resultCount, page = 1 }) => {
  const title = page > 1 
    ? `Search results for "${query}" - Page ${page}`
    : `Search results for "${query}"`;
  
  const description = `Found ${resultCount} results for "${query}". Explore our comprehensive search results.`;

  return (
    <SEOHead
      title={title}
      description={description}
      robots="noindex, follow"
      canonical={`${window.location.origin}${window.location.pathname}?q=${encodeURIComponent(query)}`}
    />
  );
};

/**
 * SEO component for breadcrumb navigation
 */
export const BreadcrumbSEO: React.FC<{
  breadcrumbs: Array<{ name: string; url: string }>;
}> = ({ breadcrumbs }) => {
  const breadcrumbJsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbs.map((crumb, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: crumb.name,
      item: crumb.url,
    })),
  };

  return <SEOHead jsonLd={breadcrumbJsonLd} />;
};

/**
 * SEO component for organization information
 */
export const OrganizationSEO: React.FC<{
  name: string;
  url: string;
  logo?: string;
  description?: string;
  contactPhone?: string;
  contactType?: string;
}> = ({ name, url, logo, description, contactPhone, contactType }) => {
  const orgJsonLd: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name,
    url,
    ...(logo && { logo }),
    ...(description && { description }),
    ...(contactPhone && {
      contactPoint: {
        '@type': 'ContactPoint',
        telephone: contactPhone,
        contactType: contactType || 'customer service',
      }
    }),
  };

  return <SEOHead jsonLd={orgJsonLd} />;
};