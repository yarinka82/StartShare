import {
  Alert, Box, Button, CircularProgress, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TablePagination, TableRow, Typography,
} from "@mui/material";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

export type Column<T> = {
  key: string;
  label: string;
  align?: "left" | "right";
  nowrap?: boolean;
  render: (row: T) => ReactNode;
};

/** Table shell for the staff area: loading / error / empty states, sticky header, pagination. */
export default function StaffTable<T>({ columns, rows, getKey, loading, error, onRetry, toolbar }: {
  columns: Column<T>[];
  rows: T[];
  getKey: (row: T) => string | number;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  toolbar?: ReactNode;
}) {
  const { t } = useTranslation();
  const [page, setPage] = useState(0);
  const [perPage, setPerPage] = useState(25);

  const lastPage = Math.max(0, Math.ceil(rows.length / perPage) - 1);
  const current = Math.min(page, lastPage); // filters can shrink the list
  const visible = rows.slice(current * perPage, current * perPage + perPage);

  return (
    <Paper variant="outlined" sx={{ borderRadius: 3, overflow: "hidden" }}>
      {toolbar && <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>{toolbar}</Box>}

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress /></Box>
      ) : error ? (
        <Alert
          severity="error" sx={{ m: 2 }}
          action={<Button color="inherit" size="small" onClick={onRetry}>{t("common.tryAgain", "Повторити")}</Button>}
        >
          {t("staff.loadError", "Не вдалося завантажити дані.")}
        </Alert>
      ) : rows.length === 0 ? (
        <Typography color="text.secondary" sx={{ py: 6, textAlign: "center" }}>
          {t("staff.empty", "Записів немає.")}
        </Typography>
      ) : (
        <>
          <TableContainer sx={{ maxHeight: "68vh" }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {columns.map((c) => (
                    <TableCell key={c.key} align={c.align} sx={{ fontWeight: 700, bgcolor: "#f8fafc" }}>
                      {c.label}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {visible.map((row) => (
                  <TableRow key={getKey(row)} hover>
                    {columns.map((c) => (
                      <TableCell key={c.key} align={c.align} sx={c.nowrap ? { whiteSpace: "nowrap" } : undefined}>
                        {c.render(row)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div" count={rows.length} page={current} rowsPerPage={perPage}
            rowsPerPageOptions={[25, 50, 100]}
            onPageChange={(_, p) => setPage(p)}
            onRowsPerPageChange={(e) => { setPerPage(Number(e.target.value)); setPage(0); }}
          />
        </>
      )}
    </Paper>
  );
}