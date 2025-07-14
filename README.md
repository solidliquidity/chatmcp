# Chatbot UI - Tech Stack Documentation

A modern, full-stack chatbot interface built with cutting-edge technologies for AI-powered conversations, file processing, and multi-model support.

## 🚀 Core Framework

### **Next.js 14**
- **Version**: 14.1.0
- **Features**: App Router, Server Components, Edge Runtime
- **Benefits**: Full-stack React framework with built-in API routes, server-side rendering, and optimized performance

### **React 18**
- **Version**: 18.x
- **Features**: Concurrent features, Suspense, Server Components
- **Benefits**: Modern React with improved performance and developer experience

## 🎨 UI & Styling

### **Tailwind CSS**
- **Version**: 3.3.5
- **Features**: Utility-first CSS framework with custom design system
- **Plugins**: 
  - `@tailwindcss/typography` - Enhanced typography styles
  - `tailwindcss-animate` - Smooth animations
- **Configuration**: Custom color scheme with CSS variables for dark/light mode

### **Radix UI**
- **Components**: Complete set of accessible, unstyled UI primitives
- **Features**: 
  - Accordion, Alert Dialog, Avatar, Checkbox, Collapsible
  - Context Menu, Dialog, Dropdown Menu, Hover Card
  - Navigation Menu, Popover, Progress, Radio Group
  - Scroll Area, Select, Separator, Slider, Switch
  - Tabs, Toast, Toggle, Tooltip
- **Benefits**: Accessible, customizable, and composable components

### **shadcn/ui**
- **Style**: Default theme with gray base color
- **Features**: Pre-built components built on Radix UI primitives
- **Configuration**: TypeScript-first with CSS variables for theming

### **Additional UI Libraries**
- **Lucide React**: Beautiful, customizable icons
- **Tabler Icons**: Additional icon set
- **React Day Picker**: Date picker component
- **React Textarea Autosize**: Auto-resizing textarea
- **Sonner**: Toast notifications

## 🔧 Development Tools

### **TypeScript**
- **Version**: 5.x
- **Configuration**: Strict mode enabled with Next.js integration
- **Features**: Full type safety across the application

### **ESLint & Prettier**
- **ESLint**: Next.js configuration with custom rules
- **Prettier**: Code formatting with custom configuration
- **Husky**: Git hooks for pre-commit formatting

### **Testing**
- **Jest**: Unit testing framework
- **React Testing Library**: Component testing utilities
- **Playwright**: End-to-end testing
- **Coverage**: V8 coverage provider

## 🗄️ Database & Backend

### **Supabase**
- **Version**: 2.38.4
- **Features**:
  - PostgreSQL database with real-time subscriptions
  - Built-in authentication system
  - File storage with 50MB file size limit
  - Row Level Security (RLS)
  - Database migrations and type generation
- **Local Development**: Supabase CLI for local development
- **Authentication**: Email, SMS, and OAuth providers

### **Database Schema**
- **Tables**: Users, Workspaces, Chats, Messages, Files, Collections
- **Features**: Multi-tenant architecture with workspace isolation
- **Migrations**: Version-controlled database schema changes

## 🤖 AI & Machine Learning

### **AI SDKs**
- **OpenAI**: GPT-4, GPT-3.5-turbo integration
- **Anthropic**: Claude models via official SDK
- **Google**: Gemini models via Generative AI SDK
- **Azure OpenAI**: Enterprise OpenAI integration
- **Mistral AI**: Mistral models
- **Groq**: High-speed inference
- **Perplexity**: Search-enhanced AI
- **OpenRouter**: Unified API for multiple models

### **AI Framework**
- **Vercel AI SDK**: Stream-based AI interactions
- **LangChain**: AI application framework
- **Model Context Protocol (MCP)**: Tool integration framework

### **File Processing**
- **PDF Parse**: PDF document processing
- **Mammoth**: DOCX document processing
- **CSV Processing**: Tabular data handling
- **Text Processing**: Markdown, code highlighting

## 🌐 Internationalization

### **i18next**
- **Version**: 23.7.16
- **Features**: 
  - 18 supported languages (Arabic, Bengali, German, English, Spanish, French, Hebrew, Indonesian, Italian, Japanese, Korean, Portuguese, Russian, Sinhala, Swedish, Telugu, Vietnamese, Chinese)
  - Dynamic language switching
  - Resource management
- **Integration**: Next.js i18n router for seamless routing

## 📱 Progressive Web App

### **Next-PWA**
- **Version**: 5.6.0
- **Features**:
  - Service worker for offline functionality
  - App manifest for mobile installation
  - Background sync capabilities
  - Push notifications support

## 🔍 Search & Analytics

### **Vercel Analytics**
- **Version**: 1.1.1
- **Features**: Web vitals monitoring, user analytics
- **Edge Config**: Dynamic configuration management

## 🛠️ Build & Deployment

### **Bundling**
- **Webpack**: Next.js default bundler
- **Bundle Analyzer**: Performance optimization tool
- **Tree Shaking**: Automatic dead code elimination

### **Performance**
- **Image Optimization**: Next.js built-in image optimization
- **Code Splitting**: Automatic route-based code splitting
- **Caching**: Built-in caching strategies

## 🔐 Security

### **Authentication**
- **Supabase Auth**: JWT-based authentication
- **Session Management**: Secure session handling
- **OAuth Providers**: Multiple social login options

### **Data Protection**
- **Row Level Security**: Database-level access control
- **Environment Variables**: Secure configuration management
- **CORS**: Cross-origin resource sharing protection

## 📊 Development Workflow

### **Scripts**
- `npm run dev`: Start development server
- `npm run build`: Production build
- `npm run start`: Start production server
- `npm run lint`: Code linting
- `npm run test`: Run test suite
- `npm run db-types`: Generate TypeScript types from database
- `npm run db-migrate`: Run database migrations

### **Database Management**
- `npm run db-reset`: Reset local database
- `npm run db-pull`: Pull remote database changes
- `npm run db-push`: Push local changes to remote

## 🏗️ Architecture

### **File Structure**
```
chatbot-ui/
├── app/                    # Next.js App Router pages
├── components/             # Reusable UI components
├── lib/                    # Utility functions and configurations
├── db/                     # Database schema and operations
├── types/                  # TypeScript type definitions
├── supabase/              # Supabase configuration and migrations
├── public/                # Static assets
└── __tests__/             # Test files
```

### **Key Features**
- **Multi-Model Support**: Integration with 8+ AI providers
- **File Processing**: Support for PDF, DOCX, CSV, and text files
- **Real-time Chat**: WebSocket-based real-time messaging
- **Workspace Management**: Multi-tenant architecture
- **Responsive Design**: Mobile-first responsive UI
- **Dark/Light Mode**: Theme switching with system preference detection
- **Accessibility**: WCAG compliant components
- **Performance**: Optimized for fast loading and smooth interactions

## 🚀 Getting Started

1. **Clone the repository**
2. **Install dependencies**: `npm install`
3. **Set up Supabase**: Configure environment variables
4. **Start development**: `npm run dev`
5. **Access the app**: http://localhost:3000

## 📝 Environment Variables

Required environment variables for full functionality:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- AI provider API keys (OpenAI, Anthropic, etc.)

## 🤝 Contributing

The project follows modern development practices:
- TypeScript for type safety
- ESLint and Prettier for code quality
- Husky for pre-commit hooks
- Comprehensive testing suite
- Conventional commit messages

This tech stack provides a robust, scalable, and maintainable foundation for building modern AI-powered applications with excellent developer experience and user interface. 