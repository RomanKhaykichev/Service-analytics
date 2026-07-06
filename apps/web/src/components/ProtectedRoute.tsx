import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Loader2 } from 'lucide-react';
import { UzumApiConnectProvider } from '@/contexts/UzumApiConnectContext';

/** Защищённый layout: одна сессия подключения API на все страницы дашборда. */
export function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading && !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/landing" replace />;
  }

  return (
    <UzumApiConnectProvider>
      <Outlet />
    </UzumApiConnectProvider>
  );
}
