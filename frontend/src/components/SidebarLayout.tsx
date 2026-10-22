import {
  Box, List, ListItemButton, ListItemIcon, ListItemText, Paper, Tab, Tabs,
} from "@mui/material";
import type { ReactElement, ReactNode } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useGuardedLink } from "./UnsavedGuard";

export type SidebarItem = {
  key: string;
  to: string;
  end?: boolean;
  label: string;
  icon: ReactElement;
  /** small mark at the right edge (status icon, lock ...) */
  trailing?: ReactNode;
};

/** Sticky sidebar on desktop, scrollable tabs on mobile, content on the right. */
export default function SidebarLayout({ items, ariaLabel, children }: {
  items: SidebarItem[]; ariaLabel: string; children: ReactNode;
}) {
  const { pathname } = useLocation();
  const guardLink = useGuardedLink(); // asks before leaving a page with unsaved edits

  const isActive = (i: SidebarItem) => (i.end ? pathname === i.to : pathname.startsWith(i.to));
  const active = items.find(isActive)?.to ?? false;

  return (
    <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "240px minmax(0, 1fr)" }, alignItems: "start" }}>
      <Paper
        variant="outlined" component="nav" aria-label={ariaLabel}
        sx={{ display: { xs: "none", md: "block" }, position: "sticky", top: 24, p: 1, borderRadius: 3 }}
      >
        <List disablePadding>
          {items.map((i) => (
            <ListItemButton
              key={i.key} component={RouterLink} to={i.to} selected={isActive(i)}
              onClick={guardLink(i.to)} sx={{ borderRadius: 2, mb: 0.25 }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{i.icon}</ListItemIcon>
              <ListItemText
                primary={i.label}
                slotProps={{
                  primary: {
                    sx: { fontWeight: isActive(i) ? 700 : 500 },
                  },
                }}
              />
              {i.trailing}
            </ListItemButton>
          ))}
        </List>
      </Paper>

      <Paper variant="outlined" sx={{ display: { xs: "block", md: "none" }, borderRadius: 3 }}>
        <Tabs value={active} variant="scrollable" scrollButtons="auto" allowScrollButtonsMobile>
          {items.map((i) => (
            <Tab
              key={i.key} value={i.to} component={RouterLink} to={i.to} onClick={guardLink(i.to)}
              icon={i.icon} iconPosition="start" label={i.label}
              sx={{ minHeight: 48, textTransform: "none" }}
            />
          ))}
        </Tabs>
      </Paper>

      <Box sx={{ minWidth: 0 }}>{children}</Box>
    </Box>
  );
}