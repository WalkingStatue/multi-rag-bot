# Layout System Documentation

This document provides an overview of the layout system used in the Multi-Bot RAG Platform frontend.

## Overview

The layout system is designed to provide a consistent and flexible way to structure pages across the application. It consists of several layout components that can be combined to create different page layouts.

## Layout Components

### BaseLayout

The foundation for all layouts in the application. It provides basic structure and common functionality.

```tsx
import { BaseLayout } from '../layouts';

<BaseLayout>
  {/* Your content here */}
</BaseLayout>
```

### MainLayout

Includes the main navigation and serves as the base for most pages. It supports optional sidebar and different content layouts.

```tsx
import { MainLayout } from '../layouts';

<MainLayout 
  hasSidebar={true}
  sidebarContent={<YourSidebarContent />}
  fullWidth={false}
>
  {/* Your content here */}
</MainLayout>
```

### AuthLayout

Used for authentication pages like login and register. It provides a centered card layout without the main navigation.

```tsx
import { AuthLayout } from '../layouts';

<AuthLayout
  title="Sign In"
  subtitle="Enter your credentials to access your account"
  footer={<FooterContent />}
>
  {/* Your form content here */}
</AuthLayout>
```

### ChatLayout

Used for the chat interface. It provides a full-screen layout with a specialized header.

```tsx
import { ChatLayout } from '../layouts';

<ChatLayout
  title="Chat with Bot"
  subtitle="Ask questions and get answers"
  rightContent={<SearchComponent />}
>
  {/* Your chat interface here */}
</ChatLayout>
```

### DashboardLayout

Extends the MainLayout with specific dashboard features. It includes a sidebar with navigation and content area with header.

```tsx
import { DashboardLayout } from '../layouts';

<DashboardLayout
  title="Dashboard"
  subtitle="Welcome to your dashboard"
  actions={<ActionButtons />}
>
  {/* Your dashboard content here */}
</DashboardLayout>
```

### LandingLayout

Used for the landing page and other marketing pages. It provides a clean layout with a simplified navigation.

```tsx
import { LandingLayout } from '../layouts';

<LandingLayout
  showNavigation={true}
  showFooter={true}
>
  {/* Your landing page content here */}
</LandingLayout>
```

## Reusable Components

### Card

A versatile card component with various style options.

```tsx
import { Card } from '../components/common';

<Card
  title="Card Title"
  subtitle="Card Subtitle"
  variant="default" // 'default', 'outline', 'filled'
  padding="medium" // 'none', 'small', 'medium', 'large'
  hover={true}
  onClick={() => {}}
  footer={<FooterContent />}
>
  {/* Card content here */}
</Card>
```

### Panel

A panel component for creating sections with headers.

```tsx
import { Panel } from '../components/common';

<Panel
  title="Panel Title"
  subtitle="Panel Subtitle"
  variant="default" // 'default', 'outline', 'filled'
  padding="medium" // 'none', 'small', 'medium', 'large'
  collapsible={true}
  defaultCollapsed={false}
  footer={<FooterContent />}
>
  {/* Panel content here */}
</Panel>
```

### Grid

A flexible grid layout component with responsive options.

```tsx
import { Grid } from '../components/common';

<Grid
  cols={1} // 1-12
  mdCols={2} // 1-12 (medium screens)
  lgCols={3} // 1-12 (large screens)
  gap="medium" // 'none', 'small', 'medium', 'large'
>
  <GridItem1 />
  <GridItem2 />
  <GridItem3 />
</Grid>
```

### Container

A container component for consistent content width and padding.

```tsx
import { Container } from '../components/common';

<Container
  size="lg" // 'sm', 'md', 'lg', 'xl', 'full'
  padding="md" // 'none', 'sm', 'md', 'lg'
  centered={true}
>
  {/* Container content here */}
</Container>
```

## Page Structure

A typical page structure might look like this:

```tsx
import { DashboardLayout, Container, Grid, Card } from '../components/common';

const YourPage = () => {
  return (
    <DashboardLayout
      title="Your Page"
      subtitle="Page description"
    >
      <Container>
        <Grid cols={1} mdCols={2} lgCols={3} gap="medium">
          <Card title="Card 1">
            {/* Card content */}
          </Card>
          <Card title="Card 2">
            {/* Card content */}
          </Card>
          <Card title="Card 3">
            {/* Card content */}
          </Card>
        </Grid>
      </Container>
    </DashboardLayout>
  );
};
```

## Responsive Behavior

All layout components are designed to be responsive and work well on all screen sizes. The MainLayout and DashboardLayout components include a responsive sidebar that can be toggled on mobile devices.

## Theme Support

All layout components support both light and dark modes through the theme system.