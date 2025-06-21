# 🚀 Threat Intelligence Dashboard Frontend

A modern React TypeScript dashboard for threat intelligence analysis.

## 🏗️ Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **React Query** - Data fetching & caching
- **React Hook Form** - Form handling
- **Zod** - Schema validation
- **Axios** - HTTP client
- **Socket.IO** - Real-time communication
- **Recharts** - Data visualization
- **Sonner** - Toast notifications

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Backend server running on `http://localhost:8000`

### Installation

```bash
# Run the setup script (Windows)
setup-frontend.bat

# Or run the setup script (Linux/Mac)
chmod +x setup-frontend.sh
./setup-frontend.sh

# Or install manually
cd frontend
npm install
npm run dev
```

### Development Server
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── auth/           # Authentication components
│   │   ├── layout/         # Layout components
│   │   └── ui/             # Basic UI elements
│   ├── pages/              # Page components
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── AnalysisPage.tsx
│   │   └── HistoryPage.tsx
│   ├── hooks/              # Custom React hooks
│   │   └── useAuth.tsx     # Authentication state
│   ├── services/           # API and external services
│   │   └── api.ts          # HTTP client
│   ├── types/              # TypeScript type definitions
│   │   └── index.ts        # All type definitions
│   ├── utils/              # Utility functions
│   └── App.tsx             # Main app component
├── public/                 # Static assets
├── index.html             # HTML template
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind CSS configuration
├── tsconfig.json          # TypeScript configuration
└── vite.config.ts         # Vite configuration
```

## 🎨 UI Components

### Authentication
- `LoginPage` - User login form
- `RegisterPage` - User registration form
- `ProtectedRoute` - Route protection

### Dashboard
- `DashboardPage` - Main dashboard with stats
- `AnalysisPage` - Threat analysis interface
- `HistoryPage` - Analysis history table

### Shared Components
- `AuthProvider` - Authentication context
- Button, Input, Card styles via Tailwind CSS

## 🔌 API Integration

### Authentication
```typescript
// Login
const response = await apiClient.login({
  email: 'user@example.com',
  password: 'password'
});

// Register
const response = await apiClient.register({
  email: 'user@example.com',
  password: 'password',
  confirm_password: 'password'
});
```

### Analysis
```typescript
// Analyze indicator
const result = await apiClient.analyzeIndicator({
  indicator: '8.8.8.8',
  sources: ['virustotal']
});

// Get history
const history = await apiClient.getAnalysisHistory(1, 20);
```

## 🎛️ Configuration

### Environment Variables
Copy `.env.example` to `.env.local` and update:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_APP_NAME="Threat Intelligence Dashboard"
```

### Proxy Setup
The Vite dev server proxies `/api` requests to `http://localhost:8000`

## 🧪 Available Scripts

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript type checking
npm run test         # Run tests (when added)
```

## 🎨 Styling

### Tailwind CSS Classes
```typescript
// Pre-defined component classes
className="btn btn-primary"     // Primary button
className="btn btn-secondary"   // Secondary button  
className="input"               // Text input
className="card"                // Card container
```

### Color Scheme
- Primary: Blue (`primary-500`, `primary-600`)
- Danger: Red (`danger-500`, `danger-600`)
- Warning: Amber (`warning-500`, `warning-600`)
- Success: Green (`success-500`, `success-600`)

## 🔐 Authentication Flow

1. User visits protected route
2. `ProtectedRoute` checks authentication status
3. If not authenticated, redirect to `/login`
4. After successful login, JWT token stored in localStorage
5. `AuthProvider` manages authentication state globally
6. API client automatically includes token in requests

## 📊 Data Flow

1. **Login** → Store JWT token → Update auth context
2. **API Calls** → Include auth token → Handle responses
3. **Real-time Updates** → WebSocket connection → Live notifications
4. **Navigation** → Protected routes → Authentication checks

## 🚧 Development Status

### ✅ Completed (Phase 2 - Week 1)
- [x] Project structure and configuration
- [x] TypeScript type definitions
- [x] Authentication components (Login/Register)
- [x] Protected routing
- [x] API client with auth integration
- [x] Basic page layouts

### 🚧 In Progress
- [ ] Analysis form components
- [ ] Dashboard statistics
- [ ] History table with filtering
- [ ] Real-time WebSocket integration

### 📋 Upcoming (Phase 2 - Week 2-3)
- [ ] Analysis results visualization
- [ ] Charts and metrics
- [ ] Export functionality
- [ ] Advanced filtering
- [ ] Mobile responsiveness
- [ ] Accessibility improvements

## 🤝 Contributing

1. Follow TypeScript best practices
2. Use functional components with hooks
3. Implement proper error handling
4. Add loading states for async operations
5. Ensure mobile responsiveness
6. Write meaningful commit messages

## 🐛 Troubleshooting

### Common Issues

**Build Errors**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**API Connection Issues**
- Ensure backend is running on `http://localhost:8000`
- Check CORS configuration in backend
- Verify proxy configuration in `vite.config.ts`

**TypeScript Errors**
- Run `npm run type-check` to see all type issues
- Ensure all types are properly imported from `@/types`

## 📚 Resources

- [React Documentation](https://react.dev)
- [TypeScript Documentation](https://www.typescriptlang.org)
- [Vite Documentation](https://vitejs.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [React Router Documentation](https://reactrouter.com)

---

**Next Phase**: Analysis Interface & Dashboard Components (Week 2)
