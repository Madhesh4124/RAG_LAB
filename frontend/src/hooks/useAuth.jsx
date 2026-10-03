import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getMe, login as apiLogin, logout as apiLogout, signup as apiSignup } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = localStorage.getItem("raglab_token");
    if (!token) {
      setUser(null);
      return null;
    }
    try {
      const { data } = await getMe();
      setUser(data || null);
      return data || null;
    } catch {
      localStorage.removeItem("raglab_token");
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const current = await refresh();
        if (mounted) setUser(current);
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [refresh]);

  const signup = useCallback(async (payload) => {
    const { data } = await apiSignup(payload);
    if (data?.access_token) {
      localStorage.setItem("raglab_token", data.access_token);
    }
    setUser(data || null);
    return data;
  }, []);

  const login = useCallback(async (payload) => {
    const { data } = await apiLogin(payload);
    if (data?.access_token) {
      localStorage.setItem("raglab_token", data.access_token);
    }
    setUser(data || null);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Ignore network errors during logout
    } finally {
      localStorage.removeItem("raglab_token");
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      isAdmin: Boolean(user?.is_admin),
      signup,
      login,
      logout,
      refresh,
    }),
    [user, loading, signup, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
