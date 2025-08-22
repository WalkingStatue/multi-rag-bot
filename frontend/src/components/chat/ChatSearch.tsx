/**
 * Chat search component for searching conversations and messages
 */
import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useChatStore } from '../../stores/chatStore';
import { chatService } from '../../services/chatService';
import { ConversationSearchResult } from '../../types/chat';
import { formatDistanceToNow } from 'date-fns';
import { log } from '../../utils/logger';

interface ChatSearchProps {
  botId?: string;
  onResultSelect?: (result: ConversationSearchResult) => void;
  className?: string;
}

export const ChatSearch: React.FC<ChatSearchProps> = ({
  botId,
  onResultSelect,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<ConversationSearchResult[]>([]);
  const [dropdownPosition, setDropdownPosition] = useState<{ top: number; left: number; width: number } | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { uiState, setSearchQuery, setSearchResults } = useChatStore();

  // Calculate dropdown position when opened
  useEffect(() => {
    if (isOpen && searchRef.current) {
      const rect = searchRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + window.scrollY,
        left: rect.left + window.scrollX,
        width: rect.width
      });
    } else {
      setDropdownPosition(null);
    }
  }, [isOpen]);

  // Close search when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (searchRef.current && !searchRef.current.contains(target)) {
        // Also check if click is in the portal dropdown
        const dropdown = document.getElementById('search-dropdown');
        if (!dropdown || !dropdown.contains(target)) {
          setIsOpen(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = async (query: string) => {
    setSearchQuery(query);

    if (!query.trim()) {
      setResults([]);
      setSearchResults([]);
      return;
    }

    if (query.length < 2) {
      return; // Don't search for very short queries
    }

    setIsSearching(true);
    try {
      const response = await chatService.searchConversations(query, botId);
      setResults(response.results);
      setSearchResults(response.results);
    } catch (error) { log.error('Search failed:', 'ChatSearch', { error });
      setResults([]);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleResultClick = (result: ConversationSearchResult) => {
    setIsOpen(false);
    onResultSelect?.(result);
  };

  const highlightText = (text: string, query: string) => {
    if (!query.trim() || !text) return text || '';

    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} className="bg-yellow-200 dark:bg-yellow-600 dark:text-yellow-100 px-1 rounded">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div ref={searchRef} className={`relative ${className}`}>
      {/* Search input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          placeholder="Search conversations..."
          value={uiState.searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => setIsOpen(true)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent"
        />
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          {isSearching ? (
            <svg className="w-5 h-5 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          )}
        </div>
      </div>

      {/* Search results dropdown - rendered via portal */}
      {isOpen && (uiState.searchQuery.length >= 2 || results.length > 0) && dropdownPosition && createPortal(
        <div 
          id="search-dropdown"
          className="fixed z-[999999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-96 overflow-y-auto"
          style={{
            top: dropdownPosition.top + 4,
            left: dropdownPosition.left,
            width: dropdownPosition.width
          }}
        >
          {isSearching ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 dark:border-blue-400 mx-auto mb-2"></div>
              Searching...
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-gray-500 dark:text-gray-400">
              {uiState.searchQuery.length < 2 ? (
                'Type at least 2 characters to search'
              ) : (
                'No results found'
              )}
            </div>
          ) : (
            <div className="py-2">
              {results.map((result, index) => (
                <div
                  key={`${result.session_id}-${index}`}
                  onClick={() => handleResultClick(result)}
                  className="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                          {result.session_title || 'Untitled Conversation'}
                        </h4>
                        <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                          {result.bot_name}
                        </span>
                      </div>
                      
                      <div className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                        <span className="font-medium capitalize">{result.role}:</span>{' '}
                        <span className="line-clamp-2">
                          {highlightText(result.content, uiState.searchQuery)}
                        </span>
                      </div>
                      
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {formatDistanceToNow(new Date(result.created_at), { addSuffix: true })}
                        {result.relevance_score && (
                          <span className="ml-2">
                            • {Math.round(result.relevance_score * 100)}% match
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="ml-2 flex-shrink-0">
                      <svg className="w-4 h-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>,
        document.body
      )}
    </div>
  );
};
