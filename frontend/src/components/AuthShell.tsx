import { Outlet } from "react-router-dom";
import AppFooter from "./AppFooter";

/** Wraps login / register / reset screens: keeps their full-screen layout, adds the legal bar. */
export default function AuthShell() {
  return (
    <>
      <Outlet />
      <AppFooter variant="auth" />
    </>
  );
}