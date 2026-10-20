import SearchIcon from "@mui/icons-material/Search";
import { Chip, InputAdornment, TextField } from "@mui/material";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import StaffTable, { type Column } from "./StaffTable";
import { useStaffList } from "./useStaffList";

interface Consent {
  id: number;
  user_email: string;
  document_code: string;
  document_version: string | number;
  context: string;
  accepted_at: string;
}

export default function StaffConsentsPage() {
  const { t, i18n } = useTranslation();
  const { rows, loading, error, reload } = useStaffList<Consent>("/api/auth/staff/consents/");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q
      ? rows.filter((c) => c.user_email.toLowerCase().includes(q) || c.document_code.toLowerCase().includes(q))
      : rows;
  }, [rows, query]);

  const columns: Column<Consent>[] = [
    { key: "user", label: t("staff.dashboard.consents.user", "Користувач"), render: (c) => c.user_email },
    { key: "doc", label: t("staff.dashboard.consents.document", "Документ"), render: (c) => <Chip label={c.document_code} size="small" variant="outlined" /> },
    { key: "ver", label: t("staff.dashboard.consents.version", "Версія"), render: (c) => `v${c.document_version}` },
    { key: "ctx", label: t("staff.dashboard.consents.context", "Контекст"), render: (c) => c.context },
    {
      key: "at", label: t("staff.dashboard.consents.acceptedAt", "Дата та час згоди"), nowrap: true,
      render: (c) => new Date(c.accepted_at).toLocaleString(i18n.resolvedLanguage),
    },
  ];

  return (
    <StaffTable
      columns={columns} rows={filtered} getKey={(c) => c.id}
      loading={loading} error={error} onRetry={() => void reload()}
      toolbar={
        <TextField
          size="small" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder={t("staff.dashboard.searchConsents", "Пошук за email або документом")}
          slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> } }}
          sx={{ maxWidth: 360 }}
        />
      }
    />
  );
}