
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from '@/components/Notifier.tsx';

import {
  Box,
  Paper,
  Typography,
  Divider,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Chip,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
  Stack,
  InputAdornment,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import dayjs, { Dayjs } from 'dayjs';
import { paymentsApi } from '@/api/payments';
import {
  Payment,
  PaymentFormData,
  PaymentStatus,
  PAYMENT_STATUS_LABELS,
} from '@/types/payments';

interface MemberPaymentsHistoryProps {
  memberId: number;
}

const emptyForm = (memberId: number): PaymentFormData => ({
  member: memberId,
  amount: '',
  date: dayjs().format('YYYY-MM-DD'),
  type: 'membership_fee',
  source_name: '',
  period: `${dayjs().year()}`,
  status: 'paid',
  comment: '',
});

const MemberPaymentsHistory = ({ memberId }: MemberPaymentsHistoryProps) => {
  const { t } = useTranslation();

  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<PaymentFormData>(emptyForm(memberId));
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    fetchPayments();
  }, [memberId]);

  const fetchPayments = async () => {
    setLoading(true);
    try {
      const data = await paymentsApi.getPayments({ member: memberId });
      setPayments(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching payments:', err);
      setPayments([]);
      const errMsg = t('payments.messages.loadError', 'Помилка завантаження платежів');
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const openCreateDialog = () => {
    setEditingId(null);
    setForm(emptyForm(memberId));
    setFormError(null);
    setDialogOpen(true);
  };

  const openEditDialog = (payment: Payment) => {
    setEditingId(payment.id);
    setForm({
      member: memberId,
      amount: String(payment.amount),
      date: payment.date,
      type: 'membership_fee',
      source_name: '',
      period: payment.period || '',
      status: payment.status,
      comment: payment.comment || '',
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (saving) return;
    setDialogOpen(false);
  };

  const handleSubmit = async () => {
    if (!form.amount || Number(form.amount) <= 0) {
      const msg = t('payments.validation.amountRequired', 'Вкажіть суму більше нуля');
      setFormError(msg);
      toast.warning(msg);
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (editingId) {
        await paymentsApi.updatePayment(editingId, form);
        toast.success(t('payments.messages.updateSuccess', 'Платіж успішно оновлено'));
      } else {
        await paymentsApi.createPayment(form);
        toast.success(t('payments.messages.createSuccess', 'Платіж успішно додано'));
      }
      setDialogOpen(false);
      await fetchPayments();
    } catch (err: any) {
      console.error('Error saving payment:', err);
      let detailedError = t('payments.messages.saveError', 'Помилка збереження платежу');
      if (err.response?.data) {
        const data = err.response.data;
        detailedError = typeof data === 'string'
          ? data
          : data.detail || Object.values(data).flat().join(' ');
      }
      setFormError(detailedError);
      toast.error(detailedError);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm(t('payments.dialogs.confirmDelete', 'Видалити цей платіж?'))) return;

    try {
      await paymentsApi.deletePayment(id);
      setPayments((prev) => prev.filter((p) => p.id !== id));
      toast.success(t('payments.messages.deleteSuccess', 'Платіж успішно видалено'));
      await fetchPayments();
    } catch (err) {
      console.error('Error deleting payment:', err);
      toast.error(t('payments.messages.deleteError', 'Не вдалося видалити платіж'));
    }
  };

  const totalPaid = payments
    .filter((p) => p.status === 'paid')
    .reduce((sum, p) => sum + Number(p.amount), 0);
  const totalOwed = payments
    .filter((p) => p.status === 'owed')
    .reduce((sum, p) => sum + Number(p.amount), 0);

  return (
    <Paper sx={{ p: 3, mt: 3 }}>
      {/* Верхняя панель */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">
          {t('payments.title.history', 'Історія платежів')}
        </Typography>
        <Button
          variant="contained"
          size="small"
          startIcon={<AddIcon />}
          onClick={openCreateDialog}
        >
          {t('payments.actions.add', 'Додати платіж')}
        </Button>
      </Box>
      <Divider sx={{ my: 2 }} />

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : payments.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
          {t('payments.empty', 'Платежів ще немає')}
        </Typography>
      ) : (
        <>
          {/* Скроллируемый контейнер таблицы с лимитом ~6 строк */}
          <TableContainer
            sx={{
              maxHeight: 310,
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1
            }}
          >
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ bgcolor: 'background.paper' }}>{t('payments.fields.date', 'Дата')}</TableCell>
                  <TableCell sx={{ bgcolor: 'background.paper' }}>{t('payments.fields.type', 'Тип')}</TableCell>
                  <TableCell sx={{ bgcolor: 'background.paper' }}>{t('payments.fields.period', 'Період')}</TableCell>
                  <TableCell sx={{ bgcolor: 'background.paper' }} align="right">{t('payments.fields.amount', 'Сума')}</TableCell>
                  <TableCell sx={{ bgcolor: 'background.paper' }}>{t('payments.fields.status', 'Статус')}</TableCell>
                  <TableCell sx={{ bgcolor: 'background.paper' }} align="right" />
                </TableRow>
              </TableHead>
              <TableBody>
                {payments.map((payment) => (
                  <TableRow key={payment.id} hover>
                    <TableCell>{dayjs(payment.date).format('DD.MM.YYYY')}</TableCell>
                    <TableCell>{t(`payments.types.${payment.type}`)}</TableCell>
                    <TableCell>{payment.period || '—'}</TableCell>
                    <TableCell align="right">{Number(payment.amount).toFixed(2)} €</TableCell>
                    <TableCell>
                      <Chip
                        label={t(`payments.statuses.${payment.status}`)}
                        color={payment.status === 'paid' ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => openEditDialog(payment)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => handleDelete(payment.id)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Всегда видимый закрепленный блок с итогами */}
          <Stack
            direction="row"
            spacing={3}
            sx={{
              mt: 2,
              pt: 1.5,
              borderTop: '1px dashed',
              borderColor: 'divider'
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {t('payments.summary.totalPaid', 'Оплачено')}: <b>{totalPaid.toFixed(2)} €</b>
            </Typography>
            {totalOwed > 0 && (
              <Typography variant="body2" color="warning.main">
                {t('payments.summary.totalOwed', 'Заборговано')}: <b>{totalOwed.toFixed(2)} €</b>
              </Typography>
            )}
          </Stack>
        </>
      )}

      {/* Модальное окно добавления/редактирования */}
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingId
            ? t('payments.dialogs.editTitle', 'Редагувати платіж')
            : t('payments.dialogs.addTitle', 'Новий платіж')}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {formError && <Alert severity="error">{formError}</Alert>}

            {/* 1. Сумма */}
            <TextField
              label={t('payments.fields.amount', 'Сума')}
              type="number"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              slotProps={{
                input: {
                  endAdornment: <InputAdornment position="end">€</InputAdornment>,
                },
              }}
              fullWidth
              autoFocus
            />

            {/* 2. Дата */}
            <DatePicker
              label={t('payments.fields.date', 'Дата')}
              format="DD MM YYYY"
              value={dayjs(form.date)}
              onChange={(value: Dayjs | null) =>
                setForm({ ...form, date: value ? value.format('YYYY-MM-DD') : form.date })
              }
              slotProps={{ textField: { fullWidth: true } }}
            />

            {/* 3. Период */}
            <TextField
              label={t('payments.fields.period', 'Період')}
              placeholder="2026 або 2026-Q1"
              value={form.period || ''}
              onChange={(e) => setForm({ ...form, period: e.target.value })}
              fullWidth
            />

            {/* 4. Статус */}
            <TextField
              select
              label={t('payments.fields.status', 'Статус')}
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value as PaymentStatus })}
              fullWidth
            >
              {(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[]).map((status) => (
                <MenuItem key={status} value={status}>
                  {t(`payments.statuses.${status}`, PAYMENT_STATUS_LABELS[status])}
                </MenuItem>
              ))}
            </TextField>

            {/* 5. Комментарий */}
            <TextField
              label={t('payments.fields.comment', 'Коментар')}
              value={form.comment || ''}
              onChange={(e) => setForm({ ...form, comment: e.target.value })}
              multiline
              minRows={2}
              fullWidth
            />
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={closeDialog} disabled={saving}>
            {t('common.cancel', 'Скасувати')}
          </Button>
          <Button onClick={handleSubmit} variant="contained" disabled={saving}>
            {saving ? <CircularProgress size={20} /> : t('common.save', 'Зберегти')}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default MemberPaymentsHistory;