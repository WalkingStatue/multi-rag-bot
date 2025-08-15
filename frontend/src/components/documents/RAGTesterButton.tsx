import React, { useState } from 'react';
import { Search } from 'lucide-react';
import RAGTester from './RAGTester';

interface RAGTesterButtonProps {
  botId: string;
  className?: string;
  variant?: 'primary' | 'secondary';
}

const RAGTesterButton: React.FC<RAGTesterButtonProps> = ({ 
  botId, 
  className = '',
  variant = 'primary'
}) => {
  const [showTester, setShowTester] = useState(false);

  const getButtonClasses = () => {
    const baseClasses = 'flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors';
    
    switch (variant) {
      case 'primary':
        return `${baseClasses} bg-blue-600 text-white hover:bg-blue-700`;
      case 'secondary':
      default:
        return `${baseClasses} bg-gray-200 text-gray-700 hover:bg-gray-300`;
    }
  };

  return (
    <>
      <button
        onClick={() => setShowTester(true)}
        className={`${getButtonClasses()} ${className}`}
        title="Test document retrieval with custom queries"
      >
        <Search className="w-4 h-4" />
        Test RAG Retrieval
      </button>

      {showTester && (
        <RAGTester
          botId={botId}
          onClose={() => setShowTester(false)}
        />
      )}
    </>
  );
};

export default RAGTesterButton;