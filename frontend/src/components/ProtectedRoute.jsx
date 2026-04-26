import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="flex items-center gap-3 rounded-full border border-border bg-white px-5 py-3 text-sm font-medium text-muted-foreground shadow-sm">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          Carregando ambiente...
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !user.is_admin) {
    return <Navigate to="/" replace />;
  }

  return children;
}
