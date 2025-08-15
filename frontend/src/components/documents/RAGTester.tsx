import React, { useState } from 'react';
import { Search, AlertCircle, CheckCircle, XCircle, Info } from 'lucide-react';

interface RAGTestResult {
  test_query: string;
  bot_config: {
    embedding_provider: string;
    embedding_model: string;
    llm_provider: string;
    llm_model: string;
  };
  steps: Record<string, any>;
  retrieved_chunks: Array<{
    id: string;
    score: number;
    text_preview: string;
    metadata: Record<string, any>;
  }>;
  errors: string[];
}

interface RAGTesterProps {
  botId: string;
  onClose: () => void;
}

const RAGTester: React.FC<RAGTesterProps> = ({ botId, onClose }) => {
  const [testQuery, setTestQuery] = useState('What is this document about?');
  const [testResult, setTestResult] = useState<RAGTestResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runTest = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/conversations/bots/${botId}/test-retrieval`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ test_query: testQuery }),
      });

      if (!response.ok) {
        throw new Error('Failed to test RAG retrieval');
      }

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      console.error('RAG test failed:', error);
      setTestResult({
        test_query: testQuery,
        bot_config: {
          embedding_provider: 'unknown',
          embedding_model: 'unknown',
          llm_provider: 'unknown',
          llm_model: 'unknown'
        },
        steps: {},
        retrieved_chunks: [],
        errors: [error instanceof Error ? error.message : 'Unknown error']
      });
    } finally {
      setLoading(false);
    }
  };

  const StatusIcon: React.FC<{ status: boolean | number | undefined }> = ({ status }) => {
    if (status === undefined || status === null) return <Info className="w-4 h-4 text-gray-400" />;
    if (typeof status === 'boolean') {
      return status ? 
        <CheckCircle className="w-4 h-4 text-green-500" /> : 
        <XCircle className="w-4 h-4 text-red-500" />;
    }
    if (typeof status === 'number') {
      return status > 0 ? 
        <CheckCircle className="w-4 h-4 text-green-500" /> : 
        <XCircle className="w-4 h-4 text-red-500" />;
    }
    return <Info className="w-4 h-4 text-gray-400" />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">RAG Retrieval Tester</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Test Query
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter a query to test document retrieval..."
              />
              <button
                onClick={runTest}
                disabled={loading}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
                {loading ? 'Testing...' : 'Test Retrieval'}
              </button>
            </div>
          </div>

          {testResult && (
            <div className="space-y-6">
              {/* Bot Configuration */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Bot Configuration</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Embedding Provider:</span> {testResult.bot_config.embedding_provider}
                  </div>
                  <div>
                    <span className="font-medium">Embedding Model:</span> {testResult.bot_config.embedding_model}
                  </div>
                  <div>
                    <span className="font-medium">LLM Provider:</span> {testResult.bot_config.llm_provider}
                  </div>
                  <div>
                    <span className="font-medium">LLM Model:</span> {testResult.bot_config.llm_model}
                  </div>
                </div>
              </div>

              {/* Test Steps */}
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-3">Test Steps</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <StatusIcon status={testResult.steps.has_documents} />
                    <span>Documents uploaded: {testResult.steps.has_documents ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={testResult.steps.collection_exists} />
                    <span>Vector collection exists: {testResult.steps.collection_exists ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={testResult.steps.api_key_available} />
                    <span>API key available: {testResult.steps.api_key_available ? 'Yes' : 'No'}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={testResult.steps.query_embedding_generated} />
                    <span>Query embedding generated: {testResult.steps.query_embedding_generated ? 'Yes' : 'No'}</span>
                    {testResult.steps.query_embedding_dimension && (
                      <span className="text-sm text-gray-600">
                        (Dimension: {testResult.steps.query_embedding_dimension})
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Collection Info */}
              {testResult.steps.collection_info && (
                <div className="bg-white border rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-3">Collection Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium">Points Count:</span> {testResult.steps.collection_info.points_count}
                    </div>
                    <div>
                      <span className="font-medium">Vectors Count:</span> {testResult.steps.collection_info.vectors_count}
                    </div>
                    <div>
                      <span className="font-medium">Vector Size:</span> {testResult.steps.collection_info.config?.vector_size}
                    </div>
                    <div>
                      <span className="font-medium">Distance:</span> {testResult.steps.collection_info.config?.distance}
                    </div>
                  </div>
                </div>
              )}

              {/* Similarity Threshold Results */}
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-3">Similarity Search Results</h3>
                <div className="space-y-2">
                  {[0.9, 0.8, 0.7, 0.6, 0.5, 0.3, 0.1].map(threshold => {
                    const key = `chunks_found_at_threshold_${threshold}`;
                    const count = testResult.steps[key];
                    if (count !== undefined) {
                      return (
                        <div key={threshold} className="flex items-center gap-3">
                          <StatusIcon status={count} />
                          <span>Threshold {threshold}: {count} chunks found</span>
                        </div>
                      );
                    }
                    return null;
                  })}
                  
                  {testResult.steps.raw_search_results !== undefined && (
                    <div className="flex items-center gap-3">
                      <StatusIcon status={testResult.steps.raw_search_results} />
                      <span>No threshold: {testResult.steps.raw_search_results} chunks found</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Retrieved Chunks */}
              {testResult.retrieved_chunks.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-green-800 mb-3">Retrieved Chunks</h3>
                  <div className="space-y-3">
                    {testResult.retrieved_chunks.map((chunk, index) => (
                      <div key={chunk.id} className="bg-white p-3 rounded border">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-sm font-medium text-gray-600">Chunk {index + 1}</span>
                          <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">
                            Score: {chunk.score.toFixed(4)}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 mb-2">{chunk.text_preview}</p>
                        {Object.keys(chunk.metadata).length > 0 && (
                          <div className="text-xs text-gray-500">
                            <span className="font-medium">Metadata:</span> {JSON.stringify(chunk.metadata)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Errors */}
              {testResult.errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-red-800 mb-3 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5" />
                    Issues Found
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-red-700">
                    {testResult.errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {testResult.retrieved_chunks.length === 0 && testResult.errors.length === 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-yellow-800 mb-3">Recommendations</h3>
                  <ul className="list-disc list-inside space-y-1 text-yellow-700">
                    <li>Try different queries that might match your document content</li>
                    <li>Check if your documents contain content similar to your query</li>
                    <li>Consider lowering the similarity threshold in bot settings</li>
                    <li>Verify that documents were processed correctly</li>
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RAGTester;