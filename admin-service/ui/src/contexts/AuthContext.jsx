/**
 * Authentication Context
 *
 * Provides auth state and methods throughout the app.
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, setTokens, clearTokens, getRefreshToken } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      const refreshToken = getRefreshToken();

      if (refreshToken) {
        try {
          // Try to refresh the token and get user info
          const tokenResponse = await authApi.refresh(refreshToken);
          setTokens(tokenResponse.access_token, tokenResponse.refresh_token);

          // Get user info
          const userResponse = await authApi.me();
          setUser(userResponse);
        } catch (error) {
          // Token invalid/expired - clear everything
          clearTokens();
          setUser(null);
        }
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    const response = await authApi.login(email, password);
    setTokens(response.access_token, response.refresh_token);
    setUser(response.user);
    return response;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // Ignore logout errors
    } finally {
      clearTokens();
      setUser(null);
    }
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
