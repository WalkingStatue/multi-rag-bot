import React, { useEffect, useState, useCallback } from 'react';
import { 
  DocumentListResponse, 
  DocumentResponse, 
  DocumentListFilters,
  PROCESSING_STATUS_CONFIG 
} from '../../types/document';
import { 
  fetchDocumentList, 
  deleteDocument, 
  formatFileSize, 
  getFileTypeInfo,
  formatProcessingStatus 
} from '../../services/documentService';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  DocumentTextIcon,
  TrashIcon,
  EyeIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface DocumentListProps {
  botId: string;
  onDocumentSelect?: (document: DocumentResponse) => void;
}

const DocumentList: React.FC<DocumentListProps> = ({ botId, onDocumentSelect }) => {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [filteredDocuments, setFilteredDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<DocumentListFilters>({
    search: '',
    sort_by: 'created_at',
    sort_order: 'desc'
  });
  const [showFilters, setShowFilters] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const response: DocumentListResponse = await fetchDocumentList(botId);
      setDocuments(response.documents);
      setError(null);
    } catch (error) {
      setError('Failed to load documents.');
    } finally {
      setLoading(false);
    }
  }, [botId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Apply filters and sorting
  useEffect(() => {
    let filtered = [...documents];

    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(doc => 
        doc.filename.toLowerCase().includes(searchLower)
      );
    }

    // Apply status filter
    if (filters.processing_status) {
      filtered = filtered.filter(doc => doc.processing_status === filters.processing_status);
    }

    // Apply mime type filter
    if (filters.mime_type) {
      filtered = filtered.filter(doc => doc.mime_type === filters.mime_type);
    }

    // Apply sorting
    if (filters.sort_by) {
      filtered.sort((a, b) => {
        let aValue: any = a[filters.sort_by as keyof DocumentResponse];
        let bValue: any = b[filters.sort_by as keyof DocumentResponse];

        if (filters.sort_by === 'created_at') {
          aValue = new Date(aValue).getTime();
          bValue = new Date(bValue).getTime();
        }

        if (filters.sort_order === 'desc') {
          return bValue > aValue ? 1 : -1;
        } else {
          return aValue > bValue ? 1 : -1;
        }
      });
    }

    setFilteredDocuments(filtered);
  }, [documents, filters]);

  const handleDelete = async (documentId: string, filename: string) => {
    if (deleteConfirm !== documentId) {
      setDeleteConfirm(documentId);
      return;
    }

    try {
      setDeleting(documentId);
      await deleteDocument(botId, documentId);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
      setDeleteConfirm(null);
    } catch (error) {
      setError(`Failed to delete document: ${filename}`);
    } finally {
      setDeleting(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const config = PROCESSING_STATUS_CONFIG[status as keyof typeof PROCESSING_STATUS_CONFIG];
    if (!config) return null;

    const colorClasses = {
      yellow: 'bg-yellow-100 text-yellow-800',
      blue: 'bg-blue-100 text-blue-800',
      green: 'bg-green-100 text-green-800',
      red: 'bg-red-100 text-red-800'
    };

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClasses[config.color]}`}>
        {config.label}
      </span>
    );
  };

  const uniqueMimeTypes = [...new Set(documents.map(doc => doc.mime_type).filter(Boolean))];
  const uniqueStatuses = [...new Set(documents.map(doc => doc.processing_status))];

  if (loading) {
    return (
      <div className="document-list bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="document-list bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <DocumentTextIcon className="h-5 w-5 mr-2 text-blue-600" />
            Documents ({filteredDocuments.length})
          </h3>
          <div className="flex items-center space-x-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <FunnelIcon className="h-4 w-4 mr-1" />
              Filters
              {showFilters ? (
                <ChevronUpIcon className="h-4 w-4 ml-1" />
              ) : (
                <ChevronDownIcon className="h-4 w-4 ml-1" />
              )}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={loadDocuments}
              disabled={loading}
            >
              Refresh
            </Button>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search documents..."
            value={filters.search}
            onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={filters.processing_status || ''}
                  onChange={(e) => setFilters(prev => ({ 
                    ...prev, 
                    processing_status: (e.target.value as "failed" | "pending" | "processing" | "processed") || undefined 
                  }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All statuses</option>
                  {uniqueStatuses.map(status => (
                    <option key={status} value={status}>
                      {formatProcessingStatus(status)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  File Type
                </label>
                <select
                  value={filters.mime_type || ''}
                  onChange={(e) => setFilters(prev => ({ 
                    ...prev, 
                    mime_type: e.target.value || undefined 
                  }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">All types</option>
                  {uniqueMimeTypes.map(mimeType => (
                    <option key={mimeType} value={mimeType}>
                      {getFileTypeInfo(mimeType!).name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sort By
                </label>
                <div className="flex space-x-2">
                  <select
                    value={filters.sort_by}
                    onChange={(e) => setFilters(prev => ({ 
                      ...prev, 
                      sort_by: e.target.value as any 
                    }))}
                    className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="created_at">Date</option>
                    <option value="filename">Name</option>
                    <option value="file_size">Size</option>
                    <option value="chunk_count">Chunks</option>
                  </select>
                  <select
                    value={filters.sort_order}
                    onChange={(e) => setFilters(prev => ({ 
                      ...prev, 
                      sort_order: e.target.value as 'asc' | 'desc' 
                    }))}
                    className="border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="desc">↓</option>
                    <option value="asc">↑</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4">
          <Alert 
            type="error" 
            message={error} 
            onClose={() => setError(null)} 
          />
        </div>
      )}

      {/* Document List */}
      <div className="divide-y divide-gray-200">
        {filteredDocuments.length === 0 ? (
          <div className="p-8 text-center">
            <DocumentTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">
              {documents.length === 0 
                ? 'No documents uploaded yet' 
                : 'No documents match your filters'
              }
            </p>
          </div>
        ) : (
          filteredDocuments.map((document) => (
            <div key={document.id} className="p-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    {document.mime_type?.includes('pdf') ? (
                      <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                        <span className="text-sm font-medium text-red-600">PDF</span>
                      </div>
                    ) : (
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <DocumentTextIcon className="h-5 w-5 text-blue-600" />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {document.filename}
                      </p>
                      {getStatusBadge(document.processing_status)}
                    </div>
                    <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                      <span>{formatFileSize(document.file_size || 0)}</span>
                      <span>{document.chunk_count} chunks</span>
                      <span>{new Date(document.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {onDocumentSelect && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => onDocumentSelect(document)}
                    >
                      <EyeIcon className="h-4 w-4 mr-1" />
                      View
                    </Button>
                  )}
                  
                  {deleteConfirm === document.id ? (
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleDelete(document.id, document.filename)}
                        disabled={deleting === document.id}
                        isLoading={deleting === document.id}
                      >
                        Confirm
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setDeleteConfirm(null)}
                        disabled={deleting === document.id}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleDelete(document.id, document.filename)}
                      disabled={deleting === document.id}
                    >
                      <TrashIcon className="h-4 w-4 mr-1" />
                      Delete
                    </Button>
                  )}
                </div>
              </div>

              {document.processing_status === 'failed' && (
                <div className="mt-2 flex items-center text-sm text-red-600">
                  <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                  Processing failed - document may be corrupted or unsupported
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default DocumentList;

