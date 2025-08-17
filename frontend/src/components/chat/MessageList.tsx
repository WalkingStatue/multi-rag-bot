/**
 * Message list component for displaying chat messages
 */
import React, { useEffect, useRef, useCallback, useState } from 'react';
import { MessageWithStatus } from '../../types/chat';
import { MessageBubble } from './MessageBubble';
import { useChatStore } from '../../stores/chatStore';

interface MessageListProps {
  messages: MessageWithStatus[];
  className?: string;
}

export const MessageList: React.FC<MessageListProps> = ({ 
  messages, 
  className = '' 
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const [lastScrolledToMessage, setLastScrolledToMessage] = useState<string | null>(null);
  
  const { highlightedMessageId, clearHighlightedMessage } = useChatStore();

  // Callback to register message refs
  const setMessageRef = useCallback((messageId: string, element: HTMLDivElement | null) => {
    if (element) {
      messageRefs.current.set(messageId, element);
    } else {
      messageRefs.current.delete(messageId);
    }
  }, []);

  // Scroll to a specific message
  const scrollToMessage = useCallback((messageId: string) => {
    const messageElement = messageRefs.current.get(messageId);
    const container = containerRef.current;
    
    if (messageElement && container) {
      // Calculate offset to center the message in the viewport
      const containerRect = container.getBoundingClientRect();
      const messageRect = messageElement.getBoundingClientRect();
      const containerScrollTop = container.scrollTop;
      const messageOffsetTop = messageElement.offsetTop;
      const containerHeight = container.clientHeight;
      const messageHeight = messageRect.height;
      
      // Center the message in the viewport
      const targetScrollTop = messageOffsetTop - (containerHeight / 2) + (messageHeight / 2);
      
      container.scrollTo({
        top: targetScrollTop,
        behavior: 'smooth'
      });
      
      setLastScrolledToMessage(messageId);
    }
  }, []);

  // Handle scrolling to highlighted message
  useEffect(() => {
    if (highlightedMessageId && highlightedMessageId !== lastScrolledToMessage) {
      // Small delay to ensure message refs are updated
      const timer = setTimeout(() => {
        scrollToMessage(highlightedMessageId);
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [highlightedMessageId, lastScrolledToMessage, scrollToMessage]);

  // Auto-scroll to bottom when new messages arrive (but only if not viewing a specific message)
  useEffect(() => {
    const scrollToBottom = () => {
      if (containerRef.current && !highlightedMessageId) {
        const container = containerRef.current;
        
        // Force scroll to bottom
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        });
      }
    };

    // Use setTimeout to ensure DOM is fully updated
    const timeoutId = setTimeout(scrollToBottom, 100);
    
    return () => clearTimeout(timeoutId);
  }, [messages, highlightedMessageId]);

  // Clear scroll tracking when highlight is cleared
  useEffect(() => {
    if (!highlightedMessageId) {
      setLastScrolledToMessage(null);
    }
  }, [highlightedMessageId]);

  if (messages.length === 0) {
    return (
      <div className={`flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400 ${className}`}>
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <p className="text-lg font-medium mb-1">Start a conversation</p>
          <p className="text-sm">Send a message to begin chatting with this bot</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`flex-1 overflow-y-auto p-4 space-y-4 min-h-0 max-h-full chat-messages ${className}`}
    >
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;
        const showTimestamp = index === 0 || 
          (index > 0 && 
           new Date(message.created_at).getTime() - 
           new Date(messages[index - 1].created_at).getTime() > 300000); // 5 minutes

        return (
          <MessageBubble
            key={message.id || message.tempId || `msg-${index}`}
            ref={(el) => {
              if (message.id) {
                setMessageRef(message.id, el);
              }
            }}
            message={message}
            showTimestamp={showTimestamp}
            isLastMessage={isLastMessage}
          />
        );
      })}
      <div ref={messagesEndRef} />
    </div>
  );
};