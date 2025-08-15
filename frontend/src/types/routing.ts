/**
 * Routing-related type definitions
 */

export interface RouteConfig {
  path: string;
  element: React.ComponentType<any>;
  children?: RouteConfig[];
  protected?: boolean;
  roles?: string[];
  fallback?: React.ComponentType<any>;
  errorBoundary?: React.ComponentType<any>;
  loader?: () => Promise<any>;
  meta?: RouteMeta;
}

export interface RouteMeta {
  title?: string;
  description?: string;
  keywords?: string[];
  canonical?: string;
  noIndex?: boolean;
  breadcrumbs?: Breadcrumb[];
}

export interface Breadcrumb {
  label: string;
  path?: string;
  active?: boolean;
}

export interface NavigationItem {
  id: string;
  label: string;
  path?: string;
  icon?: string;
  children?: NavigationItem[];
  roles?: string[];
  external?: boolean;
  badge?: string | number;
}

export interface RouteParams {
  [key: string]: string | undefined;
}

export interface LocationState {
  from?: string;
  returnTo?: string;
  [key: string]: any;
}