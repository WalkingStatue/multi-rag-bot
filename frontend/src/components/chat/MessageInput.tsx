/**
 * Message input component for sending chat messages
 */
import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { chatService } from '../../services/chatService';
import { chatWebSocketService } from '../../services/chatWebSocketService';
import { MessageWithStatus } from '../../types/chat';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../common/Button';
import { PaperAirplaneIcon } from '@heroicons/react/24/outline';

interface MessageInputProps {
  botId: string;
  sessionId: string;
  className?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  botId,
  sessionId,
  className = ''
}) => {
  const { user } = useAuth();
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [lastSentTime, setLastSentTime] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<number | null>(null);
  const sendingRef = useRef(false);
  
  // Minimum time between messages to prevent rate limiting (in milliseconds)
  const MIN_MESSAGE_INTERVAL = 3000; // Increased to 3 seconds
  
  const { addMessage, updateMessage, setTyping, getCurrentMessages, updateSession } = useChatStore();

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  // Handle typing indicators
  const handleTyping = () => {
    if (!chatWebSocketService.isConnected()) return;

    // Send typing indicator
    chatWebSocketService.sendTypingIndicator(true);
    setTyping(true);

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Stop typing after 1 second of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      chatWebSocketService.sendTypingIndicator(false);
      setTyping(false);
    }, 1000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim() || isSending || !user || sendingRef.current) return;

    // Check rate limiting
    const now = Date.now();
    const timeSinceLastMessage = now - lastSentTime;
    if (timeSinceLastMessage < MIN_MESSAGE_INTERVAL) {
      const waitTime = MIN_MESSAGE_INTERVAL - timeSinceLastMessage;
      console.log(`Rate limiting: waiting ${Math.ceil(waitTime / 1000)} seconds before sending`);
      
      // Show user feedback about rate limiting
      const errorMessage: MessageWithStatus = {
        id: `rate-limit-${Date.now()}`,
        session_id: sessionId,
        bot_id: botId,
        user_id: 'system',
        role: 'system',
        content: `Please wait ${Math.ceil(waitTime / 1000)} seconds before sending another message.`,
        created_at: new Date().toISOString(),
        status: 'sent'
      };
      addMessage(sessionId, errorMessage);
      return;
    }

    const messageContent = message.trim();
    setMessage('');
    setIsSending(true);
    sendingRef.current = true;
    setLastSentTime(now);

    // Stop typing indicator
    chatWebSocketService.sendTypingIndicator(false);
    setTyping(false);

    // Create temporary message for immediate UI feedback
    const tempId = `temp-${Date.now()}`;
    const tempMessage: MessageWithStatus = {
      id: '',
      tempId,
      session_id: sessionId,
      bot_id: botId,
      user_id: user.id,
      role: 'user',
      content: messageContent,
      created_at: new Date().toISOString(),
      status: 'sending'
    };

    addMessage(sessionId, tempMessage);

    try {
      // Send message to backend
      const response = await chatService.sendMessage(botId, {
        message: messageContent,
        session_id: sessionId
      });

      // Update temp message with real data
      updateMessage(sessionId, tempId, {
        id: response.metadata?.user_message_id || tempId,
        status: 'sent',
        tempId: undefined
      });

      // Auto-generate title for new conversations
      // Check if this is likely the first user message (only 1 message in session)
      const currentMessages = getCurrentMessages();
      const userMessages = currentMessages.filter(msg => msg.role === 'user');
      
      if (userMessages.length <= 1) {
        // This is the first user message, auto-generate title
        try {
          const updatedSession = await chatService.updateSessionTitleFromMessage(sessionId, messageContent);
          if (updatedSession) {
            // Update the session in the store
            updateSession(sessionId, { title: updatedSession.title });
          }
        } catch (error) {
          console.warn('Failed to auto-generate conversation title:', error);
        }
      }

      // Note: Assistant response will come through WebSocket, so we don't add it here
      // The HTTP response might contain the assistant message, but we ignore it to prevent duplicates

    } catch (error: any) {
      console.error('Failed to send message:', error);
      
      // Update temp message to show error
      updateMessage(sessionId, tempId, {
        status: 'error'
      });

      // Determine error message based on error type
      let errorContent = 'Failed to send message. Please try again.';
      
      if (error.response?.status === 429) {
        errorContent = 'Too many requests. Please wait a moment before sending another message.';
      } else if (error.code === 'ECONNABORTED') {
        errorContent = 'Request timed out. Please check your connection and try again.';
      } else if (error.response?.status >= 500) {
        errorContent = 'Server error. Please try again in a few moments.';
      }

      // Show error message
      const errorMessage: MessageWithStatus = {
        id: `error-${Date.now()}`,
        session_id: sessionId,
        bot_id: botId,
        user_id: 'system',
        role: 'system',
        content: errorContent,
        created_at: new Date().toISOString(),
        status: 'sent'
      };

      addMessage(sessionId, errorMessage);
    } finally {
      setIsSending(false);
      sendingRef.current = false;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    handleTyping();
  };

  return (
    <div className={`border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 ${className}`}>
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
            className="w-full resize-none border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent max-h-32"
            rows={1}
            disabled={isSending}
          />
        </div>
        
        <Button
          type="submit"
          disabled={!message.trim() || isSending}
          isLoading={isSending}
          variant="primary"
          size="md"
        >
          {!isSending && (
            <PaperAirplaneIcon className="w-5 h-5" />
          )}
        </Button>
      </form>
    </div>
  );
};