import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, RefreshCw, Info } from 'lucide-react';

interface DiagnosticResult {
  bot_id: string;
  embedding_provider: string;
  embedding_model: string;
  llm_provider: string;
  llm_model: string;
  has_documents: boolean;
  vector_collection_exists: boolean;
  api_key_available: boolean;
  model_valid: boolean;
  expected_dimension?: number;
  stored_dimension?: number;
  embedding_generation_works?: boolean;
  test_embedding_dimension?: number;
  issues: string[];
  recommendations: string[];
  available_models?: string[];
  embedding_error?: string;
  error?: string;
}

interface ReprocessResult {
  success: boolean;
  message: string;
  documents_processed: number;
  total_documents: number;
  total_chunks: number;
  embedding_provider: string;
  embedding_model: string;
  errors: string[];
}

interface EmbeddingDiagnosticsProps {
  botId: string;
  onClose: () => void;
}

const EmbeddingDiagnostics: React.FC<EmbeddingDiagnosticsProps> = ({ botId, onClose }) => {
  const [diagnostics, setDiagnostics] = useState<DiagnosticResult | null>(null);
  const [reprocessResult, setReprocessResult] = useState<ReprocessResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);

  const runDiagnostics = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/conversations/bots/${botId}/diagnose`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to run diagnostics');
      }

      const result = await response.json();
      setDiagnostics(result);
    } catch (error) {
      console.error('Diagnostics failed:', error);
      setDiagnostics({
        bot_id: botId,
        embedding_provider: 'unknown',
        embedding_model: 'unknown',
        llm_provider: 'unknown',
        llm_model: 'unknown',
        has_documents: false,
        vector_collection_exists: false,
        api_key_available: false,
        model_valid: false,
        issues: ['Failed to run diagnostics'],
        recommendations: ['Check your connection and try again'],
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setLoading(false);
    }
  };

  const reprocessDocuments = async (forceRecreate: boolean = false) => {
    setReprocessing(true);
    try {
      const response = await fetch(`/api/bots/${botId}/documents/reprocess?force_recreate_collection=${forceRecreate}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to reprocess documents');
      }

      const result = await response.json();
      setReprocessResult(result);
      
      // Re-run diagnostics after reprocessing
      setTimeout(() => {
        runDiagnostics();
      }, 1000);
    } catch (error) {
      console.error('Reprocessing failed:', error);
      setReprocessResult({
        success: false,
        message: error instanceof Error ? error.message : 'Reprocessing failed',
        documents_processed: 0,
        total_documents: 0,
        total_chunks: 0,
        embedding_provider: 'unknown',
        embedding_model: 'unknown',
        errors: [error instanceof Error ? error.message : 'Unknown error']
      });
    } finally {
      setReprocessing(false);
    }
  };

  const StatusIcon: React.FC<{ status: boolean | undefined }> = ({ status }) => {
    if (status === undefined) return <Info className="w-4 h-4 text-gray-400" />;
    return status ? 
      <CheckCircle className="w-4 h-4 text-green-500" /> : 
      <XCircle className="w-4 h-4 text-red-500" />;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Embedding Diagnostics</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <div className="mb-6">
            <button
              onClick={runDiagnostics}
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Info className="w-4 h-4" />}
              {loading ? 'Running Diagnostics...' : 'Run Diagnostics'}
            </button>
          </div>

          {diagnostics && (
            <div className="space-y-6">
              {/* Configuration Overview */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Bot Configuration</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">LLM Provider:</span> {diagnostics.llm_provider}
                  </div>
                  <div>
                    <span className="font-medium">LLM Model:</span> {diagnostics.llm_model}
                  </div>
                  <div>
                    <span className="font-medium">Embedding Provider:</span> {diagnostics.embedding_provider}
                  </div>
                  <div>
                    <span className="font-medium">Embedding Model:</span> {diagnostics.embedding_model}
                  </div>
                </div>
              </div>

              {/* Status Checks */}
              <div className="bg-white border rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-3">System Status</h3>
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <StatusIcon status={diagnostics.has_documents} />
                    <span>Documents uploaded</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={diagnostics.vector_collection_exists} />
                    <span>Vector collection exists</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={diagnostics.api_key_available} />
                    <span>API key configured for embedding provider</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={diagnostics.model_valid} />
                    <span>Embedding model valid for provider</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusIcon status={diagnostics.embedding_generation_works} />
                    <span>Embedding generation working</span>
                  </div>
                </div>
              </div>

              {/* Dimension Information */}
              {(diagnostics.expected_dimension || diagnostics.stored_dimension) && (
                <div className="bg-white border rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-3">Embedding Dimensions</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {diagnostics.expected_dimension && (
                      <div>
                        <span className="font-medium">Expected:</span> {diagnostics.expected_dimension}
                      </div>
                    )}
                    {diagnostics.stored_dimension && (
                      <div>
                        <span className="font-medium">Stored:</span> {diagnostics.stored_dimension}
                      </div>
                    )}
                    {diagnostics.test_embedding_dimension && (
                      <div>
                        <span className="font-medium">Test Generated:</span> {diagnostics.test_embedding_dimension}
                      </div>
                    )}
                  </div>
                  {diagnostics.expected_dimension && diagnostics.stored_dimension && 
                   diagnostics.expected_dimension !== diagnostics.stored_dimension && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                      <AlertTriangle className="w-4 h-4 inline mr-1" />
                      Dimension mismatch detected! This will prevent proper document retrieval.
                    </div>
                  )}
                </div>
              )}

              {/* Issues */}
              {diagnostics.issues.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-red-800 mb-3 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    Issues Found
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-red-700">
                    {diagnostics.issues.map((issue, index) => (
                      <li key={index}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {diagnostics.recommendations.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-blue-800 mb-3">Recommendations</h3>
                  <ul className="list-disc list-inside space-y-1 text-blue-700">
                    {diagnostics.recommendations.map((rec, index) => (
                      <li key={index}>{rec}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Available Models */}
              {diagnostics.available_models && diagnostics.available_models.length > 0 && (
                <div className="bg-gray-50 border rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-3">Available Models for {diagnostics.embedding_provider}</h3>
                  <div className="flex flex-wrap gap-2">
                    {diagnostics.available_models.map((model, index) => (
                      <span key={index} className="bg-gray-200 px-2 py-1 rounded text-sm">
                        {model}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Reprocessing Actions */}
              {diagnostics.has_documents && diagnostics.issues.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-yellow-800 mb-3">Fix Actions</h3>
                  <div className="space-y-3">
                    <p className="text-yellow-700 text-sm">
                      If you've fixed the configuration issues above, you can reprocess your documents to resolve embedding problems.
                    </p>
                    <div className="flex gap-3">
                      <button
                        onClick={() => reprocessDocuments(false)}
                        disabled={reprocessing}
                        className="bg-yellow-600 text-white px-4 py-2 rounded-md hover:bg-yellow-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        {reprocessing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        Reprocess Documents
                      </button>
                      <button
                        onClick={() => reprocessDocuments(true)}
                        disabled={reprocessing}
                        className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                      >
                        {reprocessing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        Force Recreate Collection
                      </button>
                    </div>
                    <p className="text-xs text-yellow-600">
                      "Force Recreate Collection" will delete the entire vector collection and rebuild it. Use this if you have dimension mismatches.
                    </p>
                  </div>
                </div>
              )}

              {/* Reprocessing Results */}
              {reprocessResult && (
                <div className={`border rounded-lg p-4 ${reprocessResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                  <h3 className={`text-lg font-semibold mb-3 ${reprocessResult.success ? 'text-green-800' : 'text-red-800'}`}>
                    Reprocessing Results
                  </h3>
                  <p className={reprocessResult.success ? 'text-green-700' : 'text-red-700'}>
                    {reprocessResult.message}
                  </p>
                  {reprocessResult.success && (
                    <div className="mt-2 text-sm text-green-600">
                      <p>Documents processed: {reprocessResult.documents_processed}/{reprocessResult.total_documents}</p>
                      <p>Total chunks created: {reprocessResult.total_chunks}</p>
                      <p>Using: {reprocessResult.embedding_provider}/{reprocessResult.embedding_model}</p>
                    </div>
                  )}
                  {reprocessResult.errors.length > 0 && (
                    <div className="mt-2">
                      <p className="text-red-700 font-medium">Errors:</p>
                      <ul className="list-disc list-inside text-red-600 text-sm">
                        {reprocessResult.errors.map((error, index) => (
                          <li key={index}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {diagnostics?.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-red-800 mb-2">Error</h3>
              <p className="text-red-700">{diagnostics.error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmbeddingDiagnostics;