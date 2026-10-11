import { createContext, useContext, useState } from "react";
import { api } from "./api";

const AuthContext = createContext(null);
const KEY = "ost.user";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem(KEY)) || null; } catch { return null; }
  });

  async function login(username, password) {
    const u = await api.login(username, password);
    sessionStorage.setItem(KEY, JSON.stringify(u));
    setUser(u);
    return u;
  }

  function logout() {
    sessionStorage.removeItem(KEY);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
