/**
 * Accessible Modal Component
 * Demonstrates proper accessibility implementation
 */

import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useModal, useAccessibilityPreferences } from '../../hooks/useAccessibility';
import { KEYBOARD_KEYS } from '../../utils/accessibility';

export interface AccessibleModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const AccessibleModal: React.FC<AccessibleModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  className = '',
  closeOnOverlayClick = true,
  closeOnEscape = true,
  size = 'md',
}) => {
  const { modalRef, titleId, descriptionId, modalProps } = useModal(isOpen);
  const { prefersReducedMotion } = useAccessibilityPreferences();

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === KEYBOARD_KEYS.ESCAPE && closeOnEscape && isOpen) {
        event.preventDefault();
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, closeOnEscape, onClose]);

  // Handle overlay click
  const handleOverlayClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget && closeOnOverlayClick) {
      onClose();
    }
  };

  if (!isOpen) {
    return null;
  }

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
  };

  const animationClass = prefersReducedMotion ? '' : 'animate-fade-in';

  const modalContent = (
    <div
      className={`modal-overlay ${animationClass}`}
      onClick={handleOverlayClick}
      role="presentation"
    >
      <div
        ref={modalRef as React.RefObject<HTMLDivElement>}
        role="dialog"
        aria-modal={true}
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className={`modal ${sizeClasses[size]} ${className}`}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <h2 id={titleId} className="modal-title">
            {title}
          </h2>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label="Close modal"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        </div>

        {/* Modal Description (if provided) */}
        {description && (
          <div id={descriptionId} className="modal-description sr-only">
            {description}
          </div>
        )}

        {/* Modal Content */}
        <div className="modal-content">
          {children}
        </div>
      </div>
    </div>
  );

  // Render modal in portal to avoid z-index issues
  return createPortal(modalContent, document.body);
};

// Example usage component
export const ModalExample: React.FC = () => {
  const [isOpen, setIsOpen] = React.useState(false);

  return (
    <div>
      <button
        type="button"
        className="btn btn-primary"
        onClick={() => setIsOpen(true)}
      >
        Open Modal
      </button>

      <AccessibleModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Example Modal"
        description="This is an example of an accessible modal dialog"
        size="md"
      >
        <div className="space-y-4">
          <p>
            This modal demonstrates proper accessibility features including:
          </p>
          <ul className="list-disc list-inside space-y-2">
            <li>Focus trapping within the modal</li>
            <li>Focus restoration when closed</li>
            <li>Keyboard navigation support</li>
            <li>Screen reader announcements</li>
            <li>Proper ARIA attributes</li>
            <li>Escape key handling</li>
          </ul>
          
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                alert('Action confirmed!');
                setIsOpen(false);
              }}
            >
              Confirm
            </button>
          </div>
        </div>
      </AccessibleModal>
    </div>
  );
};

export default AccessibleModal;