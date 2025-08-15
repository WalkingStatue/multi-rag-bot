/**
 * Session list component for managing conversation sessions
 */
import React, { useState } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { chatService } from '../../services/chatService';
import { BotResponse } from '../../types/bot';
import { ConversationSession } from '../../types/chat';
import { formatDistanceToNow } from 'date-fns';

interface SessionListProps {
  bot: BotResponse;
  sessions: ConversationSession[];
  onSelectSession: (sessionId: string) => Promise<void>;
  className?: string;
}

export const SessionList: React.FC<SessionListProps> = ({ 
  bot,
  sessions,
  onSelectSession,
  className = '' 
}) => {
  const {
    currentSessionId,
    addSession,
    updateSession,
    removeSession,
    setCurrentSession,
    setMessages
  } = useChatStore();

  const [isCreating, setIsCreating] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const handleCreateSession = async () => {
    if (isCreating) return;

    setIsCreating(true);
    try {
      const newSession = await chatService.createBotSession(bot.id);
      addSession(newSession);
      setCurrentSession(newSession.id);
      setMessages(newSession.id, []); // Initialize empty messages
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelectSession = async (session: ConversationSession) => {
    if (session.id === currentSessionId) return;
    await onSelectSession(session.id);
  };

  const handleEditTitle = (session: ConversationSession) => {
    setEditingSessionId(session.id);
    setEditTitle(session.title || 'Untitled Conversation');
  };

  const handleSaveTitle = async (sessionId: string) => {
    if (!editTitle.trim()) return;

    try {
      const updatedSession = await chatService.updateSession(sessionId, editTitle.trim());
      updateSession(sessionId, { title: updatedSession.title });
      setEditingSessionId(null);
      setEditTitle('');
    } catch (error) {
      console.error('Failed to update session title:', error);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
      return;
    }

    try {
      await chatService.deleteSession(sessionId);
      removeSession(sessionId);
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const formatSessionTime = (timestamp: string) => {
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
    } catch {
      return 'Unknown time';
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Create new session button */}
      <div className="p-3 border-b border-gray-200">
        <button
          onClick={handleCreateSession}
          disabled={isCreating}
          className="w-full bg-blue-600 text-white px-3 py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-sm"
        >
          {isCreating ? (
            <span className="flex items-center justify-center">
              <svg className="w-4 h-4 animate-spin mr-2" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Creating...
            </span>
          ) : (
            <span className="flex items-center justify-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Conversation
            </span>
          )}
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <div className="w-12 h-12 mx-auto mb-3 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs text-gray-400 mt-1">Start a new conversation to begin</p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group relative p-3 rounded-lg cursor-pointer transition-colors duration-200 ${
                  session.id === currentSessionId
                    ? 'bg-blue-50 border border-blue-200'
                    : 'hover:bg-gray-50 border border-transparent'
                }`}
                onClick={() => handleSelectSession(session)}
              >
                {editingSessionId === session.id ? (
                  <div className="space-y-2" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full text-sm font-medium bg-white border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleSaveTitle(session.id);
                        } else if (e.key === 'Escape') {
                          setEditingSessionId(null);
                          setEditTitle('');
                        }
                      }}
                      autoFocus
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleSaveTitle(session.id)}
                        className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setEditingSessionId(null);
                          setEditTitle('');
                        }}
                        className="text-xs bg-gray-300 text-gray-700 px-2 py-1 rounded hover:bg-gray-400"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {session.title || 'Untitled Conversation'}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">
                          {formatSessionTime(session.updated_at)}
                        </p>
                      </div>
                      
                      {/* Session actions */}
                      <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEditTitle(session);
                          }}
                          className="p-1 text-gray-400 hover:text-gray-600 rounded"
                          title="Edit title"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteSession(session.id);
                          }}
                          className="p-1 text-gray-400 hover:text-red-600 rounded"
                          title="Delete conversation"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};