import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import {
  Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Link, Stack, Typography,
} from "@mui/material";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

export default function TestNoticeDialog() {
  // opens on every visit of the page; it is not remembered anywhere
  const [open, setOpen] = useState(true);
  const close = () => setOpen(false);

  return (
    <Dialog
      open={open}
      // a click outside the window or Esc must not close it: only the cross or the button
      onClose={(_, reason) => {
        if (reason === "backdropClick" || reason === "escapeKeyDown") return;
        close();
      }}
      maxWidth="sm"
      fullWidth
      aria-labelledby="test-notice-title"
    >
      {/* the notice is German on purpose, whatever the interface language is */}
      <DialogTitle id="test-notice-title" lang="de" sx={{ fontWeight: 800, color: "#0b2142", pr: 7 }}>
        Hinweis zum Testbetrieb
        <IconButton
          aria-label="Schließen"
          onClick={close}
          sx={{ position: "absolute", right: 12, top: 12, color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent lang="de">
        <Stack spacing={2}>
          <Typography>
            Start Share befindet sich derzeit in der Testphase (Beta). Bitte beachten Sie:
          </Typography>
          <Typography>
            <strong>Testdaten verwenden.</strong> Bitte geben Sie nach Möglichkeit frei erfundene
            Beispieldaten ein und laden Sie keine vertraulichen Originaldokumente hoch.
          </Typography>
          <Typography>
            <strong>Datensparsamkeit.</strong> Wir verarbeiten nur die für den Testbetrieb
            erforderlichen Daten (z. B. E-Mail-Adresse und Profilangaben) und nutzen sie nicht zu
            Werbezwecken. Testkonten und Testdaten werden nach Abschluss der Testphase gelöscht.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Weitere Informationen finden Sie in unserer{" "}
            <Link component={RouterLink} to="/legal/datenschutz" target="_blank" rel="noopener">
              Datenschutzerklärung
            </Link>
            .
          </Typography>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ p: 2.5 }} lang="de">
        <Button variant="contained" startIcon={<CheckIcon />} onClick={close} autoFocus>
          Verstanden
        </Button>
      </DialogActions>
    </Dialog>
  );
}