import { useEffect, type ReactNode } from 'react';
import { useAuthStore } from '@/stores/useAuthStore';
import { LoginScreen } from './LoginScreen';
import { RegisterScreen } from './RegisterScreen';

interface Props {
  children: ReactNode;
}

export function ProtectedRoute({ children }: Props) {
  const { isAuthenticated, isLoading, restoreSession, authScreen } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen w-screen bg-[#0A0E1A]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-nexus-cyan/30 border-t-nexus-cyan rounded-full animate-spin mx-auto mb-4" />
          <p className="text-nexus-text-secondary text-sm">Restoring session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return authScreen === 'register' ? <RegisterScreen /> : <LoginScreen />;
  }

  return <>{children}</>;
}
