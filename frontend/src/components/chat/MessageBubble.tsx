/**
 * Individual message bubble component
 */
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { MessageWithStatus } from '../../types/chat';

interface MessageBubbleProps {
  message: MessageWithStatus;
  showTimestamp?: boolean;
  isLastMessage?: boolean;
  className?: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  showTimestamp = false,
  // isLastMessage = false,
  className = ''
}) => {
  // const { user } = useAuth();
  const [showDetails, setShowDetails] = useState(false);
  
  const isUser = message.role === 'user';
  // const isOwn = message.user_id === user?.id;
  const isSystem = message.role === 'system';

  const getStatusIcon = () => {
    switch (message.status) {
      case 'sending':
        return (
          <svg className="w-4 h-4 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'sent':
        return (
          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      default:
        return null;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      if (diffMins < 1) return 'just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString();
    } catch {
      return 'Unknown time';
    }
  };

  if (isSystem) {
    return (
      <div className={`flex justify-center ${className}`}>
        <div className="bg-gray-100 text-gray-600 text-sm px-3 py-1 rounded-full">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} ${className}`}>
      <div className={`max-w-xs lg:max-w-md ${isUser ? 'order-2' : 'order-1'}`}>
        {showTimestamp && (
          <div className="text-xs text-gray-500 text-center mb-2">
            {formatTimestamp(message.created_at)}
          </div>
        )}
        
        <div
          className={`px-4 py-2 rounded-lg cursor-pointer transition-all duration-200 ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-sm'
              : 'bg-gray-100 text-gray-900 rounded-bl-sm'
          } ${showDetails ? 'shadow-lg' : 'hover:shadow-md'}`}
          onClick={() => setShowDetails(!showDetails)}
        >
          <div className="break-words">
            {isUser ? (
              <div className="whitespace-pre-wrap">{message.content}</div>
            ) : (
              <ReactMarkdown 
                className="prose prose-sm max-w-none"
                components={{
                  // Custom styling for markdown elements in chat context
                  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 ml-2">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 ml-2">{children}</ol>,
                  li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 text-white">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold mb-2 text-white">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1 text-white">{children}</h3>,
                  code: ({ children, className }) => {
                    const isInline = !className;
                    return isInline ? (
                      <code className={`px-1 py-0.5 rounded text-xs font-mono ${
                        isUser 
                          ? 'bg-blue-500 text-blue-100' 
                          : 'bg-gray-200 text-gray-800'
                      }`}>
                        {children}
                      </code>
                    ) : (
                      <code className={`block p-2 rounded text-xs font-mono whitespace-pre-wrap overflow-x-auto mt-2 ${
                        isUser 
                          ? 'bg-blue-500 text-blue-100' 
                          : 'bg-gray-200 text-gray-800'
                      }`}>
                        {children}
                      </code>
                    );
                  },
                  pre: ({ children }) => (
                    <pre className={`p-2 rounded text-xs font-mono whitespace-pre-wrap overflow-x-auto mt-2 ${
                      isUser 
                        ? 'bg-blue-500 text-blue-100' 
                        : 'bg-gray-200 text-gray-800'
                    }`}>
                      {children}
                    </pre>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className={`border-l-4 pl-3 italic mb-2 ${
                      isUser 
                        ? 'border-blue-300 text-blue-100' 
                        : 'border-gray-300 text-gray-600'
                    }`}>
                      {children}
                    </blockquote>
                  ),
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  a: ({ children, href }) => (
                    <a 
                      href={href} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className={`underline hover:no-underline ${
                        isUser 
                          ? 'text-blue-200 hover:text-blue-100' 
                          : 'text-blue-600 hover:text-blue-800'
                      }`}
                    >
                      {children}
                    </a>
                  ),
                  // Handle tables if they appear
                  table: ({ children }) => (
                    <div className="overflow-x-auto mt-2 mb-2">
                      <table className={`min-w-full text-xs ${
                        isUser ? 'text-white' : 'text-gray-900'
                      }`}>
                        {children}
                      </table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className={`px-2 py-1 border font-semibold ${
                      isUser 
                        ? 'border-blue-400 bg-blue-500' 
                        : 'border-gray-300 bg-gray-100'
                    }`}>
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className={`px-2 py-1 border ${
                      isUser 
                        ? 'border-blue-400' 
                        : 'border-gray-300'
                    }`}>
                      {children}
                    </td>
                  )
                }}
              >
                {message.content}
              </ReactMarkdown>
            )}
          </div>
          
          {/* Message metadata */}
          {message.message_metadata?.chunks_used && message.message_metadata.chunks_used.length > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
              <span className="inline-flex items-center">
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Used {message.message_metadata.chunks_used.length} document{message.message_metadata.chunks_used.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
          
          <div className="flex items-center justify-between mt-1">
            <span className="text-xs opacity-70">
              {formatTimestamp(message.created_at)}
            </span>
            {isUser && getStatusIcon()}
          </div>
        </div>

        {/* Expanded details */}
        {showDetails && message.message_metadata && (
          <div className="mt-2 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
            {message.message_metadata.processing_time && (
              <div className="mb-1">
                Processing time: {message.message_metadata.processing_time.toFixed(2)}s
              </div>
            )}
            {message.message_metadata.llm_provider && (
              <div className="mb-1">
                Provider: {message.message_metadata.llm_provider} ({message.message_metadata.llm_model})
              </div>
            )}
            {message.message_metadata.chunks_count && (
              <div className="mb-1">
                Documents used: {message.message_metadata.chunks_count}
              </div>
            )}
            {message.id && (
              <div className="text-gray-400">
                ID: {message.id}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};