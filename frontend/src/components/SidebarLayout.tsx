import {
  Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, List, ListItemButton,
  ListItemIcon, ListItemText, Paper, Tab, Tabs, Typography,
} from "@mui/material";
import { useState, type MouseEvent, type ReactElement, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { UnsavedGuardProvider, useUnsavedGuardState } from "./UnsavedGuard";

export type SidebarItem = {
  key: string;
  to: string;
  end?: boolean;
  label: string;
  icon: ReactElement;
  /** small mark at the right edge (status icon, lock ...) */
  trailing?: ReactNode;
};

function Inner({ items, ariaLabel, children }: {
  items: SidebarItem[]; ariaLabel: string; children: ReactNode;
}) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const guard = useUnsavedGuardState();
  const [pending, setPending] = useState<string | null>(null);

  const isActive = (i: SidebarItem) => (i.end ? pathname === i.to : pathname.startsWith(i.to));
  const active = items.find(isActive)?.to ?? false;

  // ask before leaving a page with unsaved edits
  const onNav = (to: string) => (e: MouseEvent) => {
    if (!guard?.dirty || to === pathname) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return; // open in new tab etc.
    e.preventDefault();
    setPending(to);
  };

  const leave = () => {
    const to = pending;
    setPending(null);
    guard?.setDirty(false);
    if (to) navigate(to);
  };

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
              onClick={onNav(i.to)} sx={{ borderRadius: 2, mb: 0.25 }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{i.icon}</ListItemIcon>
              <ListItemText
                  primary={i.label}
                  slotProps={{
                    primary: {
                      sx: { fontWeight: isActive(i) ? 700 : 500 }
                    }
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
              key={i.key} value={i.to} component={RouterLink} to={i.to} onClick={onNav(i.to)}
              icon={i.icon} iconPosition="start" label={i.label}
              sx={{ minHeight: 48, textTransform: "none" }}
            />
          ))}
        </Tabs>
      </Paper>

      <Box sx={{ minWidth: 0 }}>{children}</Box>

      <Dialog open={pending !== null} onClose={() => setPending(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          {t("common.unsavedTitle", "Є незбережені зміни")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t("common.unsavedText", "Якщо піти зараз, внесені зміни буде втрачено.")}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setPending(null)} autoFocus>
            {t("common.stay", "Залишитись")}
          </Button>
          <Button onClick={leave} color="error">
            {t("common.leaveWithoutSaving", "Піти без збереження")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

/** Sticky sidebar on desktop, scrollable tabs on mobile, content on the right. */
export default function SidebarLayout(props: {
  items: SidebarItem[]; ariaLabel: string; children: ReactNode;
}) {
  return (
    <UnsavedGuardProvider>
      <Inner {...props} />
    </UnsavedGuardProvider>
  );
}