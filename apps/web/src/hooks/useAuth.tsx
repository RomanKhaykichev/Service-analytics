import { useState, useEffect, createContext, useContext, ReactNode } from 'react';

// Simple user interface (replaces Supabase User)
interface User {
  id: string;
  email?: string;
  user_metadata?: {
    full_name?: string;
  };
}

interface AuthContextType {
  user: User | null;
  session: { user: User } | null;
  loading: boolean;
  signUp: (email: string, password: string, fullName?: string) => Promise<{ error: Error | null }>;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const USER_ID_KEY = 'user_id';
const DEFAULT_USER_ID = '00000000-0000-0000-0000-000000000001';

// Get or create user_id from localStorage
function getOrCreateUserId(): string {
  const stored = localStorage.getItem(USER_ID_KEY);
  if (stored) {
    return stored;
  }
  localStorage.setItem(USER_ID_KEY, DEFAULT_USER_ID);
  return DEFAULT_USER_ID;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<{ user: User } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize user from localStorage
    const userId = getOrCreateUserId();
    const mockUser: User = {
      id: userId,
      email: 'dev@example.com',
      user_metadata: {
        full_name: 'Dev User',
      },
    };
    
    setUser(mockUser);
    setSession({ user: mockUser });
    setLoading(false);
  }, []);

  const signUp = async (email: string, password: string, fullName?: string) => {
    // TODO: Implement actual signup with backend API
    // For now, just create a mock user
    const userId = DEFAULT_USER_ID;
    localStorage.setItem(USER_ID_KEY, userId);
    
    const mockUser: User = {
      id: userId,
      email,
      user_metadata: {
        full_name: fullName,
      },
    };
    
    setUser(mockUser);
    setSession({ user: mockUser });
    
    return { error: null };
  };

  const signIn = async (email: string, password: string) => {
    // TODO: Implement actual signin with backend API
    // For now, just use default user
    const userId = getOrCreateUserId();
    
    const mockUser: User = {
      id: userId,
      email,
    };
    
    setUser(mockUser);
    setSession({ user: mockUser });
    
    return { error: null };
  };

  const signOut = async () => {
    // Clear user_id from localStorage
    localStorage.removeItem(USER_ID_KEY);
    setUser(null);
    setSession(null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      session,
      loading,
      signUp,
      signIn,
      signOut,
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
