import { lazy, Suspense } from "react";
import { Loader2 } from "lucide-react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "sonner";

import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

const AdminSettingsPage = lazy(() => import("./pages/AdminSettingsPage"));
const GeneratorPage = lazy(() => import("./pages/GeneratorPage"));
const HomePage = lazy(() => import("./pages/HomePage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const PlanEditorPage = lazy(() => import("./pages/PlanEditorPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const SavedPlansPage = lazy(() => import("./pages/SavedPlansPage"));

function RouteFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center px-4 py-10">
      <div className="flex items-center gap-2.5 text-[15px] font-medium text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        Carregando...
      </div>
    </div>
  );
}

function AppLayout({ children }) {
  const location = useLocation();
  const hideNavigation = location.pathname === "/login" || location.pathname === "/cadastro";

  return (
    <div className="min-h-screen bg-background">
      {hideNavigation ? null : <Navbar />}
      <div className="min-h-screen pb-6">{children}</div>
      <Toaster richColors position="top-center" />
    </div>
  );
}

export default function App() {
  const { user } = useAuth();

  return (
    <AppLayout>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
          <Route path="/cadastro" element={user ? <Navigate to="/" replace /> : <RegisterPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/gerador"
            element={
              <ProtectedRoute>
                <GeneratorPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/editor"
            element={
              <ProtectedRoute>
                <PlanEditorPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/editor/:planId"
            element={
              <ProtectedRoute>
                <PlanEditorPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/planos"
            element={
              <ProtectedRoute>
                <SavedPlansPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminSettingsPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Suspense>
    </AppLayout>
  );
}
