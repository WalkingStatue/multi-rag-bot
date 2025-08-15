# Theme Guide

This document outlines the theme system used in the Multi-Bot RAG Platform frontend.

## Color Palette

The theme uses a consistent color palette based on Tailwind CSS naming conventions with additional semantic colors.

### Primary Colors
- `primary-50` to `primary-900`: Main brand color variations
- Used for primary actions, links, and highlights

### Accent Colors
- `accent-50` to `accent-900`: Secondary brand color variations
- Used for secondary actions and complementary elements

### Semantic Colors
- `success`: Green tones for success states and positive actions
- `warning`: Amber tones for warning states
- `danger`: Red tones for error states and destructive actions
- `neutral`: Gray tones for general UI elements

### Background Colors
- `bg-light`: Light background color (#F8FAFC)
- `bg-dark`: Dark background color (#0B1220)
- `surface-light`: Light surface color (#FFFFFF)
- `surface-dark`: Dark surface color (#0F172A)

## Typography

The application uses the Inter font family with a comprehensive set of font sizes and weights.

### Font Families
- `font-sans`: Inter with system font fallbacks
- `font-mono`: Monospace font stack for code

### Font Sizes
- `xs`: 0.75rem
- `sm`: 0.875rem
- `base`: 1rem
- `lg`: 1.125rem
- `xl`: 1.25rem
- `2xl`: 1.5rem
- `3xl`: 1.875rem
- `4xl`: 2.25rem
- `5xl`: 3rem
- `6xl`: 3.75rem

## Spacing

The theme uses a consistent spacing scale based on 0.25rem increments:
- `px`: 1px
- `0`: 0px
- `0.5`: 0.125rem
- `1`: 0.25rem
- `2`: 0.5rem
- ... up to `96`: 24rem

## Border Radius

- `none`: 0px
- `sm`: 0.125rem
- `DEFAULT`: 0.25rem
- `md`: 0.375rem
- `lg`: 0.5rem
- `xl`: 0.75rem
- `2xl`: 1rem
- `3xl`: 1.5rem
- `full`: 9999px

## Shadows

- `sm`: Small shadow
- `DEFAULT`: Default shadow
- `md`: Medium shadow
- `lg`: Large shadow
- `xl`: Extra large shadow
- `2xl`: 2x extra large shadow
- `inner`: Inner shadow
- `none`: No shadow

## Transitions

### Duration
- `fast`: 150ms
- `normal`: 300ms
- `slow`: 500ms

### Timing Functions
- `linear`: Linear timing
- `in`: Ease in
- `out`: Ease out
- `inOut`: Ease in out

## CSS Variables

All theme values are available as CSS variables for consistent usage across the application:

```css
:root {
  --primary-50: #EEF2FF;
  --primary-100: #E0E7FF;
  --primary-200: #C7D2FE;
  --primary-300: #A5B4FC;
  --primary-400: #818CF8;
  --primary-500: #6366F1;
  --primary-600: #4F46E5;
  --primary-700: #4338CA;
  --primary-800: #3730A3;
  --primary-900: #312E81;
  
  /* ... other color variables ... */
  
  --font-sans: Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 500ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

## Dark Mode

The theme supports dark mode through the `dark` class on the root element. CSS variables automatically switch to appropriate dark mode values.

## Usage Examples

### Using Colors
```jsx
<div className="bg-primary-500 text-white">Primary Button</div>
<div className="bg-neutral-200 dark:bg-neutral-800">Card</div>
```

### Using Typography
```jsx
<h1 className="text-2xl font-bold">Heading</h1>
<p className="text-base text-neutral-700 dark:text-neutral-300">Body text</p>
```

### Using Transitions
```jsx
<button className="transition-colors duration-150">Button</button>
<div className="transition-all duration-300">Animated element</div>
```

## Component Styling Guidelines

1. Always use theme colors instead of hardcoded color values
2. Use appropriate semantic colors for different states (success, warning, danger)
3. Ensure proper contrast for accessibility in both light and dark modes
4. Use consistent spacing and typography throughout the application
5. Apply transitions for interactive elements to improve UX

## Updating the Theme

To update the theme:
1. Modify the values in `src/styles/theme.ts`
2. Update the CSS variables in `src/index.css`
3. Update component styles if necessary
4. Test in both light and dark modes