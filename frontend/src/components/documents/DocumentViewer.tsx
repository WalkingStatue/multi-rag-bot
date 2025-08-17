/**
 * Document viewer component with chunk visualization
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  DocumentDetailResponse,
  DocumentChunkInfo,
  DocumentSearchResult,
  DocumentSearchResponse
} from '../../types/document';
import {
  fetchDocument,
  searchDocuments,
  formatFileSize,
  getFileTypeInfo
} from '../../services/documentService';
import { Button } from '../common/Button';
import { useToastHelpers } from '../common/Toast';
import {
  XMarkIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  HashtagIcon
} from '@heroicons/react/24/outline';

interface DocumentViewerProps {
  botId: string;
  documentId: string;
  onClose: () => void;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({
  botId,
  documentId,
  onClose
}) => {
  const { error: showErrorToast } = useToastHelpers();
  const [document, setDocument] = useState<DocumentDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<DocumentChunkInfo | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [currentChunkIndex, setCurrentChunkIndex] = useState(0);

  const loadDocument = useCallback(async () => {
    try {
      setLoading(true);
      const documentData = await fetchDocument(botId, documentId);
      setDocument(documentData);
      if (documentData.chunks.length > 0) {
        setSelectedChunk(documentData.chunks[0]);
        setCurrentChunkIndex(0);
      }
      setError(null);
    } catch (error) {
      const errorMessage = 'Failed to load document details.';
      setError(errorMessage);
      showErrorToast('Document Error', errorMessage);
    } finally {
      setLoading(false);
    }
  }, [botId, documentId]);

  useEffect(() => {
    loadDocument();
  }, [loadDocument]);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      setSearching(true);
      setSearchError(null);
      const response: DocumentSearchResponse = await searchDocuments(
        botId,
        searchQuery,
        10,
        documentId
      );
      setSearchResults(response.results);
    } catch (error) {
      const errorMessage = 'Search failed. Please try again.';
      setSearchError(errorMessage);
      showErrorToast('Search Error', errorMessage);
    } finally {
      setSearching(false);
    }
  }, [botId, documentId, searchQuery]);

  const navigateChunk = (direction: 'prev' | 'next') => {
    if (!document) return;

    let newIndex = currentChunkIndex;
    if (direction === 'prev' && currentChunkIndex > 0) {
      newIndex = currentChunkIndex - 1;
    } else if (direction === 'next' && currentChunkIndex < document.chunks.length - 1) {
      newIndex = currentChunkIndex + 1;
    }

    if (newIndex !== currentChunkIndex) {
      setCurrentChunkIndex(newIndex);
      setSelectedChunk(document.chunks[newIndex]);
    }
  };

  const selectChunk = (chunk: DocumentChunkInfo) => {
    setSelectedChunk(chunk);
    const index = document?.chunks.findIndex(c => c.id === chunk.id) || 0;
    setCurrentChunkIndex(index);
  };

  const highlightSearchTerm = (text: string, query: string) => {
    if (!query.trim()) return text;

    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl p-8 max-w-md w-full mx-4">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-3/4 mb-4"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2 mb-4"></div>
            <div className="h-32 bg-gray-200 dark:bg-gray-800 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40">
        <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl p-6 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center mb-4">
              <svg className="h-6 w-6 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              {error ? 'Error Loading Document' : 'Document Not Found'}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              {error || 'The requested document could not be found.'}
            </p>
            <Button onClick={onClose}>Close</Button>
          </div>
        </div>
      </div>
    );
  }

  const fileTypeInfo = getFileTypeInfo(document.mime_type || '');

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-40 p-4">
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-xl max-w-6xl w-full h-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center space-x-3">
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
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {document.filename}
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                <span>{formatFileSize(document.file_size || 0)}</span>
                <span>{document.chunk_count} chunks</span>
                <span>{fileTypeInfo.name}</span>
              </div>
            </div>
          </div>
          <Button variant="secondary" onClick={onClose} aria-label="Close document viewer">
            <XMarkIcon className="h-5 w-5" />
          </Button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar - Chunk List */}
          <div className="w-1/3 border-r border-gray-200 dark:border-gray-800 flex flex-col">
            {/* Search */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-800">
              <div className="flex space-x-2">
                <div className="relative flex-1">
                  <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search in document..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    className="h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 w-full pl-10 pr-4 py-2 placeholder:text-gray-400 focus-visible:ring focus-visible:ring-offset-0 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
                <Button
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                  isLoading={searching}
                  size="sm"
                >
                  Search
                </Button>
              </div>
              {searchError && (
                <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <p className="text-sm text-red-700 dark:text-red-300">{searchError}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Search Results or Chunk List */}
            <div className="flex-1 overflow-y-auto">
              {searchResults.length > 0 ? (
                <div className="p-4">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                    Search Results ({searchResults.length})
                  </h3>
                  <div className="space-y-2">
                    {searchResults.map((result, index) => (
                      <div
                        key={index}
                        className="p-3 border border-gray-200 dark:border-gray-800 rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/60"
                        onClick={() => {
                          // Find the chunk that contains this result
                          const chunk = document.chunks.find(c => 
                            c.content_preview.includes(result.text.substring(0, 50))
                          );
                          if (chunk) {
                            selectChunk(chunk);
                          }
                        }}
                      >
                        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                          Score: {result.score.toFixed(3)}
                        </div>
                        <div className="text-sm">
                          {highlightSearchTerm(result.text, searchQuery)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-4">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
                    Document Chunks ({document.chunks.length})
                  </h3>
                  <div className="space-y-1">
                    {document.chunks.map((chunk) => (
                      <div
                        key={chunk.id}
                        className={`p-3 rounded-lg cursor-pointer transition-colors ${
                          selectedChunk?.id === chunk.id
                            ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-900/60 border border-transparent'
                        }`}
                        onClick={() => selectChunk(chunk)}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                            Chunk {chunk.chunk_index + 1}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {chunk.content_length} chars
                          </span>
                        </div>
                        <div className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
                          {chunk.content_preview}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Main Content - Chunk Viewer */}
          <div className="flex-1 flex flex-col">
            {selectedChunk ? (
              <>
                {/* Chunk Header */}
                <div className="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/40">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 flex items-center">
                        <HashtagIcon className="h-5 w-5 mr-2 text-gray-500 dark:text-gray-400" />
                        Chunk {selectedChunk.chunk_index + 1} of {document.chunks.length}
                      </h3>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {selectedChunk.content_length} characters
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => navigateChunk('prev')}
                        disabled={currentChunkIndex === 0}
                        aria-label="Previous chunk"
                      >
                        <ChevronLeftIcon className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => navigateChunk('next')}
                        disabled={currentChunkIndex === document.chunks.length - 1}
                        aria-label="Next chunk"
                      >
                        <ChevronRightIcon className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Chunk Content */}
                <div className="flex-1 p-6 overflow-y-auto">
                  <div className="prose max-w-none">
                    <div className="whitespace-pre-wrap text-gray-800 dark:text-gray-200 leading-relaxed">
                      {searchQuery 
                        ? highlightSearchTerm(selectedChunk.content_preview, searchQuery)
                        : selectedChunk.content_preview
                      }
                    </div>
                  </div>

                  {/* Chunk Metadata */}
                  {selectedChunk.metadata && Object.keys(selectedChunk.metadata).length > 0 && (
                    <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-800">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Metadata</h4>
                      <div className="bg-gray-50 dark:bg-gray-900/40 rounded-lg p-4">
                        <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                          {JSON.stringify(selectedChunk.metadata, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <EyeIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">Select a chunk to view its content</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentViewer;