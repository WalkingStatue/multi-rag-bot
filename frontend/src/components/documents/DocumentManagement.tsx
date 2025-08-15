/**
 * Main document management component that integrates upload, listing, and viewing
 */

import React, { useState, useCallback } from 'react';
import { DocumentResponse } from '../../types/document';
import DocumentUpload from './DocumentUpload';
import DocumentList from './DocumentList';
import DocumentViewer from './DocumentViewer';

interface DocumentManagementProps {
  botId: string;
}

const DocumentManagement: React.FC<DocumentManagementProps> = ({ botId }) => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);

  const handleUploadComplete = useCallback((documents: DocumentResponse[]) => {
    setUploadSuccess(`Successfully uploaded ${documents.length} document${documents.length > 1 ? 's' : ''}`);
    setUploadError(null);
    // Trigger a refresh of the document list
    setRefreshKey(prev => prev + 1);
    
    // Clear success message after 5 seconds
    setTimeout(() => setUploadSuccess(null), 5000);
  }, []);

  const handleUploadError = useCallback((error: string) => {
    setUploadError(error);
    setUploadSuccess(null);
  }, []);

  const clearMessages = useCallback(() => {
    setUploadSuccess(null);
    setUploadError(null);
  }, []);

  const handleDocumentSelect = useCallback((document: DocumentResponse) => {
    setSelectedDocumentId(document.id);
  }, []);

  const handleCloseViewer = useCallback(() => {
    setSelectedDocumentId(null);
  }, []);

  return (
    <div className="document-management space-y-6">
      <div className="document-management-header">
        <h2 className="text-2xl font-bold text-gray-900">Document Management</h2>
        <p className="text-gray-600 mt-1">
          Upload and manage documents for this bot's knowledge base
        </p>
      </div>

      {/* Success/Error Messages */}
      {uploadSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex items-center justify-between">
            <span className="text-green-800">{uploadSuccess}</span>
            <button 
              onClick={clearMessages} 
              className="text-green-600 hover:text-green-800"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {uploadError && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex items-center justify-between">
            <span className="text-red-800">{uploadError}</span>
            <button 
              onClick={clearMessages} 
              className="text-red-600 hover:text-red-800"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Upload Section */}
      <div className="document-upload-section">
        <DocumentUpload
          botId={botId}
          onUploadComplete={handleUploadComplete}
          onUploadError={handleUploadError}
          multiple={true}
          processImmediately={true}
        />
      </div>

      {/* Document List Section */}
      <div className="document-list-section">
        <DocumentList 
          botId={botId} 
          key={refreshKey} // Force re-render when refreshKey changes
          onDocumentSelect={handleDocumentSelect}
        />
      </div>

      {/* Document Viewer Modal */}
      {selectedDocumentId && (
        <DocumentViewer
          botId={botId}
          documentId={selectedDocumentId}
          onClose={handleCloseViewer}
        />
      )}
    </div>
  );
};

export default DocumentManagement;
