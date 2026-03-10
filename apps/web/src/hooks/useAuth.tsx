import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import {
  apiGet,
  apiPostNoAuth,
  setAuthTokens,
  clearAuthTokens,
  getAccessToken,
  AuthExpiredError,
} from '@/lib/api';

// User from API (matches backend UserResponse)
interface User {
  id: string;
  email?: string;
  full_name?: string;
  phone?: string;
  is_admin?: boolean;
  preferred_language?: string | null; // 'ru' | 'uz'
  plan?: string | null;
  trial_ends_at?: string | null;
  trial_days_left?: number | null;
  user_metadata?: {
    full_name?: string;
  };
}

interface AuthContextType {
  user: User | null;
  session: { user: User } | null;
  loading: boolean;
  signUp: (email: string, password: string, fullName?: string, phone?: string, consentProcessing?: boolean) => Promise<{ error: Error | null }>;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: {
    id: string;
    email?: string | null;
    full_name?: string | null;
    phone?: string | null;
    is_admin?: boolean;
    preferred_language?: string | null;
    plan?: string | null;
    trial_ends_at?: string | null;
    trial_days_left?: number | null;
  };
}

function mapUser(u: AuthResponse['user']): User {
  return {
    id: u.id,
    email: u.email ?? undefined,
    full_name: u.full_name ?? undefined,
    phone: u.phone ?? undefined,
    is_admin: u.is_admin ?? false,
    preferred_language: u.preferred_language ?? undefined,
    plan: u.plan ?? undefined,
    trial_ends_at: u.trial_ends_at ?? undefined,
    trial_days_left: u.trial_days_left ?? undefined,
    user_metadata: u.full_name ? { full_name: u.full_name } : undefined,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<{ user: User } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const token = getAccessToken();

    if (!token) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const data = await apiGet<{ id: string; email?: string | null; full_name?: string | null; phone?: string | null; is_admin?: boolean; preferred_language?: string | null }>('/api/auth/me');
        if (!cancelled) {
          const u: User = mapUser(data);
          setUser(u);
          setSession({ user: u });
        }
      } catch (err: unknown) {
        if (cancelled) return;
        // Если refresh не удался (AuthExpiredError) или другая 401-причина — разлогиниваем
        if (err instanceof AuthExpiredError) {
          clearAuthTokens();
        }
        setUser(null);
        setSession(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const signUp = async (email: string, password: string, fullName?: string, phone?: string, consentProcessing?: boolean) => {
    try {
      const res = await apiPostNoAuth<AuthResponse>('/api/auth/register', {
        email,
        password,
        full_name: fullName || null,
        phone: (phone && phone.trim()) || null,
        consent_processing: !!consentProcessing,
      });
      setAuthTokens(res.access_token, res.refresh_token);
      const u = mapUser(res.user);
      setUser(u);
      setSession({ user: u });
      return { error: null };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка регистрации';
      return { error: new Error(message) };
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      const res = await apiPostNoAuth<AuthResponse>('/api/auth/login', { email, password });
      setAuthTokens(res.access_token, res.refresh_token);
      const u = mapUser(res.user);
      setUser(u);
      setSession({ user: u });
      return { error: null };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка входа';
      return { error: new Error(message) };
    }
  };

  const signOut = async () => {
    try {
      // refresh-токен будет прочитан на сервере из HttpOnly cookie
      await apiPostNoAuth('/api/auth/logout', {});
    } catch {
      // ignore
    }
    clearAuthTokens();
    setUser(null);
    setSession(null);
  };

  const refreshProfile = async () => {
    try {
      const data = await apiGet<AuthResponse['user']>('/api/auth/me');
      const u = mapUser(data);
      setUser(u);
      setSession({ user: u });
    } catch {
      // 401 or network: leave user as is or could clear
    }
  };

  return (
    <AuthContext.Provider value={{
      user,
      session,
      loading,
      signUp,
      signIn,
      signOut,
      refreshProfile,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
