/**
 * Message list component for displaying chat messages
 */
import React, { useEffect, useRef } from 'react';
import { MessageWithStatus } from '../../types/chat';
import { MessageBubble } from './MessageBubble';

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

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    const scrollToBottom = () => {
      if (containerRef.current) {
        const container = containerRef.current;
        
        console.log('MessageList scroll before:', {
          scrollTop: container.scrollTop,
          scrollHeight: container.scrollHeight,
          clientHeight: container.clientHeight,
          messagesCount: messages.length
        });
        
        // Force scroll to bottom
        container.scrollTop = container.scrollHeight;
        
        console.log('MessageList scroll after:', {
          scrollTop: container.scrollTop,
          scrollHeight: container.scrollHeight,
          clientHeight: container.clientHeight
        });
        
        // Also try using scrollTo for better browser compatibility
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        });
      }
    };

    // Use setTimeout to ensure DOM is fully updated
    const timeoutId = setTimeout(scrollToBottom, 100);
    
    return () => clearTimeout(timeoutId);
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className={`flex-1 flex items-center justify-center text-gray-500 ${className}`}>
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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