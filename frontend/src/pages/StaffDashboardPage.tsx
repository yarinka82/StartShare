
import AssessmentIcon from "@mui/icons-material/Assessment";
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import GavelIcon from "@mui/icons-material/Gavel";
import PeopleIcon from "@mui/icons-material/People";
import ShieldIcon from "@mui/icons-material/Shield";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import StaffModerationPage from "../components/StaffModerationPage";
import {useAuth} from "../auth/AuthContext";
import {api} from "../api/client";

export default function StaffDashboardPage() {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<number>(0);
  const [users, setUsers] = useState<any[]>([]);
  const [consents, setConsents] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const { user: currentUser } = useAuth();
  const [actionError, setActionError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Завантаження даних залежно від активного таба
  useEffect(() => {
    if (activeTab === 1) {
      setLoading(true);
      fetch("/api/auth/staff/users/", { credentials: "include" })
        .then((r) => r.json())
        .then(setUsers)
        .finally(() => setLoading(false));
    } else if (activeTab === 2) {
      setLoading(true);
      fetch("/api/auth/staff/consents/", { credentials: "include" })
        .then((r) => r.json())
        .then(setConsents)
        .finally(() => setLoading(false));
    } else if (activeTab === 3) {
      setLoading(true);
      fetch("/api/auth/staff/events/", { credentials: "include" })
        .then((r) => r.json())
        .then(setEvents)
        .finally(() => setLoading(false));
    }
  }, [activeTab]);

  const handleToggleUserActive = async (userId: number) => {
    setActionError(null);
    try {
      // 🚀 Викликаємо через api (токен підтягнеться сам)
      await api.toggleUserActive(userId);

      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: !u.is_active } : u))
      );
    } catch (err: any) {
      setActionError(err.message || "Помилка при зміні статусу.");
    }
  };

  return (
    <Stack spacing={3} sx={{ maxWidth: 1300, width: "100%", mx: "auto", py: 4, px: { xs: 2, sm: 3 } }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <ShieldIcon sx={{ fontSize: 40, color: "#17407a" }} />
        <Box>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 800, color: "#0b2142" }}>
            {t("staff.dashboard.title", "Адміністративна панель платформи")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("staff.dashboard.subtitle", "Керування комплаєнсом DSA, модерація користувачів та аудит за стандартами Німеччини.")}
          </Typography>
        </Box>
      </Box>

      {/* АДАПТИВНА НАВІГАЦІЯ: scrollable гарантує, що жоден таб не зімнеться */}
      <Paper variant="outlined" sx={{ borderRadius: 2, bgcolor: "#ffffff" }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 700,
              fontSize: "0.92rem",
              py: 2,
              px: { xs: 2, sm: 3 },
              minHeight: 56,
            },
          }}
        >
          <Tab icon={<GavelIcon />} iconPosition="start" label={t("staff.dashboard.tabs.moderation", "Модерація DSA (ст. 16)")} />
          <Tab icon={<PeopleIcon />} iconPosition="start" label={t("staff.dashboard.tabs.users", "Користувачі та Інвестори")} />
          <Tab icon={<CheckCircleIcon />} iconPosition="start" label={t("staff.dashboard.tabs.consents", "Аудит згод (DSGVO)")} />
          <Tab icon={<AssessmentIcon />} iconPosition="start" label={t("staff.dashboard.tabs.events", "Журнал подій (Audit Log)")} />
        </Tabs>
      </Paper>

      {/* ТАБ 0: МОДЕРАЦІЯ СКАРГ DSA */}
      {activeTab === 0 && <StaffModerationPage />}

      {/* ТАБ 1: КОРИСТУВАЧІ ТА ІНВЕСТОРИ */}
      {activeTab === 1 && (
        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
          {actionError && <Alert severity="error" sx={{ m: 2 }} onClose={() => setActionError(null)}>{actionError}</Alert>}

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>
          ) : (
            <Table size="small">
              <TableHead sx={{ bgcolor: "#f8fafc" }}>
                <TableRow>
                  <TableCell><strong>{t("common.email", "Email")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.table.role", "Роль")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.table.orgMandate", "Організація / Мандат")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.table.status", "Статус")}</strong></TableCell>
                  <TableCell align="right"><strong>{t("staff.dashboard.table.action", "Дія")}</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((u) => {
                  // Перевірка: чи це співробітник, або поточний залогінений користувач
                  const isStaffOrSelf = u.role === "staff" || u.email === currentUser?.email;

                  return (
                    <TableRow key={u.id} hover>
                      <TableCell>{u.email}</TableCell>
                      <TableCell>
                        <Chip
                          label={u.role}
                          size="small"
                          color={u.role === "investor" ? "primary" : u.role === "startup" ? "success" : "default"}
                        />
                      </TableCell>
                      <TableCell>
                        {u.organization_name ? (
                          <>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>{u.organization_name}</Typography>
                            {u.mandate && (
                              <Typography variant="caption" color="text.secondary">
                                v{u.mandate.version}: {u.mandate.check_range}
                              </Typography>
                            )}
                          </>
                        ) : "—"}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={u.is_active ? t("staff.dashboard.status.active", "Активний") : t("staff.dashboard.status.blocked", "Заблокований")}
                          size="small"
                          color={u.is_active ? "success" : "error"}
                          variant="outlined"
                        />
                      </TableCell>

                      {/* КОЛОНКА ДІЇ З ЗАХИСТОМ */}
                      <TableCell align="right">
                        {isStaffOrSelf ? (
                          <Chip
                            label={t("staff.protectedUser", "Захищено (Staff)")}
                            size="small"
                            sx={{ bgcolor: "#f1f5f9", color: "#64748b", fontSize: "0.75rem", fontWeight: 600 }}
                          />
                        ) : (
                          <Button
                            size="small"
                            color={u.is_active ? "error" : "success"}
                            startIcon={u.is_active ? <BlockIcon /> : <CheckCircleIcon />}
                            onClick={() => handleToggleUserActive(u.id)}
                            sx={{ textTransform: "none", fontWeight: 600 }}
                          >
                            {u.is_active ? t("staff.dashboard.actions.block", "Заблокувати") : t("staff.dashboard.actions.unblock", "Розблокувати")}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      )}

      {/* ТАБ 2: АУДИТ ЮРИДИЧНИХ ЗГОД (DSGVO Art. 7) */}
      {activeTab === 2 && (
        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>
          ) : (
            <Table size="small">
              <TableHead sx={{ bgcolor: "#f8fafc" }}>
                <TableRow>
                  <TableCell><strong>{t("staff.dashboard.consents.user", "Користувач")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.consents.document", "Документ")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.consents.version", "Версія")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.consents.context", "Контекст")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.consents.acceptedAt", "Дата та час згоди")}</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {consents.map((c) => (
                  <TableRow key={c.id} hover>
                    <TableCell>{c.user_email}</TableCell>
                    <TableCell><Chip label={c.document_code} size="small" variant="outlined" /></TableCell>
                    <TableCell>v{c.document_version}</TableCell>
                    <TableCell>{c.context}</TableCell>
                    <TableCell>{new Date(c.accepted_at).toLocaleString(i18n.resolvedLanguage)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      )}

      {/* ТАБ 3: ЖУРНАЛ ПОДІЙ (Append-Only Event Log) */}
      {activeTab === 3 && (
        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>
          ) : (
            <Table size="small">
              <TableHead sx={{ bgcolor: "#f8fafc" }}>
                <TableRow>
                  <TableCell><strong>{t("staff.dashboard.events.time", "Час")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.events.event", "Подія")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.events.role", "Роль")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.events.userId", "User ID")}</strong></TableCell>
                  <TableCell><strong>{t("staff.dashboard.events.properties", "Параметри (JSON)")}</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events.map((e) => (
                  <TableRow key={e.id} hover>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      {new Date(e.created_at).toLocaleString(i18n.resolvedLanguage)}
                    </TableCell>
                    <TableCell><Chip label={e.name} size="small" color="primary" variant="outlined" /></TableCell>
                    <TableCell>{e.role}</TableCell>
                    <TableCell>{e.user_id}</TableCell>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: "0.75rem", wordBreak: "break-all" }}>
                      {JSON.stringify(e.properties)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TableContainer>
      )}
    </Stack>
  );
}