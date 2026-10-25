import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useCallback, useContext, useMemo } from "react";
import { api } from "../api/client";
import type { Me } from "../api/types";

interface AuthState {
  me: Me | undefined;
  loading: boolean;
  signIn: (googleCredential: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/auth/me"), staleTime: 60_000 });

  const signIn = useCallback(
    async (credential: string) => {
      await api("/auth/google", { method: "POST", body: JSON.stringify({ credential }) });
      await client.invalidateQueries({ queryKey: ["me"] });
    },
    [client],
  );

  const signOut = useCallback(async () => {
    await api("/auth/logout", { method: "POST" });
    window.google?.accounts.id.disableAutoSelect();
    await client.invalidateQueries({ queryKey: ["me"] });
  }, [client]);

  const value = useMemo(() => ({ me: data, loading: isPending, signIn, signOut }), [data, isPending, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
