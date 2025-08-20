/**
 * Bot Integrations Page
 * 
 * Unified page with tabbed interface for widget configuration and API documentation
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { MainLayout } from '../layouts';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { botService } from '../services/botService';
import { BotWithRole } from '../types/bot';
import {
  DocumentDuplicateIcon,
  CodeBracketIcon,
  CommandLineIcon,
  KeyIcon,
  ExclamationTriangleIcon,
  CheckIcon,
  PaintBrushIcon,
  Cog6ToothIcon,
  EyeIcon,
  CubeIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline';

interface WidgetConfig {
  title: string;
  welcomeMessage: string;
  placeholderText: string;
  primaryColor: string;
  backgroundColor: string;
  textColor: string;
  borderRadius: string;
  fontFamily: string;
  position: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  size: 'small' | 'medium' | 'large';
  showBranding: boolean;
}

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

interface InteractiveWidgetPreviewProps {
  config: WidgetConfig;
  botId: string | undefined;
}

const InteractiveWidgetPreview: React.FC<InteractiveWidgetPreviewProps> = ({ config, botId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const sizeOptions = {
    small: { width: '300px', height: '400px' },
    medium: { width: '350px', height: '500px' },
    large: { width: '400px', height: '600px' }
  };

  const positionOptions = {
    'bottom-right': { bottom: '20px', right: '20px' },
    'bottom-left': { bottom: '20px', left: '20px' },
    'top-right': { top: '20px', right: '20px' },
    'top-left': { top: '20px', left: '20px' }
  };

  // Initialize with welcome message and create new session when widget opens
  React.useEffect(() => {
    if (isOpen && !conversationId && botId) {
      initializeSession();
    }
  }, [isOpen, botId]);

  // Initialize welcome message
  React.useEffect(() => {
    if (config.welcomeMessage) {
      setMessages([{
        id: 'welcome',
        content: config.welcomeMessage,
        role: 'assistant',
        timestamp: new Date()
      }]);
    }
  }, [config.welcomeMessage]);

  // Auto scroll to bottom
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const initializeSession = async () => {
    if (!botId) return;
    
    try {
      setSessionError(null);
      // Create a new conversation session for the preview
      // This simulates what happens when a real user opens the widget
      const sessionId = `preview_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setConversationId(sessionId);
    } catch (error) {
      console.error('Failed to initialize preview session:', error);
      setSessionError('Failed to connect to bot. Preview will show simulated responses.');
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !botId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue.trim(),
      role: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const messageContent = inputValue.trim();
    setInputValue('');
    setIsTyping(true);

    try {
      // Send message to the actual bot
      const response = await fetch(`/api/v1/bots/${botId}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}` // Use user's auth token
        },
        body: JSON.stringify({
          message: messageContent,
          conversation_id: conversationId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success && data.data) {
        const botMessage: Message = {
          id: data.data.message_id || (Date.now() + 1).toString(),
          content: data.data.message || data.data.response || 'No response received',
          role: 'assistant',
          timestamp: new Date()
        };

        setMessages(prev => [...prev, botMessage]);
        
        // Update conversation ID if provided
        if (data.data.conversation_id) {
          setConversationId(data.data.conversation_id);
        }
      } else {
        throw new Error(data.error || 'Failed to get bot response');
      }
    } catch (error) {
      console.error('Error sending message to bot:', error);
      
      // Fallback to simulated response if API fails
      const fallbackResponses = [
        "I'm having trouble connecting to the bot right now. This is a preview response.",
        "Sorry, there seems to be a connection issue. In the real widget, your bot would respond here.",
        "Preview mode: Your bot would normally respond to your message here.",
        "Connection error - but your widget is working! This shows how error handling works."
      ];
      
      const fallbackMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: fallbackResponses[Math.floor(Math.random() * fallbackResponses.length)],
        role: 'assistant',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, fallbackMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  // Reset session when widget closes
  const handleClose = () => {
    setIsOpen(false);
    setConversationId(null);
    setMessages(config.welcomeMessage ? [{
      id: 'welcome',
      content: config.welcomeMessage,
      role: 'assistant',
      timestamp: new Date()
    }] : []);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="relative bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-800 dark:to-gray-900 rounded-lg overflow-hidden" style={{ height: '600px' }}>
      {/* Simulated website content */}
      <div className="absolute inset-0 p-8">
        <div className="text-center">
          <h3 className="text-xl font-bold text-gray-800 dark:text-gray-200 mb-2">Your Website</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">Click the chat button to test the widget!</p>
          <div className="bg-white dark:bg-gray-700 rounded-lg p-6 shadow-sm max-w-md mx-auto">
            <h4 className="font-semibold text-gray-800 dark:text-gray-200 mb-2">Sample Content</h4>
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-4">
              Your website content goes here. The chat widget will appear as a floating button.
            </p>
            <div className="space-y-2">
              <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded w-3/4"></div>
              <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded w-1/2"></div>
              <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Widget Container */}
      <div 
        className="absolute z-50"
        style={positionOptions[config.position]}
      >
        {/* Widget Button */}
        <div 
          className="w-14 h-14 rounded-full shadow-lg cursor-pointer flex items-center justify-center text-white transition-all duration-200 hover:scale-110"
          style={{ backgroundColor: config.primaryColor }}
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" fill="currentColor"/>
            </svg>
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="currentColor"/>
            </svg>
          )}
        </div>

        {/* Widget Window */}
        {isOpen && (
          <div 
            className="absolute shadow-2xl border border-gray-200 dark:border-gray-600 flex flex-col transition-all duration-300 transform"
            style={{
              backgroundColor: config.backgroundColor,
              borderRadius: config.borderRadius,
              width: sizeOptions[config.size].width,
              height: sizeOptions[config.size].height,
              bottom: '70px',
              right: config.position.includes('right') ? '0px' : undefined,
              left: config.position.includes('left') ? '0px' : undefined,
            }}
          >
            {/* Header */}
            <div 
              className="px-4 py-3 text-white flex justify-between items-center flex-shrink-0"
              style={{ backgroundColor: config.primaryColor }}
            >
              <div className="flex items-center space-x-2">
                <h4 className="font-medium text-sm truncate">{config.title}</h4>
                {conversationId && (
                  <div className="w-2 h-2 bg-green-400 rounded-full" title="Connected to bot"></div>
                )}
                {sessionError && (
                  <div className="w-2 h-2 bg-yellow-400 rounded-full" title="Preview mode - simulated responses"></div>
                )}
              </div>
              <button 
                className="text-white hover:text-gray-200 ml-2 w-6 h-6 flex items-center justify-center"
                onClick={handleClose}
              >
                ×
              </button>
            </div>

            {/* Messages Area */}
            <div className="flex-1 p-4 overflow-y-auto" style={{ maxHeight: 'calc(100% - 140px)' }}>
              {sessionError && (
                <div className="mb-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-xs text-yellow-700 dark:text-yellow-300">
                  <strong>Preview Mode:</strong> {sessionError}
                </div>
              )}
              {messages.map((message) => (
                <div key={message.id} className={`mb-3 ${message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}`}>
                  <div className="max-w-xs">
                    <div 
                      className="px-3 py-2 text-sm break-words"
                      style={{ 
                        backgroundColor: message.role === 'user' ? config.primaryColor : '#f1f3f4',
                        color: message.role === 'user' ? 'white' : config.textColor,
                        borderRadius: config.borderRadius,
                        ...(message.role === 'assistant' && message.id === '1' ? {
                          borderLeft: `4px solid ${config.primaryColor}`,
                          backgroundColor: '#f8f9fa'
                        } : {})
                      }}
                    >
                      {message.content}
                    </div>
                    <div className="text-xs text-gray-500 mt-1 px-1">
                      {formatTime(message.timestamp)}
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex justify-start mb-3">
                  <div 
                    className="px-3 py-2 text-sm"
                    style={{ 
                      backgroundColor: '#f1f3f4',
                      borderRadius: config.borderRadius
                    }}
                  >
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-600 flex-shrink-0">
              <div className="flex space-x-2">
                <input 
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={!botId ? "Bot ID required for real chat" : config.placeholderText}
                  disabled={!botId}
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 text-sm focus:outline-none focus:ring-2 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ 
                    borderRadius: '20px',
                    focusRingColor: config.primaryColor
                  }}
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isTyping}
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white flex-shrink-0 transition-opacity disabled:opacity-50"
                  style={{ backgroundColor: config.primaryColor }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                    <path d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z" fill="currentColor"/>
                  </svg>
                </button>
              </div>
            </div>

            {/* Branding */}
            {config.showBranding && (
              <div className="px-4 py-2 text-xs text-gray-500 text-center border-t border-gray-200 dark:border-gray-600 flex-shrink-0">
                Powered by ChatBot
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

type TabType = 'widget' | 'api' | 'iframe';

export const BotIntegrationsPage: React.FC = () => {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [bot, setBot] = useState<BotWithRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  // Get active tab from URL params, default to 'widget'
  const [activeTab, setActiveTab] = useState<TabType>((searchParams.get('tab') as TabType) || 'widget');

  const [config, setConfig] = useState<WidgetConfig>({
    title: 'Chat Assistant',
    welcomeMessage: 'Hello! How can I help you today?',
    placeholderText: 'Type your message...',
    primaryColor: '#007bff',
    backgroundColor: '#ffffff',
    textColor: '#333333',
    borderRadius: '8px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    position: 'bottom-right',
    size: 'medium',
    showBranding: true
  });

  useEffect(() => {
    if (botId) {
      loadBot();
    }
  }, [botId]);

  // Update URL when tab changes
  useEffect(() => {
    setSearchParams({ tab: activeTab });
  }, [activeTab, setSearchParams]);

  const loadBot = async () => {
    if (!botId) return;

    try {
      setIsLoading(true);
      const userBots = await botService.getUserBots();
      const foundBot = userBots.find(b => b.bot.id === botId);

      if (!foundBot) {
        setError('Bot not found or you do not have access to it.');
        return;
      }

      setBot(foundBot);
      setConfig(prev => ({
        ...prev,
        title: foundBot.bot.name + ' Assistant'
      }));
    } catch (err) {
      console.error('Failed to load bot:', err);
      setError('Failed to load bot information.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async (text: string, section: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(section);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const baseUrl = window.location.origin;
  const apiBaseUrl = baseUrl.replace(':5173', ':8000'); // Adjust for dev environment
  const embedUrl = `${baseUrl}/bots/${botId}/chat?embed=1`;
  const iframeSnippet = `<iframe src="${embedUrl}" width="100%" height="600" style="border: 1px solid #e5e7eb; border-radius: 8px;" allow="clipboard-read; clipboard-write"></iframe>`;

  const generateWidgetCode = () => {
    return `<!-- Chat Widget -->
<script>
  window.CHAT_WIDGET_CONFIG = ${JSON.stringify(config, null, 2)};
  window.CHAT_WIDGET_BOT_ID = '${botId}';
  window.CHAT_WIDGET_API_URL = '${apiBaseUrl}/api';
  window.CHAT_WIDGET_WS_URL = '${apiBaseUrl.replace('http', 'ws')}/api';
</script>
<script src="${baseUrl}/widget.js" data-widget-key="${botId}"></script>`;
  };

  const sizeOptions = {
    small: { width: '300px', height: '400px' },
    medium: { width: '350px', height: '500px' },
    large: { width: '400px', height: '600px' }
  };

  const positionOptions = {
    'bottom-right': { bottom: '20px', right: '20px' },
    'bottom-left': { bottom: '20px', left: '20px' },
    'top-right': { top: '20px', right: '20px' },
    'top-left': { top: '20px', left: '20px' }
  };

  const tabs = [
    { id: 'widget', name: 'Widget Configuration', icon: CubeIcon },
    { id: 'iframe', name: 'Iframe Embed', icon: DocumentTextIcon },
    { id: 'api', name: 'API Documentation', icon: CodeBracketIcon }
  ];

  if (isLoading) {
    return (
      <ProtectedRoute>
        <MainLayout
          title="Bot Integrations"
          subtitle="Loading..."
          showBackButton
          onBackClick={() => navigate('/bots')}
        >
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (error || !bot) {
    return (
      <ProtectedRoute>
        <MainLayout
          title="Bot Integrations"
          subtitle="Error loading bot"
          showBackButton
          onBackClick={() => navigate('/bots')}
        >
          <Card padding="lg" className="text-center">
            <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-red-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
              {error || 'Bot not found'}
            </h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">
              Please check the bot ID and try again.
            </p>
            <Button
              onClick={() => navigate('/bots')}
              className="mt-4"
            >
              Back to Bots
            </Button>
          </Card>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  const renderWidgetTab = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Configuration Panel */}
      <div className="space-y-6">
        {/* Basic Settings */}
        <Card title="Basic Settings" icon={<Cog6ToothIcon className="h-5 w-5" />} padding="md">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Widget Title
              </label>
              <input
                type="text"
                value={config.title}
                onChange={(e) => setConfig(prev => ({ ...prev, title: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100"
                placeholder="Chat Assistant"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Welcome Message
              </label>
              <textarea
                value={config.welcomeMessage}
                onChange={(e) => setConfig(prev => ({ ...prev, welcomeMessage: e.target.value }))}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100"
                placeholder="Hello! How can I help you today?"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Input Placeholder
              </label>
              <input
                type="text"
                value={config.placeholderText}
                onChange={(e) => setConfig(prev => ({ ...prev, placeholderText: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100"
                placeholder="Type your message..."
              />
            </div>
          </div>
        </Card>

        {/* Appearance Settings */}
        <Card title="Appearance" icon={<PaintBrushIcon className="h-5 w-5" />} padding="md">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Primary Color
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={config.primaryColor}
                    onChange={(e) => setConfig(prev => ({ ...prev, primaryColor: e.target.value }))}
                    className="w-12 h-10 border border-gray-300 dark:border-gray-600 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={config.primaryColor}
                    onChange={(e) => setConfig(prev => ({ ...prev, primaryColor: e.target.value }))}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100 font-mono text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Background Color
                </label>
                <div className="flex items-center space-x-2">
                  <input
                    type="color"
                    value={config.backgroundColor}
                    onChange={(e) => setConfig(prev => ({ ...prev, backgroundColor: e.target.value }))}
                    className="w-12 h-10 border border-gray-300 dark:border-gray-600 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={config.backgroundColor}
                    onChange={(e) => setConfig(prev => ({ ...prev, backgroundColor: e.target.value }))}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100 font-mono text-sm"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Text Color
              </label>
              <div className="flex items-center space-x-2">
                <input
                  type="color"
                  value={config.textColor}
                  onChange={(e) => setConfig(prev => ({ ...prev, textColor: e.target.value }))}
                  className="w-12 h-10 border border-gray-300 dark:border-gray-600 rounded cursor-pointer"
                />
                <input
                  type="text"
                  value={config.textColor}
                  onChange={(e) => setConfig(prev => ({ ...prev, textColor: e.target.value }))}
                  className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100 font-mono text-sm"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Border Radius
                </label>
                <select
                  value={config.borderRadius}
                  onChange={(e) => setConfig(prev => ({ ...prev, borderRadius: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option value="0px">None (0px)</option>
                  <option value="4px">Small (4px)</option>
                  <option value="8px">Medium (8px)</option>
                  <option value="12px">Large (12px)</option>
                  <option value="16px">Extra Large (16px)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Size
                </label>
                <select
                  value={config.size}
                  onChange={(e) => setConfig(prev => ({ ...prev, size: e.target.value as 'small' | 'medium' | 'large' }))}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option value="small">Small (300x400)</option>
                  <option value="medium">Medium (350x500)</option>
                  <option value="large">Large (400x600)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Position
              </label>
              <select
                value={config.position}
                onChange={(e) => setConfig(prev => ({ ...prev, position: e.target.value as any }))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-gray-100"
              >
                <option value="bottom-right">Bottom Right</option>
                <option value="bottom-left">Bottom Left</option>
                <option value="top-right">Top Right</option>
                <option value="top-left">Top Left</option>
              </select>
            </div>

            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.showBranding}
                  onChange={(e) => setConfig(prev => ({ ...prev, showBranding: e.target.checked }))}
                  className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-300 focus:ring focus:ring-primary-200 focus:ring-opacity-50"
                />
                <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                  Show "Powered by" branding
                </span>
              </label>
            </div>
          </div>
        </Card>

        {/* Generated Code */}
        <Card title="Embed Code" padding="md">
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Copy this code and paste it into your website's HTML, just before the closing &lt;/body&gt; tag.
            </p>
            <div className="relative">
              <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm max-h-64">
                <code>{generateWidgetCode()}</code>
              </pre>
              <button
                onClick={() => copyToClipboard(generateWidgetCode(), 'embed-code')}
                className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
              >
                {copiedSection === 'embed-code' ? (
                  <CheckIcon className="h-4 w-4 text-green-400" />
                ) : (
                  <DocumentDuplicateIcon className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </Card>
      </div>

      {/* Preview Panel */}
      <div className="space-y-6">
        <Card title="Live Preview" icon={<EyeIcon className="h-5 w-5" />} padding="md">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                See how your widget will look on a website
              </p>
              <Button
                onClick={() => setShowPreview(!showPreview)}
                variant="outline"
                size="sm"
              >
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </Button>
            </div>

            {showPreview && <InteractiveWidgetPreview config={config} botId={botId} />}
          </div>
        </Card>

        {/* Quick Actions */}
        <Card title="Quick Actions" padding="md">
          <div className="space-y-3">
            <Button
              onClick={() => window.open(`/widget.js?${new URLSearchParams({ botId: botId || '' })}`, '_blank')}
              variant="outline"
              className="w-full"
            >
              Test Widget Directly
            </Button>
            <Button
              onClick={() => navigate(`/bots/${botId}/chat`)}
              variant="outline"
              className="w-full"
            >
              Test Bot Chat
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );

  const renderIframeTab = () => (
    <div className="space-y-6">
      <Card title="Iframe Embed" padding="md">
        <div className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            Use this iframe code to embed the full chat interface directly into your website. This provides a complete chat experience within your page.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">Embed Code</h4>
              <div className="relative">
                <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                  <code>{iframeSnippet}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(iframeSnippet, 'iframe')}
                  className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                >
                  {copiedSection === 'iframe' ? (
                    <CheckIcon className="h-4 w-4 text-green-400" />
                  ) : (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-3">Preview</h4>
              <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
                <iframe
                  src={embedUrl}
                  width="100%"
                  height="400"
                  style={{ border: 'none' }}
                  title="Chat Preview"
                />
              </div>
            </div>
          </div>

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-4">
            <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
              Iframe vs Widget
            </h4>
            <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
              <li>• <strong>Iframe:</strong> Full chat interface embedded in your page</li>
              <li>• <strong>Widget:</strong> Floating chat button with popup window</li>
              <li>• <strong>Iframe:</strong> Takes up dedicated space on your page</li>
              <li>• <strong>Widget:</strong> Overlays on top of your content</li>
            </ul>
          </div>

          <div className="flex space-x-4">
            <Button
              onClick={() => window.open(embedUrl, '_blank')}
              variant="outline"
            >
              Open in New Tab
            </Button>
            <Button
              onClick={() => setActiveTab('widget')}
              variant="outline"
            >
              Try Widget Instead
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
  const renderApiTab = () => {
    const curlExample = `curl -X POST "${apiBaseUrl}/api/v1/bots/${botId}/chat" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "message": "Hello, how can you help me?",
    "conversation_id": "optional-conversation-id"
  }'`;

    const pythonExample = `import requests

# Bot configuration
BOT_ID = "${botId}"
API_KEY = "YOUR_API_KEY"
BASE_URL = "${apiBaseUrl}/api/v1"

# Send a message to the bot
def chat_with_bot(message, conversation_id=None):
    url = f"{BASE_URL}/bots/{BOT_ID}/chat"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Example usage
result = chat_with_bot("What can you help me with?")
print(result)`;

    const javascriptExample = `const BOT_ID = '${botId}';
const API_KEY = 'YOUR_API_KEY';
const BASE_URL = '${apiBaseUrl}/api/v1';

// Function to send message to bot
async function chatWithBot(message, conversationId = null) {
  const response = await fetch(\`\${BASE_URL}/bots/\${BOT_ID}/chat\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${API_KEY}\`
    },
    body: JSON.stringify({
      message: message,
      ...(conversationId && { conversation_id: conversationId })
    })
  });
  
  return await response.json();
}

// Example usage
chatWithBot('Hello, how can you help me?')
  .then(result => console.log(result))
  .catch(error => console.error('Error:', error));`;

    const endpoints = [
      {
        method: 'POST',
        endpoint: `/api/v1/bots/${botId}/chat`,
        description: 'Send a message to the bot and receive a response',
        parameters: [
          { name: 'message', type: 'string', required: true, description: 'The message to send to the bot' },
          { name: 'conversation_id', type: 'string', required: false, description: 'Optional conversation ID for context' }
        ]
      },
      {
        method: 'GET',
        endpoint: `/api/v1/bots/${botId}/conversations`,
        description: 'Get list of conversations with this bot',
        parameters: [
          { name: 'limit', type: 'number', required: false, description: 'Maximum number of conversations to return (default: 50)' },
          { name: 'offset', type: 'number', required: false, description: 'Number of conversations to skip (default: 0)' }
        ]
      },
      {
        method: 'GET',
        endpoint: `/api/v1/bots/${botId}/conversations/{conversation_id}`,
        description: 'Get messages from a specific conversation',
        parameters: [
          { name: 'conversation_id', type: 'string', required: true, description: 'The conversation ID' }
        ]
      },
      {
        method: 'GET',
        endpoint: `/api/v1/bots/${botId}`,
        description: 'Get bot information and configuration',
        parameters: []
      }
    ];

    return (
      <div className="space-y-8">
        {/* API Authentication */}
        <Card title="Authentication" padding="md">
          <div className="space-y-4">
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
              <div className="flex">
                <KeyIcon className="h-5 w-5 text-yellow-400 mt-0.5" />
                <div className="ml-3">
                  <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    API Key Required
                  </h4>
                  <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                    You'll need an API key to authenticate requests. Contact your administrator to obtain one.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Authorization Header</h4>
              <div className="relative">
                <code className="block bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm font-mono">
                  Authorization: Bearer YOUR_API_KEY
                </code>
                <button
                  onClick={() => copyToClipboard('Authorization: Bearer YOUR_API_KEY', 'auth-header')}
                  className="absolute top-2 right-2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {copiedSection === 'auth-header' ? (
                    <CheckIcon className="h-4 w-4 text-green-500" />
                  ) : (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </Card>

        {/* API Endpoints */}
        <Card title="Available Endpoints" padding="md">
          <div className="space-y-6">
            {endpoints.map((endpoint, index) => (
              <div key={index} className="border-b border-gray-200 dark:border-gray-700 last:border-b-0 pb-6 last:pb-0">
                <div className="flex items-center space-x-2 mb-2">
                  <span className={`px-2 py-1 text-xs font-mono font-semibold rounded ${endpoint.method === 'GET'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                    }`}>
                    {endpoint.method}
                  </span>
                  <code className="text-sm font-mono text-gray-700 dark:text-gray-300">
                    {endpoint.endpoint}
                  </code>
                </div>
                <p className="text-gray-600 dark:text-gray-400 mb-3">{endpoint.description}</p>

                {endpoint.parameters.length > 0 && (
                  <div>
                    <h5 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Parameters</h5>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead>
                          <tr>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Name
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Type
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Required
                            </th>
                            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                              Description
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                          {endpoint.parameters.map((param, paramIndex) => (
                            <tr key={paramIndex}>
                              <td className="px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100">
                                {param.name}
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                                {param.type}
                              </td>
                              <td className="px-3 py-2 text-sm">
                                <span className={`px-2 py-1 text-xs rounded ${param.required
                                    ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                    : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                                  }`}>
                                  {param.required ? 'Required' : 'Optional'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                                {param.description}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>

        {/* Code Examples */}
        <Card title="Code Examples" padding="md">
          <div className="space-y-6">
            {/* cURL Example */}
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <CommandLineIcon className="h-5 w-5 text-gray-500" />
                <h4 className="font-medium text-gray-900 dark:text-gray-100">cURL</h4>
              </div>
              <div className="relative">
                <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                  <code>{curlExample}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(curlExample, 'curl')}
                  className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                >
                  {copiedSection === 'curl' ? (
                    <CheckIcon className="h-4 w-4 text-green-400" />
                  ) : (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Python Example */}
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <CodeBracketIcon className="h-5 w-5 text-gray-500" />
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Python</h4>
              </div>
              <div className="relative">
                <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                  <code>{pythonExample}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(pythonExample, 'python')}
                  className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                >
                  {copiedSection === 'python' ? (
                    <CheckIcon className="h-4 w-4 text-green-400" />
                  ) : (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* JavaScript Example */}
            <div>
              <div className="flex items-center space-x-2 mb-3">
                <CodeBracketIcon className="h-5 w-5 text-gray-500" />
                <h4 className="font-medium text-gray-900 dark:text-gray-100">JavaScript</h4>
              </div>
              <div className="relative">
                <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                  <code>{javascriptExample}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(javascriptExample, 'javascript')}
                  className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                >
                  {copiedSection === 'javascript' ? (
                    <CheckIcon className="h-4 w-4 text-green-400" />
                  ) : (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </div>
        </Card>

        {/* Response Format */}
        <Card title="Response Format" padding="md">
          <div className="space-y-4">
            <p className="text-gray-600 dark:text-gray-400">
              All API responses follow this format:
            </p>
            <div className="relative">
              <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`{
  "success": true,
  "data": {
    "message": "Bot response message here",
    "conversation_id": "conv_123456789",
    "message_id": "msg_987654321",
    "timestamp": "2024-08-16T16:12:03Z",
    "model_used": "${bot.bot.llm_model}",
    "tokens_used": {
      "prompt": 45,
      "completion": 32,
      "total": 77
    }
  },
  "error": null
}`}</code>
              </pre>
              <button
                onClick={() => copyToClipboard(`{
  "success": true,
  "data": {
    "message": "Bot response message here",
    "conversation_id": "conv_123456789",
    "message_id": "msg_987654321",
    "timestamp": "2024-08-16T16:12:03Z",
    "model_used": "${bot.bot.llm_model}",
    "tokens_used": {
      "prompt": 45,
      "completion": 32,
      "total": 77
    }
  },
  "error": null
}`, 'response-format')}
                className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
              >
                {copiedSection === 'response-format' ? (
                  <CheckIcon className="h-4 w-4 text-green-400" />
                ) : (
                  <DocumentDuplicateIcon className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>
        </Card>

        {/* Rate Limits & Guidelines */}
        <Card title="Guidelines & Limitations" padding="md">
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Rate Limits</h4>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <li>• 100 requests per minute per API key</li>
                  <li>• 1000 requests per hour per API key</li>
                  <li>• Rate limits reset every hour</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Best Practices</h4>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <li>• Include conversation_id for context</li>
                  <li>• Handle rate limit responses (429)</li>
                  <li>• Implement retry logic with backoff</li>
                  <li>• Keep messages under 4000 characters</li>
                </ul>
              </div>
            </div>
          </div>
        </Card>
      </div>
    );
  };

  return (
    <ProtectedRoute>
      <MainLayout
        title={`${bot.bot.name} - Integrations`}
        subtitle="Configure widgets, embed options, and API access"
        showBackButton
        onBackClick={() => navigate('/bots')}
      >
        <div className="space-y-6">
          {/* Bot Information */}
          <Card title="Bot Information" padding="md">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Bot Name</h4>
                <p className="text-gray-600 dark:text-gray-400">{bot.bot.name}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Bot ID</h4>
                <p className="text-gray-600 dark:text-gray-400 font-mono text-sm">{bot.bot.id}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Provider</h4>
                <p className="text-gray-600 dark:text-gray-400">{bot.bot.llm_provider}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Model</h4>
                <p className="text-gray-600 dark:text-gray-400">{bot.bot.llm_model}</p>
              </div>
            </div>
          </Card>

          {/* Tabs */}
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as TabType)}
                    className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${activeTab === tab.id
                        ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                      }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span>{tab.name}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="mt-6">
            {activeTab === 'widget' && renderWidgetTab()}
            {activeTab === 'iframe' && renderIframeTab()}
            {activeTab === 'api' && renderApiTab()}
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
};