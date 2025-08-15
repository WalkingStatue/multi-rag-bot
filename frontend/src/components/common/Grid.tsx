/**
 * Grid component
 * 
 * A flexible grid layout component with responsive options.
 */
import React from 'react';

export interface GridProps {
  children: React.ReactNode;
  className?: string;
  cols?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  mdCols?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  lgCols?: 1 | 2 | 3 | 4 | 5 | 6 | 12;
  gap?: 'none' | 'small' | 'medium' | 'large';
  rowGap?: 'none' | 'small' | 'medium' | 'large';
  colGap?: 'none' | 'small' | 'medium' | 'large';
}

export const Grid: React.FC<GridProps> = ({
  children,
  className = '',
  cols = 1,
  mdCols,
  lgCols,
  gap = 'medium',
  rowGap,
  colGap,
}) => {
  // Column classes
  const colClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6',
    12: 'grid-cols-12',
  };
  
  // Medium breakpoint column classes
  const mdColClasses = {
    1: 'md:grid-cols-1',
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-3',
    4: 'md:grid-cols-4',
    5: 'md:grid-cols-5',
    6: 'md:grid-cols-6',
    12: 'md:grid-cols-12',
  };
  
  // Large breakpoint column classes
  const lgColClasses = {
    1: 'lg:grid-cols-1',
    2: 'lg:grid-cols-2',
    3: 'lg:grid-cols-3',
    4: 'lg:grid-cols-4',
    5: 'lg:grid-cols-5',
    6: 'lg:grid-cols-6',
    12: 'lg:grid-cols-12',
  };
  
  // Gap classes
  const gapClasses = {
    none: 'gap-0',
    small: 'gap-2',
    medium: 'gap-4',
    large: 'gap-6',
  };
  
  // Row gap classes
  const rowGapClasses = {
    none: 'row-gap-0',
    small: 'row-gap-2',
    medium: 'row-gap-4',
    large: 'row-gap-6',
  };
  
  // Column gap classes
  const colGapClasses = {
    none: 'col-gap-0',
    small: 'col-gap-2',
    medium: 'col-gap-4',
    large: 'col-gap-6',
  };
  
  // Combine classes
  const gridClasses = [
    'grid',
    colClasses[cols],
    mdCols ? mdColClasses[mdCols] : '',
    lgCols ? lgColClasses[lgCols] : '',
    !rowGap && !colGap ? gapClasses[gap] : '',
    rowGap ? rowGapClasses[rowGap] : '',
    colGap ? colGapClasses[colGap] : '',
    className,
  ].filter(Boolean).join(' ');
  
  return (
    <div className={gridClasses}>
      {children}
    </div>
  );
};

export default Grid;