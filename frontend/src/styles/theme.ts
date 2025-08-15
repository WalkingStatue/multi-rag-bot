// Centralized theme configuration
export const theme = {
  colors: {
    // Primary color palette
    primary: {
      50: '#EEF2FF',
      100: '#E0E7FF',
      200: '#C7D2FE',
      300: '#A5B4FC',
      400: '#818CF8',
      500: '#6366F1',
      600: '#4F46E5',
      700: '#4338CA',
      800: '#3730A3',
      900: '#312E81',
    },
    // Accent color palette
    accent: {
      50: '#F5F3FF',
      100: '#EDE9FE',
      200: '#DDD6FE',
      300: '#C4B5FD',
      400: '#A78BFA',
      500: '#8B5CF6',
      600: '#7C3AED',
      700: '#6D28D9',
      800: '#5B21B6',
      900: '#4C1D95',
    },
    // Success color
    success: {
      50: '#ECFDF5',
      100: '#D1FAE5',
      200: '#A7F3D0',
      300: '#6EE7B7',
      400: '#34D399',
      500: '#10B981',
      600: '#059669',
      700: '#047857',
      800: '#065F46',
      900: '#064E3B',
    },
    // Warning color
    warning: {
      50: '#FFF7ED',
      100: '#FEF3C7',
      200: '#FDE68A',
      300: '#FCD34D',
      400: '#FBBF24',
      500: '#F59E0B',
      600: '#D97706',
      700: '#B45309',
      800: '#92400E',
      900: '#78350F',
    },
    // Danger/Error color
    danger: {
      50: '#FEF2F2',
      100: '#FEE2E2',
      200: '#FECACA',
      300: '#FCA5A5',
      400: '#F87171',
      500: '#EF4444',
      600: '#E11D48',
      700: '#B91C1C',
      800: '#991B1B',
      900: '#7F1D1D',
    },
    // Neutral color palette
    neutral: {
      50: '#F8FAFC',
      100: '#F1F5F9',
      200: '#E2E8F0',
      300: '#CBD5E1',
      400: '#94A3B8',
      500: '#64748B',
      600: '#475569',
      700: '#334155',
      800: '#1E293B',
      900: '#0F172A',
    },
    // Background colors
    background: {
      light: '#F8FAFC',
      dark: '#0B1220',
    },
    // Surface colors
    surface: {
      light: '#FFFFFF',
      dark: '#0F172A',
    },
  },
  // Typography
  typography: {
    fontFamily: {
      sans: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", sans-serif',
      mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
      '4xl': '2.25rem',
      '5xl': '3rem',
      '6xl': '3.75rem',
    },
    fontWeight: {
      thin: '100',
      extralight: '200',
      light: '300',
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
      extrabold: '800',
      black: '900',
    },
    lineHeight: {
      none: '1',
      tight: '1.25',
      snug: '1.375',
      normal: '1.5',
      relaxed: '1.625',
      loose: '2',
    },
  },
  // Spacing
  spacing: {
    px: '1px',
    0: '0px',
    0.5: '0.125rem',
    1: '0.25rem',
    1.5: '0.375rem',
    2: '0.5rem',
    2.5: '0.625rem',
    3: '0.75rem',
    3.5: '0.875rem',
    4: '1rem',
    5: '1.25rem',
    6: '1.5rem',
    7: '1.75rem',
    8: '2rem',
    9: '2.25rem',
    10: '2.5rem',
    11: '2.75rem',
    12: '3rem',
    14: '3.5rem',
    16: '4rem',
    20: '5rem',
    24: '6rem',
    28: '7rem',
    32: '8rem',
    36: '9rem',
    40: '10rem',
    44: '11rem',
    48: '12rem',
    52: '13rem',
    56: '14rem',
    60: '15rem',
    64: '16rem',
    72: '18rem',
    80: '20rem',
    96: '24rem',
  },
  // Border radius
  borderRadius: {
    none: '0px',
    sm: '0.125rem',
    DEFAULT: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    '2xl': '1rem',
    '3xl': '1.5rem',
    full: '9999px',
  },
  // Shadows
  boxShadow: {
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
    '2xl': '0 25px 50px -12px rgb(0 0 0 / 0.25)',
    inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
    none: 'none',
  },
  // Transitions
  transition: {
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
    },
    timing: {
      linear: 'linear',
      in: 'cubic-bezier(0.4, 0, 1, 1)',
      out: 'cubic-bezier(0, 0, 0.2, 1)',
      inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  },
};

// Theme utilities
export const getThemeColor = (color: string, shade: number | string = 500) => {
  return `var(--${color}-${shade})`;
};

export const getThemeValue = (category: string, key: string) => {
  return `var(--${category}-${key})`;
};

// CSS variables for the theme
export const themeCSSVariables = `
:root {
  /* Primary colors */
  --primary-50: ${theme.colors.primary[50]};
  --primary-100: ${theme.colors.primary[100]};
  --primary-200: ${theme.colors.primary[200]};
  --primary-300: ${theme.colors.primary[300]};
  --primary-400: ${theme.colors.primary[400]};
  --primary-500: ${theme.colors.primary[500]};
  --primary-600: ${theme.colors.primary[600]};
  --primary-700: ${theme.colors.primary[700]};
  --primary-800: ${theme.colors.primary[800]};
  --primary-900: ${theme.colors.primary[900]};
  
  /* Accent colors */
  --accent-50: ${theme.colors.accent[50]};
  --accent-100: ${theme.colors.accent[100]};
  --accent-200: ${theme.colors.accent[200]};
  --accent-300: ${theme.colors.accent[300]};
  --accent-400: ${theme.colors.accent[400]};
  --accent-500: ${theme.colors.accent[500]};
  --accent-600: ${theme.colors.accent[600]};
  --accent-700: ${theme.colors.accent[700]};
  --accent-800: ${theme.colors.accent[800]};
  --accent-900: ${theme.colors.accent[900]};
  
  /* Success colors */
  --success-50: ${theme.colors.success[50]};
  --success-100: ${theme.colors.success[100]};
  --success-200: ${theme.colors.success[200]};
  --success-300: ${theme.colors.success[300]};
  --success-400: ${theme.colors.success[400]};
  --success-500: ${theme.colors.success[500]};
  --success-600: ${theme.colors.success[600]};
  --success-700: ${theme.colors.success[700]};
  --success-800: ${theme.colors.success[800]};
  --success-900: ${theme.colors.success[900]};
  
  /* Warning colors */
  --warning-50: ${theme.colors.warning[50]};
  --warning-100: ${theme.colors.warning[100]};
  --warning-200: ${theme.colors.warning[200]};
  --warning-300: ${theme.colors.warning[300]};
  --warning-400: ${theme.colors.warning[400]};
  --warning-500: ${theme.colors.warning[500]};
  --warning-600: ${theme.colors.warning[600]};
  --warning-700: ${theme.colors.warning[700]};
  --warning-800: ${theme.colors.warning[800]};
  --warning-900: ${theme.colors.warning[900]};
  
  /* Danger colors */
  --danger-50: ${theme.colors.danger[50]};
  --danger-100: ${theme.colors.danger[100]};
  --danger-200: ${theme.colors.danger[200]};
  --danger-300: ${theme.colors.danger[300]};
  --danger-400: ${theme.colors.danger[400]};
  --danger-500: ${theme.colors.danger[500]};
  --danger-600: ${theme.colors.danger[600]};
  --danger-700: ${theme.colors.danger[700]};
  --danger-800: ${theme.colors.danger[800]};
  --danger-900: ${theme.colors.danger[900]};
  
  /* Neutral colors */
  --neutral-50: ${theme.colors.neutral[50]};
  --neutral-100: ${theme.colors.neutral[100]};
  --neutral-200: ${theme.colors.neutral[200]};
  --neutral-300: ${theme.colors.neutral[300]};
  --neutral-400: ${theme.colors.neutral[400]};
  --neutral-500: ${theme.colors.neutral[500]};
  --neutral-600: ${theme.colors.neutral[600]};
  --neutral-700: ${theme.colors.neutral[700]};
  --neutral-800: ${theme.colors.neutral[800]};
  --neutral-900: ${theme.colors.neutral[900]};
  
  /* Background colors */
  --bg-light: ${theme.colors.background.light};
  --bg-dark: ${theme.colors.background.dark};
  --surface-light: ${theme.colors.surface.light};
  --surface-dark: ${theme.colors.surface.dark};
  
  /* Typography */
  --font-sans: ${theme.typography.fontFamily.sans};
  --font-mono: ${theme.typography.fontFamily.mono};
  
  /* Transitions */
  --transition-fast: ${theme.transition.duration.fast} ${theme.transition.timing.inOut};
  --transition-normal: ${theme.transition.duration.normal} ${theme.transition.timing.inOut};
  --transition-slow: ${theme.transition.duration.slow} ${theme.transition.timing.inOut};
}

.dark {
  --bg: var(--bg-dark);
  --surface: var(--surface-dark);
}

.light {
  --bg: var(--bg-light);
  --surface: var(--surface-light);
}
`;

export default theme;