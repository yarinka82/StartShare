import AddIcon from "@mui/icons-material/Add";
import EditNoteIcon from "@mui/icons-material/EditNote";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

interface LegalDocDto {
  id: number;
  code: string;
  code_display: string;
  language: string;
  version: number;
  title: string;
  body: string;
  is_current: boolean;
  valid_from?: string;
}

const DOCUMENT_CODES = [
  { code: "A", label: "A — Erklärung des Startups (Декларація стартапу)" },
  { code: "B", label: "B — Hinweis auf dem Teaser (Дисклеймер B)" },
  { code: "C", label: "C — Bestätigung Investor (Статус інвестора)" },
  { code: "D", label: "D — Anfrage an das Startup (Запит інтро)" },
  { code: "E", label: "E — Signatur Intro-E-Mail (Підпис листа)" },
  { code: "F", label: "F — Auswahlkriterien (Критерії відбору)" },
  { code: "G", label: "G — Hinweis KI (Застереження ШІ)" },
  { code: "AGB", label: "AGB — Allgemeine Geschäftsbedingungen" },
  { code: "DSE", label: "DSE — Datenschutzerklärung" },
  { code: "IMPRESSUM", label: "IMPRESSUM — Вихідні дані компанії" },
];

function getCsrfToken(): string {
  const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[2]) : "";
}

export default function StaffLegalDocsPage() {
  const { t, i18n } = useTranslation();
  const [docs, setDocs] = useState<LegalDocDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Стан для діалогу створення нової версії
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedCode, setSelectedCode] = useState("A");
  const [selectedLang, setSelectedLang] = useState("de");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [toastSuccess, setToastSuccess] = useState(false);

  const loadDocs = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/auth/staff/legal-documents/", { credentials: "include" });
      if (!res.ok) throw new Error("Не вдалося завантажити документи.");
      const data = await res.json();
      setDocs(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDocs();
  }, []);

  const openEditorFor = (doc?: LegalDocDto) => {
    if (doc) {
      setSelectedCode(doc.code);
      setSelectedLang(doc.language);
      setTitle(doc.title);
      setBody(doc.body);
    } else {
      setSelectedCode("A");
      setSelectedLang("de");
      setTitle("");
      setBody("");
    }
    setDialogOpen(true);
  };

  const handlePublishNewVersion = async () => {
    if (!body.trim()) return;
    try {
      setPublishing(true);
      const res = await fetch("/api/auth/staff/legal-documents/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        credentials: "include",
        body: JSON.stringify({
          code: selectedCode,
          language: selectedLang,
          title: title.trim(),
          body: body.trim(),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Помилка при публікації.");
      }

      setDialogOpen(false);
      setToastSuccess(true);
      void loadDocs();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <Stack spacing={3}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
        <Box>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 800, color: "#0b2142", display: "flex", alignItems: "center", gap: 1 }}>
            <MenuBookOutlinedIcon color="primary" />
            {t("staff.legal.title", "Юридичні тексти та версії (A–G, AGB, DSE)")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("staff.legal.subtitle", "Керування офіційними текстами платформи. Кожне оновлення створює версію v+1 зі збереженням аудиту.")}
          </Typography>
        </Box>

        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => openEditorFor()}
          sx={{ bgcolor: "#17407a", textTransform: "none", fontWeight: 700, "&:hover": { bgcolor: "#0b2142" } }}
        >
          {t("staff.legal.newVersionBtn", "Опублікувати нову редакцію")}
        </Button>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>
        ) : (
          <Table size="small">
            <TableHead sx={{ bgcolor: "#f8fafc" }}>
              <TableRow>
                <TableCell><strong>{t("staff.legal.code", "Код")}</strong></TableCell>
                <TableCell><strong>{t("staff.legal.docTitle", "Назва документа")}</strong></TableCell>
                <TableCell><strong>{t("staff.legal.lang", "Мова")}</strong></TableCell>
                <TableCell><strong>{t("staff.legal.version", "Версія")}</strong></TableCell>
                <TableCell><strong>{t("staff.legal.status", "Статус")}</strong></TableCell>
                <TableCell><strong>{t("staff.legal.validFrom", "Діє з")}</strong></TableCell>
                <TableCell align="right"><strong>{t("staff.dashboard.table.action", "Дія")}</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {docs.map((d) => (
                <TableRow key={d.id} hover>
                  <TableCell>
                    <Chip label={d.code} size="small" sx={{ fontWeight: 800 }} color="primary" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{d.title}</Typography>
                    <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 300, display: "block" }}>
                      {d.body}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={d.language.toUpperCase()} size="small" />
                  </TableCell>
                  <TableCell><strong>v{d.version}</strong></TableCell>
                  <TableCell>
                    <Chip
                      label={d.is_current ? t("staff.legal.active", "Чинна") : t("staff.legal.archived", "Архів")}
                      size="small"
                      color={d.is_current ? "success" : "default"}
                    />
                  </TableCell>
                  <TableCell>
                    {d.valid_from ? new Date(d.valid_from).toLocaleDateString(i18n.resolvedLanguage) : "—"}
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      startIcon={<EditNoteIcon />}
                      onClick={() => openEditorFor(d)}
                      sx={{ textTransform: "none", fontWeight: 600 }}
                    >
                      {t("staff.legal.createNextVersion", "Нова редакція")}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>

      {/* МОДАЛЬНЕ ВІКНО РЕДАКТУВАННЯ ТА ПУБЛІКАЦІЇ НОВОЇ РЕДАКЦІЇ */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800, color: "#0b2142" }}>
          {t("staff.legal.modalTitle", "Публікація нової редакції юридичного документа")}
        </DialogTitle>

        <DialogContent dividers>
          <Stack spacing={2.5}>
            <Alert severity="info" sx={{ fontSize: "0.85rem" }}>
              {t(
                "staff.legal.modalNotice",
                "Збереження створить наступну версію документа (v+1) і автоматично закриє дію поточної версії. Всі минулі згоди користувачів залишаться прив'язаними до попередньої редакції за Art. 7 DSGVO."
              )}
            </Alert>

            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "2fr 1fr" }, gap: 2 }}>
              <FormControl fullWidth size="small">
                <InputLabel>{t("staff.legal.code", "Код документа")}</InputLabel>
                <Select
                  value={selectedCode}
                  label={t("staff.legal.code", "Код документа")}
                  onChange={(e) => setSelectedCode(e.target.value)}
                >
                  {DOCUMENT_CODES.map((item) => (
                    <MenuItem key={item.code} value={item.code}>
                      {item.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth size="small">
                <InputLabel>{t("staff.legal.lang", "Мова")}</InputLabel>
                <Select
                  value={selectedLang}
                  label={t("staff.legal.lang", "Мова")}
                  onChange={(e) => setSelectedLang(e.target.value)}
                >
                  <MenuItem value="de">Deutsch (DE — Офіційний оригінал)</MenuItem>
                  <MenuItem value="en">English (EN — Переклад)</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <TextField
              label={t("staff.legal.docTitle", "Заголовок документа")}
              size="small"
              fullWidth
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            <Box>
              <Typography variant="caption" sx={{ fontWeight: 700, color: "text.secondary", mb: 0.5, display: "block" }}>
                {t("staff.legal.bodyLabel", "Офіційний текст документа (Markdown / Plain Text):")}
              </Typography>
              <TextField
                multiline
                rows={12}
                fullWidth
                value={body}
                onChange={(e) => setBody(e.target.value)}
                slotProps={{
                  htmlInput: {
                    sx: { fontFamily: "monospace", fontSize: "0.88rem", lineHeight: 1.6 },
                  },
                }}
              />
            </Box>
          </Stack>
        </DialogContent>

        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDialogOpen(false)} color="inherit" disabled={publishing}>
            {t("common.cancel", "Скасувати")}
          </Button>
          <Button
            variant="contained"
            onClick={handlePublishNewVersion}
            disabled={publishing || !body.trim()}
            sx={{ bgcolor: "#17407a", "&:hover": { bgcolor: "#0b2142" }, fontWeight: 700 }}
          >
            {publishing ? t("common.saving", "Публікація...") : t("staff.legal.publishAction", "Опублікувати нову редакцію")}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={toastSuccess}
        autoHideDuration={3000}
        onClose={() => setToastSuccess(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity="success" variant="filled" onClose={() => setToastSuccess(false)}>
          {t("staff.legal.publishedToast", "Нову редакцію документа успішно опубліковано!")}
        </Alert>
      </Snackbar>
    </Stack>
  );
}