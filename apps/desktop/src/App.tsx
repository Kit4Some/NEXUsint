import { AppShell } from '@/components/layout/AppShell';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

export default function App() {
  return (
    <ProtectedRoute>
      <AppShell />
    </ProtectedRoute>
  );
}
