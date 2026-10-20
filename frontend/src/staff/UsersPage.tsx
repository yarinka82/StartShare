import BlockIcon from "@mui/icons-material/Block";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import SearchIcon from "@mui/icons-material/Search";
import {
  Alert, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, InputAdornment,
  Stack, TextField, ToggleButton, ToggleButtonGroup, Typography,
} from "@mui/material";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import StaffTable, { type Column } from "./StaffTable";
import { useStaffList } from "./useStaffList";

interface StaffUser {
  id: number;
  email: string;
  role: string;
  is_active: boolean;
  organization_name?: string | null;
  mandate?: { version: number; check_range: string } | null;
}

export default function StaffUsersPage() {
  const { t } = useTranslation();
  const { user: currentUser } = useAuth();
  const { rows, setRows, loading, error, reload } = useStaffList<StaffUser>("/api/auth/staff/users/");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("all");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<StaffUser | null>(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter(
      (u) =>
        (role === "all" || u.role === role) &&
        (!q || u.email.toLowerCase().includes(q) || (u.organization_name ?? "").toLowerCase().includes(q)),
    );
  }, [rows, query, role]);

  async function toggle(u: StaffUser) {
    setActionError(null);
    setBusyId(u.id);
    try {
      await api.toggleUserActive(u.id);
      setRows((prev) => prev.map((x) => (x.id === u.id ? { ...x, is_active: !x.is_active } : x)));
    } catch (e) {
      setActionError((e as Error)?.message || t("staff.dashboard.actionError", "Помилка при зміні статусу."));
    } finally {
      setBusyId(null);
    }
  }

  const columns: Column<StaffUser>[] = [
    { key: "email", label: t("common.email", "Email"), render: (u) => u.email },
    {
      key: "role", label: t("staff.dashboard.table.role", "Роль"),
      render: (u) => (
        <Chip label={u.role} size="small" color={u.role === "investor" ? "primary" : u.role === "startup" ? "success" : "default"} />
      ),
    },
    {
      key: "org", label: t("staff.dashboard.table.orgMandate", "Організація / Мандат"),
      render: (u) =>
        u.organization_name ? (
          <>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>{u.organization_name}</Typography>
            {u.mandate && (
              <Typography variant="caption" color="text.secondary">v{u.mandate.version}: {u.mandate.check_range}</Typography>
            )}
          </>
        ) : "—",
    },
    {
      key: "status", label: t("staff.dashboard.table.status", "Статус"),
      render: (u) => (
        <Chip
          label={u.is_active ? t("staff.dashboard.status.active", "Активний") : t("staff.dashboard.status.blocked", "Заблокований")}
          size="small" color={u.is_active ? "success" : "error"} variant="outlined"
        />
      ),
    },
    {
      key: "action", label: t("staff.dashboard.table.action", "Дія"), align: "right",
      render: (u) => {
        const protectedUser = u.role === "staff" || u.email === currentUser?.email;
        if (protectedUser) {
          return (
            <Chip
              label={t("staff.protectedUser", "Захищено (Staff)")} size="small"
              sx={{ bgcolor: "#f1f5f9", color: "#64748b", fontSize: "0.75rem", fontWeight: 600 }}
            />
          );
        }
        return (
          <Button
            size="small" disabled={busyId === u.id}
            color={u.is_active ? "error" : "success"}
            startIcon={u.is_active ? <BlockIcon /> : <CheckCircleIcon />}
            onClick={() => (u.is_active ? setConfirm(u) : void toggle(u))} // blocking asks first
          >
            {u.is_active ? t("staff.dashboard.actions.block", "Заблокувати") : t("staff.dashboard.actions.unblock", "Розблокувати")}
          </Button>
        );
      },
    },
  ];

  return (
    <Stack spacing={2}>
      {actionError && <Alert severity="error" onClose={() => setActionError(null)}>{actionError}</Alert>}

      <StaffTable
        columns={columns} rows={filtered} getKey={(u) => u.id}
        loading={loading} error={error} onRetry={() => void reload()}
        toolbar={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" } }}>
            <TextField
              size="small" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder={t("staff.dashboard.searchUsers", "Пошук за email або організацією")}
              slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
              sx={{ maxWidth: 360 }}
            />
            <ToggleButtonGroup size="small" exclusive value={role} onChange={(_, v: string | null) => v && setRole(v)}>
              <ToggleButton value="all" sx={{ textTransform: "none" }}>{t("staff.dashboard.filter.all")}</ToggleButton>
              <ToggleButton value="startup" sx={{ textTransform: "none" }}>{t("roles.startup")}</ToggleButton>
              <ToggleButton value="investor" sx={{ textTransform: "none" }}>{t("roles.investor")}</ToggleButton>
              <ToggleButton value="staff" sx={{ textTransform: "none" }}>Staff</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        }
      />

      <Dialog open={!!confirm} onClose={() => setConfirm(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>{t("staff.dashboard.confirmBlockTitle", "Заблокувати користувача?")}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t("staff.dashboard.confirmBlockText", "Користувач {{email}} більше не зможе увійти в систему.", { email: confirm?.email })}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button color="inherit" onClick={() => setConfirm(null)}>{t("common.cancel", "Скасувати")}</Button>
          <Button
            color="error" variant="contained"
            onClick={() => { const u = confirm; setConfirm(null); if (u) void toggle(u); }}
          >
            {t("staff.dashboard.actions.block", "Заблокувати")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}