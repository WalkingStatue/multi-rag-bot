import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, XCircleIcon, CogIcon } from '@heroicons/react/24/outline';

interface OCRStatusData {
  available: boolean;
  enabled: boolean;
  message: string;
  version_info: string;
  installed_languages: string[];
  available_languages: string[];
  default_language: string;
  config: string;
}

interface OCRTestResult {
  success: boolean;
  original_text: string;
  ocr_result: string;
  accuracy_percent: number;
  language_used: string;
  config_used: string;
}

const OCRStatus: React.FC = () => {
  const [ocrStatus, setOcrStatus] = useState<OCRStatusData | null>(null);
  const [testResult, setTestResult] = useState<OCRTestResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchOCRStatus();
  }, []);

  const fetchOCRStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/ocr/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch OCR status');
      }

      const data = await response.json();
      setOcrStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const testOCR = async () => {
    try {
      setTesting(true);
      const response = await fetch('/api/ocr/test', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('OCR test failed');
      }

      const data = await response.json();
      setTestResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OCR test failed');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center">
          <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700">Error: {error}</span>
        </div>
        <button
          onClick={fetchOCRStatus}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">OCR Status</h3>
        <button
          onClick={fetchOCRStatus}
          className="p-2 text-gray-400 hover:text-gray-600"
          title="Refresh status"
        >
          <CogIcon className="h-5 w-5" />
        </button>
      </div>

      {ocrStatus && (
        <div className="space-y-4">
          {/* Availability Status */}
          <div className="flex items-center">
            {ocrStatus.available ? (
              <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
            ) : (
              <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
            )}
            <span className={`font-medium ${ocrStatus.available ? 'text-green-700' : 'text-red-700'}`}>
              OCR {ocrStatus.available ? 'Available' : 'Unavailable'}
            </span>
          </div>

          {/* Status Message */}
          <div className="text-sm text-gray-600">
            <strong>Status:</strong> {ocrStatus.message}
          </div>

          {/* Configuration Details */}
          {ocrStatus.available && (
            <>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <strong>Enabled:</strong> {ocrStatus.enabled ? 'Yes' : 'No'}
                </div>
                <div>
                  <strong>Default Language:</strong> {ocrStatus.default_language}
                </div>
              </div>

              {/* Installed Languages */}
              <div className="text-sm">
                <strong>Installed Languages:</strong>
                <div className="mt-1 flex flex-wrap gap-1">
                  {ocrStatus.installed_languages.map((lang) => (
                    <span
                      key={lang}
                      className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
                    >
                      {lang}
                    </span>
                  ))}
                </div>
              </div>

              {/* Test OCR */}
              <div className="pt-4 border-t">
                <button
                  onClick={testOCR}
                  disabled={testing || !ocrStatus.enabled}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                >
                  {testing ? 'Testing...' : 'Test OCR'}
                </button>
              </div>

              {/* Test Results */}
              {testResult && (
                <div className="mt-4 p-4 bg-gray-50 rounded">
                  <h4 className="font-medium text-gray-900 mb-2">Test Results</h4>
                  <div className="space-y-2 text-sm">
                    <div>
                      <strong>Original:</strong> {testResult.original_text}
                    </div>
                    <div>
                      <strong>OCR Result:</strong> {testResult.ocr_result}
                    </div>
                    <div>
                      <strong>Accuracy:</strong> 
                      <span className={`ml-1 font-medium ${
                        testResult.accuracy_percent > 80 ? 'text-green-600' : 
                        testResult.accuracy_percent > 60 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {testResult.accuracy_percent}%
                      </span>
                    </div>
                    <div>
                      <strong>Language:</strong> {testResult.language_used}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default OCRStatus;