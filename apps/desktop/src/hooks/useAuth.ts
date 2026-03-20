import { useQuery, useMutation } from '@tanstack/react-query';
import { auth } from '@/services/api';
import { useAuthStore } from '@/stores/useAuthStore';

export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore();
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => auth.me(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      auth.changePassword(data.current_password, data.new_password),
  });
}
