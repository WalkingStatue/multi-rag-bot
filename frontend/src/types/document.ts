/**
 * Document-related TypeScript types for frontend
 */

export interface DocumentBase {
  filename: string;
}

export interface DocumentUpload {
  bot_id: string;
  file: File;
  process_immediately?: boolean;
}

export interface DocumentResponse extends DocumentBase {
  id: string;
  bot_id: string;
  uploaded_by?: string;
  file_size?: number;
  mime_type?: string;
  chunk_count: number;
  created_at: string;
  processing_status: 'pending' | 'processing' | 'processed' | 'failed';
}

export interface DocumentChunkInfo {
  id: string;
  chunk_index: number;
  content_preview: string;
  content_length: number;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface DocumentDetailResponse extends DocumentResponse {
  chunks: DocumentChunkInfo[];
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
  skip: number;
  limit: number;
}

export interface DocumentProcessingResponse {
  document_id: string;
  filename: string;
  chunks_created: number;
  embeddings_stored: number;
  processing_stats: Record<string, any>;
  document_metadata: Record<string, any>;
}

export interface DocumentSearchResult {
  id: string;
  score: number;
  text: string;
  metadata: Record<string, any>;
  document_info?: Record<string, any>;
}

export interface DocumentSearchResponse {
  query: string;
  results: DocumentSearchResult[];
  total_results: number;
}

export interface DocumentStatsResponse {
  total_documents: number;
  total_file_size: number;
  total_chunks: number;
  average_chunks_per_document: number;
  file_type_distribution: Record<string, number>;
  vector_store_stats: Record<string, any>;
}

export interface DocumentChunkResponse {
  id: string;
  document_id: string;
  bot_id: string;
  chunk_index: number;
  content: string;
  embedding_id?: string;
  chunk_metadata?: Record<string, any>;
  created_at: string;
}

export interface DocumentReprocessResponse {
  document_id: string;
  filename: string;
  previous_chunk_count: number;
  new_chunk_count: number;
  processing_stats: Record<string, any>;
}

// UI-specific types
export interface DocumentUploadState {
  uploading: boolean;
  progress: number;
  error?: string;
}

export interface DocumentListFilters {
  search?: string;
  mime_type?: string;
  processing_status?: 'pending' | 'processing' | 'processed' | 'failed';
  sort_by?: 'filename' | 'created_at' | 'file_size' | 'chunk_count';
  sort_order?: 'asc' | 'desc';
  uploaded_by?: string;
}

export interface DocumentViewerState {
  selectedDocument?: DocumentDetailResponse;
  selectedChunk?: DocumentChunkInfo;
  searchQuery?: string;
  searchResults?: DocumentSearchResult[];
}

export interface DocumentDeleteConfirmation {
  document_id: string;
  filename: string;
  chunk_count: number;
  file_size?: number;
}

export interface BulkDocumentAction {
  action: 'delete' | 'reprocess';
  document_ids: string[];
}

// File upload validation
export interface FileValidationResult {
  valid: boolean;
  error?: string;
  warnings?: string[];
}

// Supported file types
export const SUPPORTED_FILE_TYPES = {
  'application/pdf': { extension: '.pdf', name: 'PDF Document' },
  'text/plain': { extension: '.txt', name: 'Text Document' },
  'text/markdown': { extension: '.md', name: 'Markdown Document' },
  'application/msword': { extension: '.doc', name: 'Word Document' },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { 
    extension: '.docx', 
    name: 'Word Document' 
  }
} as const;

export type SupportedMimeType = keyof typeof SUPPORTED_FILE_TYPES;

// File size limits
export const FILE_SIZE_LIMITS = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  MAX_TOTAL_SIZE: 100 * 1024 * 1024, // 100MB per bot
} as const;

// Processing status colors and icons
export const PROCESSING_STATUS_CONFIG = {
  pending: { color: 'yellow', icon: 'clock', label: 'Pending' },
  processing: { color: 'blue', icon: 'loader', label: 'Processing' },
  processed: { color: 'green', icon: 'check', label: 'Processed' },
  failed: { color: 'red', icon: 'x', label: 'Failed' }
} as const;
