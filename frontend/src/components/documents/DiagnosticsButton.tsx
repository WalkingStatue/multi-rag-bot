import React, { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import EmbeddingDiagnostics from './EmbeddingDiagnostics';

interface DiagnosticsButtonProps {
  botId: string;
  className?: string;
  variant?: 'primary' | 'secondary' | 'warning';
}

const DiagnosticsButton: React.FC<DiagnosticsButtonProps> = ({ 
  botId, 
  className = '',
  variant = 'warning'
}) => {
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  const getButtonClasses = () => {
    const baseClasses = 'flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors';
    
    switch (variant) {
      case 'primary':
        return `${baseClasses} bg-blue-600 text-white hover:bg-blue-700`;
      case 'secondary':
        return `${baseClasses} bg-gray-200 text-gray-700 hover:bg-gray-300`;
      case 'warning':
      default:
        return `${baseClasses} bg-yellow-100 text-yellow-800 hover:bg-yellow-200 border border-yellow-300`;
    }
  };

  return (
    <>
      <button
        onClick={() => setShowDiagnostics(true)}
        className={`${getButtonClasses()} ${className}`}
        title="Diagnose document retrieval issues"
      >
        <AlertTriangle className="w-4 h-4" />
        Diagnose RAG Issues
      </button>

      {showDiagnostics && (
        <EmbeddingDiagnostics
          botId={botId}
          onClose={() => setShowDiagnostics(false)}
        />
      )}
    </>
  );
};

export default DiagnosticsButton;