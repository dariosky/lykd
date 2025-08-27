import React, { createContext, useContext } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiService, queryKeys, UserResponse } from "./api";

interface AuthContextType {
  user: UserResponse["user"] | null;
  isLoggedIn: boolean;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { data, isLoading, error, refetch } = useQuery<UserResponse, Error>({
    queryKey: queryKeys.currentUser,
    queryFn: apiService.getCurrentUser,
    staleTime: 30 * 1000,
    retry: 1,
  });

  const user = data?.user ?? null;
  const isLoggedIn = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        loading: isLoading,
        error: error ?? null,
        refetch,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
