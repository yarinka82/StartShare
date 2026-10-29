import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutlined";
import DownloadIcon from "@mui/icons-material/Download";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
  LinearProgress, Link, Paper, Stack, Tooltip, Typography,
} from "@mui/material";
import { useRef, useState, type DragEvent } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, api } from "../api/client";
import { errorText, parseError } from "../api/errors";
import type { Deck } from "../api/types";

const formatSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;

interface Props {
  deck: Deck | null;
  /** called after upload / removal so the parent can refresh the completeness checklist */
  onChanged: () => void;
  /** replacing / deleting is blocked while the teaser is approved (status LIVE) */
  locked?: boolean;
  /** upload limit in MB, from the server (PlatformConfig); the same value the server enforces */
  maxMb: number;
}

export default function DeckUpload({ deck, onChanged, locked = false, maxMb }: Props) {
  const { t, i18n } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const max = maxMb;
  const params = { max }; // fills {{max}} in deck.hint and in the size error
  const uploading = progress !== null;

  async function handleFile(file: File) {
    if (locked || uploading) return;
    setError("");

    if (!file.name.toLowerCase().endsWith(".pdf")) return setError(errorText(t, "deck_not_pdf", params));
    if (file.size === 0) return setError(errorText(t, "deck_empty", params));
    if (file.size > max * 1024 * 1024) return setError(errorText(t, "deck_too_large", params));
    // a renamed file is not a PDF: "%PDF-" must appear in the first 1024 bytes (the server checks again)
    if (!(await file.slice(0, 1024).text()).includes("%PDF-")) return setError(errorText(t, "deck_not_pdf", params));

    setProgress(0);
    try {
      await api.uploadDeck(file, setProgress);
      onChanged();
    } catch (ex) {
      if (ex instanceof ApiError && ex.status === 413) {
        // the web server (nginx) rejected it before Django: its limit is lower than the one in the admin
        setError(errorText(t, "deck_too_large", params));
      } else {
        const p = parseError(ex);
        setError(errorText(t, p.fields.file?.[0] ?? p.detail, params));
      }
    } finally {
      setProgress(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (locked) return;
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  async function remove() {
    setConfirmOpen(false);
    try {
      await api.deleteDeck();
      onChanged();
    } catch (ex) {
      setError(errorText(t, parseError(ex).detail));
    }
  }

  return (
    <Stack spacing={2}>
      {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}

      {locked && (
        <Alert severity="info" icon={<LockOutlinedIcon fontSize="inherit" />}>
          {t("deck.lockedHint", "Тизер опубліковано (LIVE). Для заміни або видалення презентації спочатку переведіть профіль у режим паузи.")}
        </Alert>
      )}

      {deck && (
        <Paper variant="outlined" sx={{ p: 2, bgcolor: locked ? "#fafafa" : "background.paper" }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { sm: "center" } }}>
            <PictureAsPdfIcon color="error" fontSize="large" />
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Typography noWrap sx={{ fontWeight: 600 }}>{deck.original_name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {formatSize(deck.size)} ·{" "}
                {t("deck.uploaded", { date: new Date(deck.uploaded_at).toLocaleDateString(i18n.resolvedLanguage) })}
              </Typography>
            </Box>
            <CheckCircleOutlineIcon color="success" />

            <Button component={Link} href={api.deckDownloadUrl} startIcon={<DownloadIcon />} size="small">
              {t("deck.download")}
            </Button>

            <Tooltip title={locked ? t("deck.lockedDeleteTooltip", "Неможливо видалити під час статусу LIVE") : ""}>
              <span>
                <Button
                  color="error" startIcon={<DeleteOutlineIcon />} size="small"
                  onClick={() => setConfirmOpen(true)} disabled={uploading || locked}
                >
                  {t("deck.remove")}
                </Button>
              </span>
            </Tooltip>
          </Stack>
        </Paper>
      )}

      {!locked && (
        <Box
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          sx={{
            border: "2px dashed", borderColor: dragOver ? "primary.main" : "divider", borderRadius: 2,
            bgcolor: dragOver ? "action.hover" : "transparent", p: 3, textAlign: "center",
          }}
        >
          <UploadFileIcon color="action" fontSize="large" />
          <Typography>
            {deck ? t("deck.replace") + ": " : ""}
            {t("deck.dropHere")}{" "}
            <Link component="button" type="button" onClick={() => inputRef.current?.click()} disabled={uploading}>
              {t("deck.choose")}
            </Link>
          </Typography>
          <Typography variant="body2" color="text.secondary">{t("deck.hint", params)}</Typography>
          <input
            ref={inputRef} type="file" accept="application/pdf,.pdf" hidden
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleFile(f); }}
          />
          {uploading && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2">{t("deck.uploading")} {progress}%</Typography>
              <LinearProgress variant="determinate" value={progress ?? 0} />
            </Box>
          )}
        </Box>
      )}

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>{t("deck.removeTitle")}</DialogTitle>
        <DialogContent><DialogContentText>{t("deck.removeText")}</DialogContentText></DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)}>{t("common.cancel")}</Button>
          <Button color="error" onClick={remove}>{t("common.delete")}</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}