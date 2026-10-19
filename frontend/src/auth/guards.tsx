import { Box, CircularProgress } from "@mui/material";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import type { Role } from "../api/types";
import { useAuth } from "./AuthContext";

function Spinner() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
      <CircularProgress />
    </Box>
  );
}

export function homeFor(role: string): string {
  if (role === "investor") return "/investor";
  if (role === "startup") return "/profile";
  if (role === "staff") return "/staff/dashboard";
  return "/";
}

/** Role areas: a path inside one of them is only valid for that role. */
function allowedFor(role: string, path: string): boolean {
  if (path.startsWith("/investor")) return role === "investor";
  if (path.startsWith("/profile")) return role === "startup";
  if (path.startsWith("/staff")) return role === "staff";
  return true;
}

/**
 * Where to go after login: the page the user originally wanted (if it is a safe,
 * in-app path that this role may open), otherwise the role's home page.
 */
export function resolveLanding(role: string, from: unknown): string {
  if (
    typeof from === "string" &&
    from.startsWith("/") &&
    !from.startsWith("//") &&
    !from.startsWith("/login") &&
    !from.startsWith("/register") &&
    allowedFor(role, from)
  ) {
    return from;
  }
  return homeFor(role);
}

export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner />;
  if (!user) {
    // remember where the user wanted to go, so login can bring them back
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />;
  return <>{children}</>;
}

export function PublicOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner />;
  if (user) {
    const from = (location.state as { from?: unknown } | null)?.from;
    return <Navigate to={resolveLanding(user.role, from)} replace />;
  }
  return <>{children}</>;
}

export function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <Spinner />;
  return <Navigate to={user ? homeFor(user.role) : "/login"} replace />;
}
