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
  phone_verified_at?: string | null;
  plan?: string | null;
  trial_ends_at?: string | null;
  trial_days_left?: number | null;
  user_metadata?: {
    full_name?: string;
  };
}

export interface RegisterVerifyPending {
  ok: boolean;
  next: 'verify_phone';
  pending_id: string;
  phone_masked: string;
  expires_in_sec: number;
}

interface AuthContextType {
  user: User | null;
  session: { user: User } | null;
  loading: boolean;
  signUp: (
    email: string,
    password: string,
    fullName?: string,
    phone?: string,
    consentProcessing?: boolean,
  ) => Promise<{ error: Error | null; pending?: RegisterVerifyPending }>;
  verifyPhone: (
    pendingId: string,
    code: string,
  ) => Promise<{ error: Error | null }>;
  resendPhoneOtp: (pendingId: string) => Promise<{ error: Error | null; expiresInSec?: number }>;
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
    phone_verified_at?: string | null;
    plan?: string | null;
    trial_ends_at?: string | null;
    trial_days_left?: number | null;
  };
}

function mapUser(u: AuthResponse['user'] & { phone_verified_at?: string | null }): User {
  return {
    id: u.id,
    email: u.email ?? undefined,
    full_name: u.full_name ?? undefined,
    phone: u.phone ?? undefined,
    is_admin: u.is_admin ?? false,
    preferred_language: u.preferred_language ?? undefined,
    phone_verified_at: u.phone_verified_at ?? undefined,
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
        const data = await apiGet<{ id: string; email?: string | null; full_name?: string | null; phone?: string | null; is_admin?: boolean; preferred_language?: string | null; phone_verified_at?: string | null }>(
          '/api/auth/me',
          undefined,
          { timeoutMs: 15_000 },
        );
        if (!cancelled) {
          const u: User = mapUser(data);
          setUser(u);
          setSession({ user: u });
        }
      } catch (err: unknown) {
        if (!cancelled) {
          // Если refresh не удался (AuthExpiredError) или другая 401-причина — разлогиниваем
          if (err instanceof AuthExpiredError) {
            clearAuthTokens();
          }
          setUser(null);
          setSession(null);
        }
      } finally {
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const onAuthExpired = () => {
      clearAuthTokens();
      setUser(null);
      setSession(null);
    };
    window.addEventListener("auth-expired", onAuthExpired);
    return () => {
      window.removeEventListener("auth-expired", onAuthExpired);
    };
  }, []);

  const signUp = async (email: string, password: string, fullName?: string, phone?: string, consentProcessing?: boolean) => {
    try {
      const res = await apiPostNoAuth<AuthResponse | RegisterVerifyPending>('/api/auth/register', {
        email,
        password,
        full_name: fullName || null,
        phone: (phone && phone.trim()) || '',
        consent_processing: !!consentProcessing,
      });
      if ('next' in res && res.next === 'verify_phone') {
        return { error: null, pending: res };
      }
      return { error: null };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка регистрации';
      return { error: new Error(message) };
    }
  };

  const verifyPhone = async (pendingId: string, code: string) => {
    try {
      const res = await apiPostNoAuth<AuthResponse>('/api/auth/verify-phone', {
        pending_id: pendingId,
        code: code.replace(/\s/g, ''),
      });
      setAuthTokens(res.access_token, res.refresh_token);
      const u = mapUser(res.user);
      setUser(u);
      setSession({ user: u });
      return { error: null };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка подтверждения';
      return { error: new Error(message) };
    }
  };

  const resendPhoneOtp = async (pendingId: string) => {
    try {
      const res = await apiPostNoAuth<{ ok: boolean; expires_in_sec: number }>('/api/auth/resend-phone-otp', {
        pending_id: pendingId,
      });
      return { error: null, expiresInSec: res.expires_in_sec };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Не удалось отправить код';
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
      verifyPhone,
      resendPhoneOtp,
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
