/**
 * Example chat interface component showing proper error handling
 */
import React, { useState } from 'react';
import { useChatSession } from '../../hooks/useChatSession';
import { useChatMessage } from '../../hooks/useChatMessage';
import { ChatErrorDisplay } from './ChatErrorDisplay';
import { Button } from '../common/Button';
import { Input } from '../common/Input';

interface ChatInterfaceProps {
  botId: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ botId }) => {
  const [messageInput, setMessageInput] = useState('');
  
  const {
    currentSession,
    isLoading: sessionsLoading,
    error: sessionError,
    createSession
  } = useChatSession({ botId });

  const {
    sendMessage,
    isLoading: messageLoading,
    error: messageError,
    clearError
  } = useChatMessage({
    botId,
    sessionId: currentSession?.id || ''
  });

  const handleSendMessage = async () => {
    if (!messageInput.trim()) return;
    
    // Create session if none exists
    if (!currentSession) {
      await createSession();
    }
    
    await sendMessage(messageInput);
    setMessageInput('');
  };

  const handleRetryMessage = () => {
    if (messageInput.trim()) {
      sendMessage(messageInput);
    }
  };

  const isLoading = sessionsLoading || messageLoading;

  return (
    <div className="flex flex-col h-full">
      {/* Error Display */}
      {(sessionError || messageError) && (
        <div className="p-4">
          <ChatErrorDisplay
            error={messageError || sessionError}
            onRetry={messageError ? handleRetryMessage : undefined}
            onDismiss={clearError}
          />
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Messages would be rendered here */}
        <div className="text-center text-gray-500 dark:text-gray-400">
          {isLoading ? 'Loading...' : 'Start a conversation'}
        </div>
      </div>

      {/* Message Input */}
      <div className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
        <div className="flex space-x-2">
          <Input
            type="text"
            value={messageInput}
            onChange={(e) => setMessageInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || !messageInput.trim()}
            isLoading={isLoading}
            variant="primary"
            size="md"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </Button>
        </div>
      </div>
    </div>
  );
};