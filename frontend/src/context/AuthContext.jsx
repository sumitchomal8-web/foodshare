import { createContext, useContext, useEffect, useState } from "react";
import { loginUser, registerUser } from "../api/auth";
import { TOKEN_STORAGE_KEY } from "../api/client";
import { getMyProfile } from "../api/users";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(localStorage.getItem(TOKEN_STORAGE_KEY)));

  const refreshUser = async () => {
    const profile = await getMyProfile();
    setUser(profile);
    return profile;
  };

  useEffect(() => {
    let active = true;

    async function loadSession() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const profile = await getMyProfile();
        if (active) {
          setUser(profile);
        }
      } catch {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        if (active) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadSession();
    return () => {
      active = false;
    };
  }, [token]);

  const login = async (credentials) => {
    const data = await loginUser(credentials);
    localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
    setToken(data.access_token);
    const profile = await getMyProfile();
    setUser(profile);
    return profile;
  };

  const register = async (payload) => {
    return registerUser(payload);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        loading,
        isAuthenticated: Boolean(token && user),
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
