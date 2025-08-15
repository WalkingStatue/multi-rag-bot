/**
 * Accessibility hooks for React components
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  generateId,
  trapFocus,
  createFocusManager,
  announceToScreenReader,
  prefersReducedMotion,
  prefersHighContrast,
  handleArrowKeyNavigation,
  KEYBOARD_KEYS,
} from '../utils/accessibility';

/**
 * Hook for managing unique IDs for accessibility attributes
 */
export const useId = (prefix?: string): string => {
  const [id] = useState(() => generateId(prefix));
  return id;
};

/**
 * Hook for managing ARIA announcements
 */
export const useAnnouncer = () => {
  const announce = useCallback((
    message: string,
    priority: 'polite' | 'assertive' = 'polite'
  ) => {
    announceToScreenReader(message, priority);
  }, []);

  return { announce };
};

/**
 * Hook for managing focus trap (useful for modals, dropdowns)
 */
export const useFocusTrap = (isActive: boolean = false) => {
  const containerRef = useRef<HTMLElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (isActive && containerRef.current) {
      cleanupRef.current = trapFocus(containerRef.current);
    } else if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, [isActive]);

  return containerRef;
};

/**
 * Hook for managing focus restoration
 */
export const useFocusRestore = () => {
  const focusManager = useRef(createFocusManager());

  const saveFocus = useCallback(() => {
    focusManager.current.save();
  }, []);

  const restoreFocus = useCallback(() => {
    focusManager.current.restore();
  }, []);

  return { saveFocus, restoreFocus };
};

/**
 * Hook for keyboard navigation in lists/menus
 */
export const useKeyboardNavigation = (
  items: HTMLElement[],
  options: {
    loop?: boolean;
    orientation?: 'horizontal' | 'vertical';
    onSelect?: (index: number) => void;
  } = {}
) => {
  const [currentIndex, setCurrentIndex] = useState(-1);
  const { loop = true, orientation = 'vertical', onSelect } = options;

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const newIndex = handleArrowKeyNavigation(event, items, currentIndex, {
      loop,
      orientation,
    });

    if (newIndex !== currentIndex) {
      setCurrentIndex(newIndex);
    }

    // Handle selection
    if (event.key === KEYBOARD_KEYS.ENTER || event.key === KEYBOARD_KEYS.SPACE) {
      event.preventDefault();
      if (currentIndex >= 0 && onSelect) {
        onSelect(currentIndex);
      }
    }
  }, [items, currentIndex, loop, orientation, onSelect]);

  const setActiveIndex = useCallback((index: number) => {
    setCurrentIndex(index);
    if (items[index]) {
      items[index].focus();
    }
  }, [items]);

  return {
    currentIndex,
    setActiveIndex,
    handleKeyDown,
  };
};

/**
 * Hook for managing ARIA expanded state
 */
export const useExpanded = (initialState: boolean = false) => {
  const [isExpanded, setIsExpanded] = useState(initialState);

  const toggle = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  const expand = useCallback(() => {
    setIsExpanded(true);
  }, []);

  const collapse = useCallback(() => {
    setIsExpanded(false);
  }, []);

  return {
    isExpanded,
    toggle,
    expand,
    collapse,
    'aria-expanded': isExpanded,
  };
};

/**
 * Hook for managing ARIA selected state
 */
export const useSelected = (initialState: boolean = false) => {
  const [isSelected, setIsSelected] = useState(initialState);

  const toggle = useCallback(() => {
    setIsSelected(prev => !prev);
  }, []);

  const select = useCallback(() => {
    setIsSelected(true);
  }, []);

  const deselect = useCallback(() => {
    setIsSelected(false);
  }, []);

  return {
    isSelected,
    toggle,
    select,
    deselect,
    'aria-selected': isSelected,
  };
};

/**
 * Hook for managing ARIA pressed state (for toggle buttons)
 */
export const usePressed = (initialState: boolean = false) => {
  const [isPressed, setIsPressed] = useState(initialState);

  const toggle = useCallback(() => {
    setIsPressed(prev => !prev);
  }, []);

  const press = useCallback(() => {
    setIsPressed(true);
  }, []);

  const release = useCallback(() => {
    setIsPressed(false);
  }, []);

  return {
    isPressed,
    toggle,
    press,
    release,
    'aria-pressed': isPressed,
  };
};

/**
 * Hook for detecting user preferences
 */
export const useAccessibilityPreferences = () => {
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion);
  const [highContrast, setHighContrast] = useState(prefersHighContrast);

  useEffect(() => {
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const contrastQuery = window.matchMedia('(prefers-contrast: high)');

    const handleMotionChange = (e: MediaQueryListEvent) => {
      setReducedMotion(e.matches);
    };

    const handleContrastChange = (e: MediaQueryListEvent) => {
      setHighContrast(e.matches);
    };

    motionQuery.addEventListener('change', handleMotionChange);
    contrastQuery.addEventListener('change', handleContrastChange);

    return () => {
      motionQuery.removeEventListener('change', handleMotionChange);
      contrastQuery.removeEventListener('change', handleContrastChange);
    };
  }, []);

  return {
    prefersReducedMotion: reducedMotion,
    prefersHighContrast: highContrast,
  };
};

/**
 * Hook for managing disclosure patterns (show/hide content)
 */
export const useDisclosure = (initialState: boolean = false) => {
  const [isOpen, setIsOpen] = useState(initialState);
  const triggerId = useId('disclosure-trigger');
  const contentId = useId('disclosure-content');

  const open = useCallback(() => {
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  return {
    isOpen,
    open,
    close,
    toggle,
    triggerProps: {
      id: triggerId,
      'aria-expanded': isOpen,
      'aria-controls': contentId,
    },
    contentProps: {
      id: contentId,
      'aria-labelledby': triggerId,
      hidden: !isOpen,
    },
  };
};

/**
 * Hook for managing modal accessibility
 */
export const useModal = (isOpen: boolean = false) => {
  const modalRef = useFocusTrap(isOpen);
  const { saveFocus, restoreFocus } = useFocusRestore();
  const { announce } = useAnnouncer();
  const titleId = useId('modal-title');
  const descriptionId = useId('modal-description');

  useEffect(() => {
    if (isOpen) {
      saveFocus();
      announce('Modal opened', 'assertive');
      
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    } else {
      restoreFocus();
      announce('Modal closed', 'assertive');
      
      // Restore body scroll
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen, saveFocus, restoreFocus, announce]);

  const handleEscape = useCallback((event: KeyboardEvent) => {
    if (event.key === KEYBOARD_KEYS.ESCAPE && isOpen) {
      event.preventDefault();
      // Modal should provide onClose callback
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, handleEscape]);

  return {
    modalRef,
    titleId,
    descriptionId,
    modalProps: {
      ref: modalRef,
      role: 'dialog',
      'aria-modal': true,
      'aria-labelledby': titleId,
      'aria-describedby': descriptionId,
    },
  };
};

/**
 * Hook for managing tooltip accessibility
 */
export const useTooltip = (delay: number = 500) => {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<number | null>(null);
  const tooltipId = useId('tooltip');

  const show = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = window.setTimeout(() => {
      setIsVisible(true);
    }, delay);
  }, [delay]);

  const hide = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return {
    isVisible,
    show,
    hide,
    triggerProps: {
      'aria-describedby': isVisible ? tooltipId : undefined,
      onMouseEnter: show,
      onMouseLeave: hide,
      onFocus: show,
      onBlur: hide,
    },
    tooltipProps: {
      id: tooltipId,
      role: 'tooltip',
      hidden: !isVisible,
    },
  };
};

/**
 * Hook for managing combobox/autocomplete accessibility
 */
export const useCombobox = (options: string[] = []) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [inputValue, setInputValue] = useState('');
  const comboboxId = useId('combobox');
  const listboxId = useId('listbox');

  const filteredOptions = options.filter(option =>
    option.toLowerCase().includes(inputValue.toLowerCase())
  );

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    switch (event.key) {
      case KEYBOARD_KEYS.ARROW_DOWN:
        event.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        }
        setSelectedIndex(prev => 
          prev < filteredOptions.length - 1 ? prev + 1 : 0
        );
        break;
      case KEYBOARD_KEYS.ARROW_UP:
        event.preventDefault();
        if (!isOpen) {
          setIsOpen(true);
        }
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : filteredOptions.length - 1
        );
        break;
      case KEYBOARD_KEYS.ENTER:
        event.preventDefault();
        if (isOpen && selectedIndex >= 0) {
          setInputValue(filteredOptions[selectedIndex] || '');
          setIsOpen(false);
          setSelectedIndex(-1);
        }
        break;
      case KEYBOARD_KEYS.ESCAPE:
        event.preventDefault();
        setIsOpen(false);
        setSelectedIndex(-1);
        break;
    }
  }, [isOpen, selectedIndex, filteredOptions]);

  return {
    isOpen,
    selectedIndex,
    inputValue,
    filteredOptions,
    setInputValue,
    setIsOpen,
    handleKeyDown,
    inputProps: {
      id: comboboxId,
      role: 'combobox',
      'aria-expanded': isOpen,
      'aria-controls': listboxId,
      'aria-activedescendant': selectedIndex >= 0 ? `${listboxId}-option-${selectedIndex}` : undefined,
      autoComplete: 'off',
      value: inputValue,
      onKeyDown: handleKeyDown,
    },
    listboxProps: {
      id: listboxId,
      role: 'listbox',
      'aria-labelledby': comboboxId,
      hidden: !isOpen,
    },
  };
};

export default {
  useId,
  useAnnouncer,
  useFocusTrap,
  useFocusRestore,
  useKeyboardNavigation,
  useExpanded,
  useSelected,
  usePressed,
  useAccessibilityPreferences,
  useDisclosure,
  useModal,
  useTooltip,
  useCombobox,
};