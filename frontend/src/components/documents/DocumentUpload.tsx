/**
 * Enhanced document upload component with drag-and-drop functionality
 */

import React, { useState, useRef, useCallback } from 'react';
import {
  DocumentResponse,
  DocumentUploadState,
  FileValidationResult,
  SUPPORTED_FILE_TYPES,
  FILE_SIZE_LIMITS
} from '../../types/document';
import { 
  uploadDocument, 
  uploadDocuments, 
  validateFile, 
  formatFileSize 
} from '../../services/documentService';
import { Alert } from '../common/Alert';
import { Button } from '../common/Button';
import { 
  DocumentArrowUpIcon, 
  XMarkIcon, 

  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline';

interface DocumentUploadProps {
  botId: string;
  onUploadComplete?: (documents: DocumentResponse[]) => void;
  onUploadError?: (error: string) => void;
  multiple?: boolean;
  processImmediately?: boolean;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  botId,
  onUploadComplete,
  onUploadError,
  multiple = true,
  processImmediately = true
}) => {
  const [uploadState, setUploadState] = useState<DocumentUploadState>({
    uploading: false,
    progress: 0
  });
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [validationWarnings, setValidationWarnings] = useState<Record<string, string[]>>({});
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFiles = useCallback((files: File[]): { valid: File[], invalid: File[], errors: Record<string, string>, warnings: Record<string, string[]> } => {
    const valid: File[] = [];
    const invalid: File[] = [];
    const errors: Record<string, string> = {};
    const warnings: Record<string, string[]> = {};

    files.forEach(file => {
      const result: FileValidationResult = validateFile(file);
      if (result.valid) {
        valid.push(file);
        if (result.warnings) {
          warnings[file.name] = result.warnings;
        }
      } else {
        invalid.push(file);
        if (result.error) {
          errors[file.name] = result.error;
        }
      }
    });

    return { valid, invalid, errors, warnings };
  }, []);

  const handleFileSelection = useCallback((files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const { valid, errors, warnings } = validateFiles(fileArray);

    setSelectedFiles(valid);
    setValidationErrors(errors);
    setValidationWarnings(warnings);
  }, [validateFiles]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    handleFileSelection(files);
  }, [handleFileSelection]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelection(e.target.files);
  }, [handleFileSelection]);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;

    setUploadState({ uploading: true, progress: 0 });

    try {
      let uploadedDocuments: DocumentResponse[];

      if (selectedFiles.length === 1) {
        // Single file upload
        const document = await uploadDocument(botId, selectedFiles[0], processImmediately);
        uploadedDocuments = [document];
      } else {
        // Multiple file upload
        uploadedDocuments = await uploadDocuments(botId, selectedFiles, processImmediately);
      }

      setUploadState({ uploading: false, progress: 100 });
      setSelectedFiles([]);
      setValidationErrors({});
      setValidationWarnings({});

      if (onUploadComplete) {
        onUploadComplete(uploadedDocuments);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setUploadState({ uploading: false, progress: 0, error: errorMessage });
      
      if (onUploadError) {
        onUploadError(errorMessage);
      }
    }
  }, [botId, selectedFiles, processImmediately, onUploadComplete, onUploadError]);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearAll = useCallback(() => {
    setSelectedFiles([]);
    setValidationErrors({});
    setValidationWarnings({});
    setUploadState({ uploading: false, progress: 0 });
  }, []);

  const openFileDialog = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const supportedExtensions = Object.values(SUPPORTED_FILE_TYPES).map(t => t.extension).join(', ');
  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);

  return (
    <div className="document-upload bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="upload-header mb-6">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <DocumentArrowUpIcon className="h-5 w-5 mr-2 text-blue-600" />
          Upload Documents
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Supported formats: {supportedExtensions} | Max size: {formatFileSize(FILE_SIZE_LIMITS.MAX_FILE_SIZE)} per file
        </p>
      </div>

      {/* Drag and Drop Area */}
      <div
        className={`
          upload-dropzone relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200
          ${dragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
          }
          ${uploadState.uploading ? 'pointer-events-none opacity-75' : ''}
        `}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={Object.keys(SUPPORTED_FILE_TYPES).join(',')}
          onChange={handleFileInputChange}
          className="hidden"
        />

        <div className="upload-content">
          {uploadState.uploading ? (
            <div className="upload-progress">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-700 font-medium">Uploading documents...</p>
              {uploadState.progress > 0 && (
                <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                    style={{ width: `${uploadState.progress}%` }}
                  ></div>
                </div>
              )}
            </div>
          ) : (
            <div className="drop-message">
              <DocumentArrowUpIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-lg text-gray-700 mb-2">
                {dragActive 
                  ? 'Drop files here...' 
                  : 'Drag and drop files here, or click to select'
                }
              </p>
              <p className="text-sm text-gray-500">
                {multiple ? 'Multiple files allowed' : 'Single file only'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Upload Error */}
      {uploadState.error && (
        <Alert type="error" message={uploadState.error} className="mt-4" />
      )}

      {/* Validation Errors */}
      {Object.keys(validationErrors).length > 0 && (
        <div className="validation-errors mt-4">
          <Alert 
            type="error" 
            message={
              <div>
                <strong>Some files cannot be uploaded:</strong>
                <ul className="list-disc list-inside mt-2">
                  {Object.entries(validationErrors).map(([filename, error]) => (
                    <li key={filename}>{filename}: {error}</li>
                  ))}
                </ul>
              </div>
            } 
          />
        </div>
      )}

      {/* Validation Warnings */}
      {Object.keys(validationWarnings).length > 0 && (
        <div className="validation-warnings mt-4">
          <Alert 
            type="warning" 
            message={
              <div>
                <strong>Warnings:</strong>
                <ul className="list-disc list-inside mt-2">
                  {Object.entries(validationWarnings).map(([filename, warnings]) => (
                    <li key={filename}>
                      {filename}: {warnings.join(', ')}
                    </li>
                  ))}
                </ul>
              </div>
            } 
          />
        </div>
      )}

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div className="selected-files mt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-md font-medium text-gray-900">
              Selected Files ({selectedFiles.length})
            </h4>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Total size: {formatFileSize(totalSize)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={clearAll}
                disabled={uploadState.uploading}
              >
                Clear All
              </Button>
            </div>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div 
                key={`${file.name}-${index}`} 
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    {file.type.includes('pdf') ? (
                      <div className="w-8 h-8 bg-red-100 rounded flex items-center justify-center">
                        <span className="text-xs font-medium text-red-600">PDF</span>
                      </div>
                    ) : (
                      <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
                        <span className="text-xs font-medium text-blue-600">TXT</span>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                  {validationWarnings[file.name] && (
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
                  )}
                </div>
                <button
                  onClick={() => removeFile(index)}
                  disabled={uploadState.uploading}
                  className="flex-shrink-0 p-1 text-gray-400 hover:text-red-500 disabled:opacity-50"
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Actions */}
      {selectedFiles.length > 0 && (
        <div className="upload-actions mt-6 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={processImmediately}
                  onChange={() => {
                    // This would need to be passed up to parent component
                    // For now, we'll keep it as a visual indicator
                  }}
                  disabled={uploadState.uploading}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-700">Process immediately</span>
              </label>
            </div>
            
            <Button
              onClick={handleUpload}
              disabled={uploadState.uploading || selectedFiles.length === 0}
              isLoading={uploadState.uploading}
              className="min-w-[140px]"
            >
              {uploadState.uploading 
                ? 'Uploading...' 
                : `Upload ${selectedFiles.length} Document${selectedFiles.length > 1 ? 's' : ''}`
              }
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;
