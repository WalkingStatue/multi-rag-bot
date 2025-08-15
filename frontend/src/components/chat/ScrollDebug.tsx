/**
 * Debug component to test scrolling behavior
 */
import React, { useEffect, useRef } from 'react';

export const ScrollDebug: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const logScrollInfo = () => {
      if (containerRef.current) {
        const container = containerRef.current;
        console.log('ScrollDebug:', {
          scrollTop: container.scrollTop,
          scrollHeight: container.scrollHeight,
          clientHeight: container.clientHeight,
          isAtBottom: container.scrollTop + container.clientHeight >= container.scrollHeight - 5
        });
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('scroll', logScrollInfo);
      return () => container.removeEventListener('scroll', logScrollInfo);
    }
  }, []);

  return (
    <div className="p-2 bg-yellow-100 text-xs">
      <div>Scroll Debug Active - Check console for scroll info</div>
      <div ref={containerRef} className="h-20 overflow-y-auto border border-gray-300 mt-1">
        <div className="h-40 bg-gradient-to-b from-red-100 to-blue-100 p-2">
          Scrollable content for testing
        </div>
      </div>
    </div>
  );
};