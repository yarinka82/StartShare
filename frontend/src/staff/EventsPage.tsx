import SearchIcon from "@mui/icons-material/Search";
import { Chip, InputAdornment, TextField, Tooltip, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import StaffTable, { type Column } from "./StaffTable";
import { useStaffList } from "./useStaffList";

interface AuditEvent {
  id: number;
  created_at: string;
  name: string;
  role: string;
  user_id: number | string | null;
  properties: unknown;
}

export default function StaffEventsPage() {
  const { t, i18n } = useTranslation();
  const { rows, loading, error, reload } = useStaffList<AuditEvent>("/api/auth/staff/events/");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q
      ? rows.filter((e) =>
          `${e.name} ${e.role} ${e.user_id ?? ""} ${JSON.stringify(e.properties)}`.toLowerCase().includes(q))
      : rows;
  }, [rows, query]);

  const columns: Column<AuditEvent>[] = [
    {
      key: "time", label: t("staff.dashboard.events.time", "Час"), nowrap: true,
      render: (e) => new Date(e.created_at).toLocaleString(i18n.resolvedLanguage),
    },
    { key: "name", label: t("staff.dashboard.events.event", "Подія"), render: (e) => <Chip label={e.name} size="small" color="primary" variant="outlined" /> },
    { key: "role", label: t("staff.dashboard.events.role", "Роль"), render: (e) => e.role },
    { key: "uid", label: t("staff.dashboard.events.userId", "User ID"), render: (e) => e.user_id ?? "—" },
    {
      key: "props", label: t("staff.dashboard.events.properties", "Параметри (JSON)"),
      render: (e) => (
        // one line in the table, the full pretty-printed JSON on hover
        <Tooltip
          title={<pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>{JSON.stringify(e.properties, null, 2)}</pre>}
          slotProps={{ tooltip: { sx: { maxWidth: 560 } } }}
        >
          <Typography noWrap sx={{ fontFamily: "monospace", fontSize: "0.75rem", maxWidth: 360 }}>
            {JSON.stringify(e.properties)}
          </Typography>
        </Tooltip>
      ),
    },
  ];

  return (
    <StaffTable
      columns={columns} rows={filtered} getKey={(e) => e.id}
      loading={loading} error={error} onRetry={() => void reload()}
      toolbar={
        <TextField
          size="small" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder={t("staff.dashboard.searchEvents", "Пошук за подією, роллю, ID або параметрами")}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
          sx={{ maxWidth: 420 }}
        />
      }
    />
  );
}