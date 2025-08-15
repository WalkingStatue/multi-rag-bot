/**
 * Document service for handling backend API calls
 */

import { apiClient } from './api';
import {
  DocumentListResponse,
  DocumentDetailResponse,
  DocumentResponse,
  DocumentProcessingResponse,
  DocumentSearchResponse,
  DocumentStatsResponse,
  DocumentChunkResponse,
  DocumentReprocessResponse,
  FileValidationResult,
  SUPPORTED_FILE_TYPES,
  FILE_SIZE_LIMITS,
  SupportedMimeType
} from '../types/document';

class DocumentService {
  
  /**
   * Validate a file before upload
   */
  validateFile(file: File): FileValidationResult {
    const warnings: string[] = [];
    
    // Check file size
    if (file.size > FILE_SIZE_LIMITS.MAX_FILE_SIZE) {
      return {
        valid: false,
        error: `File size ${this.formatFileSize(file.size)} exceeds maximum allowed size of ${this.formatFileSize(FILE_SIZE_LIMITS.MAX_FILE_SIZE)}`
      };
    }
    
    // Check file type
    if (!Object.keys(SUPPORTED_FILE_TYPES).includes(file.type)) {
      return {
        valid: false,
        error: `File type ${file.type} is not supported. Supported types: ${Object.values(SUPPORTED_FILE_TYPES).map(t => t.extension).join(', ')}`
      };
    }
    
    // Add warnings for large files
    if (file.size > FILE_SIZE_LIMITS.MAX_FILE_SIZE * 0.8) {
      warnings.push('Large file may take longer to process');
    }
    
    return {
      valid: true,
      warnings: warnings.length > 0 ? warnings : undefined
    };
  }
  
  /**
   * Upload a document to a bot
   */
  async uploadDocument(botId: string, file: File, processImmediately: boolean = true): Promise<DocumentResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post(
      `/bots/${botId}/documents/?process_immediately=${processImmediately}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    
    return response.data;
  }
  
  /**
   * Upload multiple documents
   */
  async uploadDocuments(botId: string, files: File[], processImmediately: boolean = true): Promise<DocumentResponse[]> {
    const uploadPromises = files.map(file => this.uploadDocument(botId, file, processImmediately));
    return Promise.all(uploadPromises);
  }
  
  /**
   * Get list of documents for a bot
   */
  async getDocuments(botId: string, skip: number = 0, limit: number = 100): Promise<DocumentListResponse> {
    const response = await apiClient.get(`/bots/${botId}/documents/?skip=${skip}&limit=${limit}`);
    return response.data;
  }
  
  /**
   * Get detailed information about a document
   */
  async getDocument(botId: string, documentId: string): Promise<DocumentDetailResponse> {
    const response = await apiClient.get(`/bots/${botId}/documents/${documentId}`);
    return response.data;
  }
  
  /**
   * Delete a document
   */
  async deleteDocument(botId: string, documentId: string): Promise<void> {
    await apiClient.delete(`/bots/${botId}/documents/${documentId}`);
  }
  
  /**
   * Process a document (extract text, chunk, generate embeddings)
   */
  async processDocument(botId: string, documentId: string): Promise<DocumentProcessingResponse> {
    const response = await apiClient.post(`/bots/${botId}/documents/${documentId}/process`);
    return response.data;
  }
  
  /**
   * Search document content
   */
  async searchDocuments(
    botId: string, 
    query: string, 
    topK: number = 10, 
    documentFilter?: string
  ): Promise<DocumentSearchResponse> {
    if (!query.trim()) {
      throw new Error('Search query cannot be empty');
    }

    let url = `/bots/${botId}/documents/search?query=${encodeURIComponent(query)}&top_k=${topK}`;
    if (documentFilter) {
      url += `&document_filter=${documentFilter}`;
    }
    
    try {
      const response = await apiClient.get(url);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('No documents found for search');
      } else if (error.response?.status === 400) {
        throw new Error('Invalid search query');
      }
      throw new Error('Search failed. Please try again.');
    }
  }

  /**
   * Get document chunks with content
   */
  async getDocumentChunks(botId: string, documentId: string): Promise<DocumentChunkResponse[]> {
    try {
      const response = await apiClient.get(`/bots/${botId}/documents/${documentId}/chunks`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Document not found');
      }
      throw new Error('Failed to load document chunks');
    }
  }

  /**
   * Reprocess a document
   */
  async reprocessDocument(botId: string, documentId: string): Promise<DocumentReprocessResponse> {
    try {
      const response = await apiClient.post(`/bots/${botId}/documents/${documentId}/reprocess`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        throw new Error('Document not found');
      } else if (error.response?.status === 409) {
        throw new Error('Document is already being processed');
      }
      throw new Error('Failed to reprocess document');
    }
  }
  
  /**
   * Get document statistics for a bot
   */
  async getDocumentStats(botId: string): Promise<DocumentStatsResponse> {
    const response = await apiClient.get(`/bots/${botId}/documents/stats`);
    return response.data;
  }
  
  /**
   * Format file size for display
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  /**
   * Get file type info from MIME type
   */
  getFileTypeInfo(mimeType: string) {
    return SUPPORTED_FILE_TYPES[mimeType as SupportedMimeType] || { 
      extension: '.unknown', 
      name: 'Unknown' 
    };
  }
  
  /**
   * Format processing status for display
   */
  formatProcessingStatus(status: string): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }
}

// Export a singleton instance
export const documentService = new DocumentService();

// Export individual methods for convenience
export const {
  validateFile,
  uploadDocument,
  uploadDocuments,
  getDocuments: fetchDocumentList,
  getDocument: fetchDocument,
  deleteDocument,
  processDocument,
  searchDocuments,
  getDocumentStats: fetchDocumentStats,
  getDocumentChunks: fetchDocumentChunks,
  reprocessDocument,
  formatFileSize,
  getFileTypeInfo,
  formatProcessingStatus
} = documentService;
