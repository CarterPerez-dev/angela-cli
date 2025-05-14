import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate, Outlet } from 'react-router-dom';

// --- Page Components (Lazy Loaded) ---
// These components are assumed to be in 'src/pages/'
// e.g., src/pages/TaskListPage.tsx
const TaskListPage = lazy(() => import('./pages/TaskListPage'));
const TaskDetailPage = lazy(() => import('./pages/TaskDetailPage'));
const CreateTaskPage = lazy(() => import('./pages/CreateTaskPage'));
const EditTaskPage = lazy(() => import('./pages/EditTaskPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

// Auth pages (example: could be in 'src/pages/Auth/')
// e.g., src/pages/Auth/LoginPage.tsx
const LoginPage = lazy(() => import('./pages/Auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/Auth/RegisterPage'));

// --- Layout Components ---

/**
 * MainLayout component.
 * In a real application, this would typically be in its own file,
 * e.g., 'src/components/Layout/MainLayout.tsx'.
 * It uses <Outlet /> from react-router-dom to render nested child routes.
 */
const MainLayout: React.FC = () => (
  <div className="app-layout">
    <header className="app-header">
      {/* Basic navigation or header content can go here */}
      <h1>A Cool New Web Application For Tasks</h1>
      {/* Example Nav:
      <nav>
        <Link to="/">Home</Link> | <Link to="/tasks">Tasks</Link> | <Link to="/settings">Settings</Link>
      </nav>
      */}
    </header>
    <main className="app-content">
      <Outlet /> {/* Child routes defined within AppRoutes will render here */}
    </main>
    <footer className="app-footer">
      <p>&copy; {new Date().getFullYear()} a-cool-new-web-application-for</p>
    </footer>
  </div>
);

// --- Helper Components ---

/**
 * LoadingFallback component.
 * Displayed as a fallback while lazy-loaded components are being fetched.
 */
const LoadingFallback: React.FC = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'sans-serif' }}>
    <p>Loading, please wait...</p>
  </div>
);

/**
 * ProtectedRoute component.
 * This component checks if the user is authenticated.
 * If authenticated, it renders the child components.
 * If not, it redirects the user to the login page.
 *
 * Note: The authentication logic (`isAuthenticated`) is a placeholder.
 * In a real application, this would involve checking an authentication context,
 * Redux store, or making an API call.
 */
const ProtectedRoute: React.FC<{ children: JSX.Element }> = ({ children }) => {
  // Placeholder for actual authentication status
  // TODO: Replace with your actual authentication check logic (e.g., from context or store)
  const isAuthenticated = true;

  if (!isAuthenticated) {
    // Redirect them to the /login page.
    // Optionally, pass the current location they were trying to go to,
    // so you can redirect them back after they login.
    // Example: return <Navigate to="/login" state={{ from: location }} replace />; (requires useLocation)
    return <Navigate to="/login" replace />;
  }

  return children;
};

/**
 * AppRoutes component.
 * Defines the main routing configuration for the application.
 * It uses React Router v6 features like nested routes and layouts.
 * Pages are lazy-loaded for better initial load performance.
 *
 * This component is typically used within the main App component,
 * wrapped by <BrowserRouter>.
 */
const AppRoutes: React.FC = () => {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* Public routes (e.g., login, register) - typically without MainLayout */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Routes protected by authentication and using MainLayout */}
        <Route path="/" element={<MainLayout />}>
          {/* Index route for the root path '/' (e.g., dashboard or task list) */}
          <Route
            index
            element={
              <ProtectedRoute>
                <TaskListPage />
              </ProtectedRoute>
            }
          />
          {/* Task related routes */}
          <Route
            path="tasks" // Matches '/tasks'
            element={
              <ProtectedRoute>
                <TaskListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="tasks/new" // Matches '/tasks/new'
            element={
              <ProtectedRoute>
                <CreateTaskPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="tasks/:taskId" // Matches '/tasks/some-id'
            element={
              <ProtectedRoute>
                <TaskDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="tasks/:taskId/edit" // Matches '/tasks/some-id/edit'
            element={
              <ProtectedRoute>
                <EditTaskPage />
              </ProtectedRoute>
            }
          />
          {/* Other application routes */}
          <Route
            path="settings" // Matches '/settings'
            element={
              <ProtectedRoute>
                <SettingsPage />
              </ProtectedRoute>
            }
          />
          {/* Catch-all route for 404 Not Found pages within the MainLayout */}
          {/* This will match any path not matched by the routes above under MainLayout */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        
        {/* 
          If a global 404 page is needed that does NOT use MainLayout (e.g., for /foo/bar),
          it could be placed here as a top-level catch-all:
          <Route path="*" element={<StandaloneNotFoundPage />} />
          However, the current setup where the 404 is part of MainLayout is common
          as it keeps the app's look and feel consistent.
        */}
      </Routes>
    </Suspense>
  );
};

export default AppRoutes;