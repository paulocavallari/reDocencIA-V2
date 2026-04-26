import { createContext, startTransition, useContext, useEffect, useState } from "react";

import api from "../services/api";
import { isSupabaseConfigured, supabase } from "../services/supabase";

const AuthContext = createContext(null);
const TOKEN_STORAGE_KEY = "redocencia-token";


function normalizeSupabaseAuthError(error, fallbackMessage) {
  const message = error?.message || "";

  if (/rate limit/i.test(message)) {
    return new Error("O Supabase limitou temporariamente novos envios. Aguarde alguns minutos e tente novamente.");
  }

  if (/email not confirmed/i.test(message)) {
    return new Error("Seu cadastro existe, mas o email ainda não foi confirmado. Abra a mensagem enviada pelo Supabase antes de entrar.");
  }

  return new Error(message || fallbackMessage);
}


function normalizeApiError(error, fallbackMessage) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return new Error(detail.trim());
  }
  return new Error(error?.message || fallbackMessage);
}


function looksLikeEmail(value) {
  return /.+@.+\..+/.test(value);
}


function persistToken(token) {
  if (token) {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    return;
  }
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    let subscription;

    async function syncUserFromApi() {
      const { data } = await api.get("/api/auth/me");
      if (!active) {
        return;
      }
      startTransition(() => {
        setUser(data);
        setLoading(false);
      });
    }

    async function bootstrapSupabaseAuth() {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!active) {
        return;
      }

      persistToken(session?.access_token || null);
      if (!session) {
        setLoading(false);
      } else {
        try {
          await syncUserFromApi();
        } catch {
          persistToken(null);
          setUser(null);
          setLoading(false);
        }
      }

      const authListener = supabase.auth.onAuthStateChange(async (_event, nextSession) => {
        persistToken(nextSession?.access_token || null);

        if (!nextSession) {
          startTransition(() => {
            setUser(null);
            setLoading(false);
          });
          return;
        }

        try {
          await syncUserFromApi();
        } catch {
          persistToken(null);
          startTransition(() => {
            setUser(null);
            setLoading(false);
          });
        }
      });

      subscription = authListener.data.subscription;
    }

    function bootstrapLocalAuth() {
      const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
      if (!token) {
        setLoading(false);
        return;
      }

      api
        .get("/api/auth/me")
        .then(({ data }) => {
          if (!active) {
            return;
          }
          startTransition(() => {
            setUser(data);
            setLoading(false);
          });
        })
        .catch(() => {
          persistToken(null);
          if (active) {
            setLoading(false);
          }
        });
    }

    if (isSupabaseConfigured && supabase) {
      bootstrapSupabaseAuth();
    } else {
      bootstrapLocalAuth();
    }

    return () => {
      active = false;
      subscription?.unsubscribe();
    };
  }, []);

  async function login(identifier, password) {
    const normalizedIdentifier = (identifier || "").trim();

    if (isSupabaseConfigured && supabase) {
      let supabaseError = null;

      if (looksLikeEmail(normalizedIdentifier)) {
        const { data, error } = await supabase.auth.signInWithPassword({
          email: normalizedIdentifier,
          password,
        });

        if (!error && data?.session) {
          persistToken(data.session.access_token);
          const response = await api.get("/api/auth/me");
          setUser(response.data);
          return response.data;
        }

        supabaseError = error;
      }

      try {
        const { data } = await api.post("/api/auth/login", { username: normalizedIdentifier, password });
        persistToken(data.access_token);
        setUser(data.user);
        return data.user;
      } catch (apiError) {
        if (supabaseError) {
          throw normalizeSupabaseAuthError(supabaseError, "Não foi possível entrar.");
        }
        throw normalizeApiError(apiError, "Não foi possível entrar.");
      }
    }

    const { data } = await api.post("/api/auth/login", { username: normalizedIdentifier, password });
    persistToken(data.access_token);
    setUser(data.user);
    return data.user;
  }

  async function register(payload) {
    if (isSupabaseConfigured && supabase) {
      try {
        const { data } = await api.post("/api/auth/register", payload, {
          params: { auth_mode: "supabase" },
        });

        if (data?.assisted_login) {
          const { data: signInData, error } = await supabase.auth.signInWithPassword({
            email: payload.email,
            password: payload.password,
          });
          if (error) {
            throw normalizeSupabaseAuthError(error, "Não foi possível entrar após concluir o cadastro.");
          }

          persistToken(signInData.session?.access_token || null);
          const response = await api.get("/api/auth/me");
          setUser(response.data);
          return response.data;
        }

        if (data?.pending_confirmation) {
          return {
            pendingConfirmation: true,
            email: data.email || payload.email,
          };
        }
      } catch (error) {
        if (
          error?.response?.status !== 503 ||
          error?.response?.data?.detail !== "SUPABASE_ASSISTED_SIGNUP_UNAVAILABLE"
        ) {
          throw normalizeApiError(error, "Não foi possível concluir o cadastro.");
        }
      }

      const { data, error } = await supabase.auth.signUp({
        email: payload.email,
        password: payload.password,
        options: {
          emailRedirectTo: window.location.origin,
          data: {
            nome: payload.nome,
            username: payload.username,
          },
        },
      });
      if (error) {
        throw normalizeSupabaseAuthError(error, "Não foi possível concluir o cadastro.");
      }
      if (!data.session) {
        return {
          pendingConfirmation: true,
          email: payload.email,
        };
      }

      persistToken(data.session.access_token);
      const response = await api.get("/api/auth/me");
      setUser(response.data);
      return response.data;
    }

    const { data } = await api.post("/api/auth/register", payload);
    persistToken(data.access_token);
    setUser(data.user);
    return data.user;
  }

  async function logout() {
    if (isSupabaseConfigured && supabase) {
      await supabase.auth.signOut();
    }

    persistToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
