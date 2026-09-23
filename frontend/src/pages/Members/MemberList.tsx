
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  Box,
  Typography,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableSortLabel,
  Chip,
  Button,
  ToggleButton,
  ToggleButtonGroup,
  TextField,
  InputAdornment,
  CircularProgress,
  Paper,
  Tooltip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Alert,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import VerifiedIcon from '@mui/icons-material/Verified';
import DeleteOutlineIcon from '@mui/icons-material/Delete';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import TableViewIcon from '@mui/icons-material/TableView';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';

import { apiFetch } from "@/api/client.ts";
import { tokens } from "@/pages/Members/components/theme.ts";
import {toast} from "@/components/Notifier.tsx";

interface Member {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  join_date: string;
  status: 'active' | 'inactive';
  is_founder: boolean;
}

type FounderFilter = 'all' | 'founders';
type StatusFilter = 'all' | 'active' | 'inactive';

const formatDate = (isoDate: string) => {
  const d = dayjs(isoDate);
  return d.isValid() ? d.format('DD.MM.YYYY') : isoDate;
};

const MemberList: React.FC = () => {
  const { t } = useTranslation();
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [founderFilter, setFounderFilter] = useState<FounderFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [query, setQuery] = useState('');

  // Меню экспорта
  const [exportAnchorEl, setExportAnchorEl] = useState<null | HTMLElement>(null);

  const [deleteTarget, setDeleteTarget] = useState<Member | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const loadMembers = () => {
    setLoading(true);
    setError(null);
    fetch('/api/members/')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: Member[]) => setMembers(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadMembers();
  }, []);

  const filtered = useMemo(() => {
    return members
      .filter((m) => (founderFilter === 'founders' ? m.is_founder : true))
      .filter((m) => (statusFilter === 'all' ? true : m.status === statusFilter))
      .filter((m) => {
        if (!query.trim()) return true;
        const q = query.toLowerCase();
        return (
          m.first_name.toLowerCase().includes(q) ||
          m.last_name.toLowerCase().includes(q) ||
          m.email.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => {
        const diff = dayjs(a.join_date).valueOf() - dayjs(b.join_date).valueOf();
        return sortOrder === 'asc' ? diff : -diff;
      });
  }, [members, founderFilter, statusFilter, query, sortOrder]);

  // ---- 1. Экспорт в CSV (с поддержкой Excel UTF-8) ----
  const handleExportCSV = () => {
    setExportAnchorEl(null);
    if (!filtered.length) {
      toast.warning(t('members.exportEmpty', 'Немає даних для експорту'));
      return;
    }

    try {
      const headers = [
        t('members.fullName', 'ПІБ'),
        t('members.email', 'Email'),
        t('members.phone', 'Телефон'),
        t('members.joinedDate', 'Дата вступу'),
        t('members.status', 'Статус'),
        t('members.isFounder', 'Засновник'),
      ];

      const rows = filtered.map((m) => [
        `"${m.last_name} ${m.first_name}"`,
        `"${m.email || ''}"`,
        `"${m.phone || ''}"`,
        `"${formatDate(m.join_date)}"`,
        `"${m.status === 'active' ? t('members.statusActive', 'Активний') : t('members.statusInactive', 'Неактивний')}"`,
        `"${m.is_founder ? t('common.yes', 'Так') : t('common.no', 'Ні')}"`,
      ]);

      const csvContent = '\uFEFF' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `members_${dayjs().format('YYYY-MM-DD')}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success(t('members.exportCSVSuccess', 'CSV-файл завантажено'));
    } catch (err) {
      console.error('CSV export error:', err);
      toast.error(t('members.exportError', 'Помилка експорту'));
    }
  };

  // ---- 2. Экспорт в PDF (через окно печати с готовыми стилями) ----
   const handleExportPDF = () => {
    setExportAnchorEl(null);
    if (!filtered.length) {
      toast.warning(t('members.exportEmpty', 'Немає даних для експорту'));
      return;
    }
  
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toast.error(t('members.exportPopupBlocked', 'Браузер заблокував спливаюче вікно. Дозвольте спливаючі вікна для цього сайту.'));
      return;
    }

    try {
      const htmlContent = `
        <!DOCTYPE html>
        <html>
          <head>
            <title>${t('members.title', 'Члени організації')} - ${dayjs().format('DD.MM.YYYY')}</title>
            <style>
              body { font-family: Arial, sans-serif; padding: 20px; color: #1a1a1a; }
              h2 { margin-bottom: 5px; }
              p { margin-top: 0; color: #666; font-size: 13px; }
              table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }
              th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
              th { background-color: #f4f4f4; font-weight: bold; }
              tr:nth-child(even) { background-color: #fafafa; }
              .founder { font-weight: bold; color: #b8860b; }
              @media print {
                @page { size: landscape; margin: 10mm; }
              }
            </style>
          </head>
          <body>
            <h2>${t('members.title', 'Список членів організації')}</h2>
            <p>${t('members.totalRecords', { count: filtered.length })} | ${dayjs().format('DD.MM.YYYY HH:mm')}</p>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>${t('members.fullName', 'ПІБ')}</th>
                  <th>${t('members.email', 'Email')}</th>
                  <th>${t('members.phone', 'Телефон')}</th>
                  <th>${t('members.joinedDate', 'Дата вступу')}</th>
                  <th>${t('members.status', 'Статус')}</th>
                </tr>
              </thead>
              <tbody>
                ${filtered
                  .map(
                    (m, idx) => `
                  <tr>
                    <td>${idx + 1}</td>
                    <td>${m.last_name} ${m.first_name} ${m.is_founder ? '<span class="founder">★</span>' : ''}</td>
                    <td>${m.email || '—'}</td>
                    <td>${m.phone || '—'}</td>
                    <td>${formatDate(m.join_date)}</td>
                    <td>${m.status === 'active' ? t('members.statusActive', 'Активний') : t('members.statusInactive', 'Неактивний')}</td>
                  </tr>
                `
                  )
                  .join('')}
              </tbody>
            </table>
            <script>
              window.onload = () => {
                window.print();
                window.onafterprint = () => window.close();
              };
            </script>
          </body>
        </html>
      `;

      printWindow.document.write(htmlContent);
      printWindow.document.close();

      toast.success(t('members.exportPDFSuccess', 'PDF відкрито для друку'));
    } catch (err) {
      console.error('PDF export error:', err);
      toast.error(t('members.exportError', 'Помилка експорту'));
      printWindow.close();
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await apiFetch(`/api/members/${deleteTarget.id}/`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) {
        throw new Error(`HTTP ${res.status}`);
      }
      setMembers((prev) => prev.filter((m) => m.id !== deleteTarget.id));
      toast.success(t('members.deleteSuccess', 'Члена видалено'));
      setDeleteTarget(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('members.deleteError');
      setDeleteError(message);
      toast.error(message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 1100, mx: 'auto', px: { xs: 2, md: 4 }, py: 4 }}>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 2,
          mb: 1,
        }}
      >
        <Box>
          <Typography
            variant="overline"
            sx={{
              color: tokens.muted,
              fontFamily: '"IBM Plex Mono", monospace',
              letterSpacing: '0.12em',
            }}
          >
            {t('members.registryTitle')}
          </Typography>
          <Typography variant="h4" sx={{ color: tokens.ink, lineHeight: 1.1 }}>
            {t('members.title')}
          </Typography>
        </Box>

        {/* Кнопки действий: Экспорт + Добавить */}
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
          <Button
            variant="outlined"
            startIcon={<FileDownloadIcon />}
            onClick={(e) => setExportAnchorEl(e.currentTarget)}
            disabled={filtered.length === 0}
            sx={{ borderColor: tokens.divider, color: tokens.ink }}
          >
            {t('common.export', 'Експорт')}
          </Button>

          {/* Меню выбора формата экспорта */}
          <Menu
            anchorEl={exportAnchorEl}
            open={Boolean(exportAnchorEl)}
            onClose={() => setExportAnchorEl(null)}
          >
            <MenuItem onClick={handleExportCSV}>
              <ListItemIcon>
                <TableViewIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{t('common.exportCSV', 'Експорт у CSV (Excel)')}</ListItemText>
            </MenuItem>
            <MenuItem onClick={handleExportPDF}>
              <ListItemIcon>
                <PictureAsPdfIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>{t('common.exportPDF', 'Експорт у PDF')}</ListItemText>
            </MenuItem>
          </Menu>

          <Button
            component={RouterLink}
            to="/members/add"
            variant="contained"
            startIcon={<AddIcon />}
            sx={{
              bgcolor: tokens.registry,
              '&:hover': { bgcolor: tokens.registryDark },
            }}
          >
            {t('members.addMember')}
          </Button>
        </Box>
      </Box>

      <Typography variant="body2" sx={{ color: tokens.muted, mb: 3 }}>
        {t('members.totalRecords', { count: filtered.length })}
        {founderFilter === 'founders' ? ` · ${t('members.onlyFounders')}` : ''}
      </Typography>

      {/* Controls */}
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 3, alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder={t('members.searchPlaceholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ minWidth: 400, bgcolor: tokens.paperElevated }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" sx={{ color: tokens.muted }} />
                </InputAdornment>
              ),
            },
          }}
        />

        <ToggleButtonGroup
          value={founderFilter}
          exclusive
          size="small"
          onChange={(_, val) => val && setFounderFilter(val)}
          sx={{
            bgcolor: tokens.paperElevated,
            '& .MuiToggleButton-root.Mui-selected': {
              bgcolor: tokens.registry,
              color: '#fff',
              '&:hover': { bgcolor: tokens.registryDark },
            },
          }}
        >
          <ToggleButton value="all">{t('members.all')}</ToggleButton>
          <ToggleButton value="founders">{t('members.founders')}</ToggleButton>
        </ToggleButtonGroup>

        <ToggleButtonGroup
          value={statusFilter}
          exclusive
          size="small"
          onChange={(_, val) => val && setStatusFilter(val)}
          sx={{
            bgcolor: tokens.paperElevated,
            '& .MuiToggleButton-root.Mui-selected': {
              bgcolor: tokens.registry,
              color: '#fff',
              '&:hover': { bgcolor: tokens.registryDark },
            },
          }}
        >
          <ToggleButton value="all">{t('members.all')}</ToggleButton>
          <ToggleButton value="active">{t('members.statusActive')}</ToggleButton>
          <ToggleButton value="inactive">{t('members.statusInactive')}</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Table */}
      <Paper
        variant="outlined"
        sx={{ borderColor: tokens.divider, bgcolor: tokens.paperElevated, overflow: 'hidden' }}
      >
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress sx={{ color: tokens.registry }} />
          </Box>
        ) : error ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography sx={{ color: tokens.danger, fontWeight: 500 }}>
              {t('members.loadError', { error })}
            </Typography>
          </Box>
        ) : filtered.length === 0 ? (
          <Box sx={{ p: 6, textAlign: 'center' }}>
            <Typography variant="h6" sx={{ color: tokens.ink, mb: 1 }}>
              {t('members.emptyTitle')}
            </Typography>
            <Typography variant="body2" sx={{ color: tokens.muted, mb: 2 }}>
              {t('members.emptyDescription')}
            </Typography>
            <Button component={RouterLink} to="/members/add" variant="outlined">
              {t('members.addMember')}
            </Button>
          </Box>
        ) : (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>{t('members.fullName')}</TableCell>
                <TableCell>{t('members.email')}</TableCell>
                <TableCell>{t('members.phone')}</TableCell>
                <TableCell sortDirection={sortOrder}>
                  <TableSortLabel
                    active
                    direction={sortOrder}
                    onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
                  >
                    {t('members.joinedDate')}
                  </TableSortLabel>
                </TableCell>

                <TableCell>{t('members.status')}</TableCell>

                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {filtered.map((m) => (
                <TableRow
                  key={m.id}
                  component={RouterLink}
                  to={`/members/${m.id}`}
                  hover
                  sx={{
                    textDecoration: 'none',
                    cursor: 'pointer',
                    '& td': { color: tokens.ink },
                  }}
                >
                  <TableCell sx={{ fontWeight: 500 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      {m.last_name} {m.first_name}
                      {m.is_founder && (
                        <Tooltip title={t('members.founderTooltip')}>
                          <VerifiedIcon
                            sx={{ fontSize: 18, color: tokens.sealGold }}
                          />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '0.85rem' }}>
                    {m.email}
                  </TableCell>
                  <TableCell sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '0.85rem' }}>
                    {m.phone || '—'}
                  </TableCell>
                  <TableCell sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '0.85rem' }}>
                    {formatDate(m.join_date)}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={m.status === 'active' ? t('members.statusActive') : t('members.statusInactive')}
                      size="small"
                      sx={{
                        bgcolor: m.status === 'active' ? 'rgba(47,111,94,0.12)' : 'rgba(154,165,160,0.15)',
                        color: m.status === 'active' ? tokens.registryDark : tokens.muted,
                        fontWeight: 500,
                        border: '1px solid',
                        borderColor: m.status === 'active' ? tokens.registry : tokens.divider,
                      }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('members.delete')}>
                      <IconButton
                        size="small"
                        sx={{ color: tokens.muted, '&:hover': { color: tokens.danger } }}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          setDeleteError(null);
                          setDeleteTarget(m);
                        }}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>

      {/* Delete confirmation */}
      <Dialog open={Boolean(deleteTarget)} onClose={() => !deleting && setDeleteTarget(null)}>
        <DialogTitle sx={{ color: tokens.ink }}>{t('members.deleteConfirmTitle')}</DialogTitle>
        <DialogContent>
          {deleteError && <Alert severity="error" sx={{ mb: 2 }}>{deleteError}</Alert>}
          <DialogContentText>
            {deleteTarget &&
              t('members.deleteConfirmText', {
                name: `${deleteTarget.last_name} ${deleteTarget.first_name}`,
              })}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={handleDelete}
            color="error"
            variant="contained"
            disabled={deleting}
          >
            {deleting ? t('common.deleting') : t('common.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MemberList;