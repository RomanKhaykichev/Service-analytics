import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import {
  apiGet,
  apiPostNoAuth,
  setAuthTokens,
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
} from '@/lib/api';

// User from API (matches backend UserResponse)
interface User {
  id: string;
  email?: string;
  full_name?: string;
  phone?: string;
  is_admin?: boolean;
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
  user: { id: string; email?: string | null; full_name?: string | null; phone?: string | null; is_admin?: boolean };
}

function mapUser(u: AuthResponse['user']): User {
  return {
    id: u.id,
    email: u.email ?? undefined,
    full_name: u.full_name ?? undefined,
    phone: u.phone ?? undefined,
    is_admin: u.is_admin ?? false,
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
    const refreshToken = getRefreshToken();

    if (!token) {
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const data = await apiGet<{ id: string; email?: string | null; full_name?: string | null; phone?: string | null; is_admin?: boolean }>('/api/auth/me');
        if (!cancelled) {
          const u: User = mapUser(data);
          setUser(u);
          setSession({ user: u });
        }
      } catch (err: unknown) {
        if (cancelled) return;
        if (refreshToken) {
          try {
            const tokens = await apiPostNoAuth<{ access_token: string; refresh_token: string }>('/api/auth/refresh', { refresh_token: refreshToken });
            setAuthTokens(tokens.access_token, tokens.refresh_token);
            const me = await apiGet<AuthResponse['user']>('/api/auth/me');
            if (!cancelled) {
              const u = mapUser(me);
              setUser(u);
              setSession({ user: u });
            }
          } catch {
            clearAuthTokens();
            setUser(null);
            setSession(null);
          }
        } else {
          clearAuthTokens();
          setUser(null);
          setSession(null);
        }
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
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await apiPostNoAuth('/api/auth/logout', { refresh_token: refreshToken });
      } catch {
        // ignore
      }
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
