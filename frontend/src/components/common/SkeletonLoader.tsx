/**
 * Skeleton Loading Components
 * 
 * Reusable skeleton loaders for different content types
 */
import React from 'react';
import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  width?: string;
  height?: string;
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | 'full';
  animated?: boolean;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  width = 'w-full',
  height = 'h-4',
  rounded = 'md',
  animated = true,
}) => {
  const roundedClasses = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    xl: 'rounded-xl',
    full: 'rounded-full',
  };

  return (
    <div
      className={clsx(
        'bg-neutral-200 dark:bg-neutral-700',
        width,
        height,
        roundedClasses[rounded],
        animated && 'animate-pulse',
        className
      )}
    />
  );
};

export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({
  lines = 3,
  className = '',
}) => {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          width={index === lines - 1 ? 'w-3/4' : 'w-full'}
          height="h-4"
        />
      ))}
    </div>
  );
};

export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={clsx('p-6 border border-neutral-200 dark:border-neutral-800 rounded-xl bg-white dark:bg-neutral-900', className)}>
      <div className="flex items-center space-x-4 mb-4">
        <Skeleton width="w-12" height="h-12" rounded="full" />
        <div className="flex-1">
          <Skeleton width="w-1/3" height="h-5" className="mb-2" />
          <Skeleton width="w-1/2" height="h-4" />
        </div>
      </div>
      <SkeletonText lines={2} className="mb-4" />
      <div className="flex justify-between items-center">
        <Skeleton width="w-20" height="h-8" rounded="lg" />
        <Skeleton width="w-24" height="h-8" rounded="lg" />
      </div>
    </div>
  );
};

export const SkeletonTable: React.FC<{ rows?: number; cols?: number; className?: string }> = ({
  rows = 5,
  cols = 4,
  className = '',
}) => {
  return (
    <div className={clsx('space-y-4', className)}>
      {/* Header */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }).map((_, index) => (
          <Skeleton key={`header-${index}`} width="w-full" height="h-5" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((_, colIndex) => (
            <Skeleton key={`cell-${rowIndex}-${colIndex}`} width="w-full" height="h-4" />
          ))}
        </div>
      ))}
    </div>
  );
};

export const SkeletonList: React.FC<{ items?: number; className?: string }> = ({
  items = 5,
  className = '',
}) => {
  return (
    <div className={clsx('space-y-3', className)}>
      {Array.from({ length: items }).map((_, index) => (
        <div key={index} className="flex items-center space-x-3 p-3 border border-neutral-200 dark:border-neutral-800 rounded-lg">
          <Skeleton width="w-10" height="h-10" rounded="full" />
          <div className="flex-1">
            <Skeleton width="w-1/4" height="h-4" className="mb-2" />
            <Skeleton width="w-3/4" height="h-3" />
          </div>
          <Skeleton width="w-16" height="h-6" rounded="lg" />
        </div>
      ))}
    </div>
  );
};

export const SkeletonDashboard: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={clsx('space-y-8', className)}>
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <Skeleton width="w-48" height="h-8" className="mb-2" />
          <Skeleton width="w-64" height="h-5" />
        </div>
        <Skeleton width="w-32" height="h-10" rounded="lg" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="p-6 border border-neutral-200 dark:border-neutral-800 rounded-xl">
            <div className="flex items-center">
              <Skeleton width="w-12" height="h-12" rounded="xl" className="mr-4" />
              <div>
                <Skeleton width="w-16" height="h-8" className="mb-2" />
                <Skeleton width="w-20" height="h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Content Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-4">
          <Skeleton width="w-40" height="h-6" />
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <Skeleton width="w-36" height="h-6" />
          <SkeletonTable rows={6} cols={3} />
        </div>
      </div>
    </div>
  );
};

export const SkeletonChat: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={clsx('space-y-4', className)}>
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-xs p-3 rounded-xl bg-primary-100 dark:bg-primary-900/30">
          <Skeleton width="w-full" height="h-4" className="mb-2" />
          <Skeleton width="w-2/3" height="h-4" />
        </div>
      </div>

      {/* Bot message */}
      <div className="flex justify-start">
        <div className="flex items-start space-x-3 max-w-xs">
          <Skeleton width="w-8" height="h-8" rounded="full" />
          <div className="flex-1 p-3 rounded-xl bg-neutral-100 dark:bg-neutral-800">
            <SkeletonText lines={3} />
          </div>
        </div>
      </div>

      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-xs p-3 rounded-xl bg-primary-100 dark:bg-primary-900/30">
          <Skeleton width="w-3/4" height="h-4" />
        </div>
      </div>

      {/* Typing indicator */}
      <div className="flex justify-start">
        <div className="flex items-start space-x-3 max-w-xs">
          <Skeleton width="w-8" height="h-8" rounded="full" />
          <div className="flex-1 p-3 rounded-xl bg-neutral-100 dark:bg-neutral-800">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-2 h-2 bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export const SkeletonPage: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <div className={clsx('max-w-4xl mx-auto p-6 space-y-8', className)}>
      {/* Page Header */}
      <div className="text-center space-y-4">
        <Skeleton width="w-96" height="h-12" className="mx-auto" />
        <Skeleton width="w-128" height="h-6" className="mx-auto" />
      </div>

      {/* Content Sections */}
      <div className="space-y-12">
        <div className="space-y-6">
          <Skeleton width="w-64" height="h-8" />
          <SkeletonText lines={4} />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <SkeletonCard />
          <SkeletonCard />
        </div>

        <div className="space-y-6">
          <Skeleton width="w-48" height="h-8" />
          <SkeletonList items={4} />
        </div>
      </div>
    </div>
  );
};

export default Skeleton;
