import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import dayjs, { Dayjs } from 'dayjs';
import quarterOfYear from 'dayjs/plugin/quarterOfYear';
dayjs.extend(quarterOfYear);

import {
  Box,
  Paper,
  Typography,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableContainer,
  Button,
  IconButton,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
  Grid,
} from '@mui/material';

import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import RefreshIcon from '@mui/icons-material/Refresh';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import LayersIcon from '@mui/icons-material/Layers';

import { paymentsApi } from '@/api/payments';
import type { Payment } from '@/types/payments';

type PeriodMode = 'month' | 'quarter' | 'year';

export const FinanceOverviewPage: React.FC = () => {
  const { t, i18n } = useTranslation();

  // Режим периода и текущая опорная дата
  const [periodMode, setPeriodMode] = useState<PeriodMode>('year');
  const [currentDate, setCurrentDate] = useState<Dayjs>(dayjs());

  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Форматирование сумм в EUR под текущий язык
  const formatAmount = useCallback(
    (value: number) => {
      const locale =
        i18n.language === 'de' ? 'de-DE' : i18n.language === 'en' ? 'en-US' : 'uk-UA';

      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value || 0);
    },
    [i18n.language]
  );

  // Расчет дат date_from и date_to исходя из режима
  const { dateFrom, dateTo, periodLabel } = useMemo(() => {
    let from: Dayjs;
    let to: Dayjs;
    let label = '';

    if (periodMode === 'month') {
      from = currentDate.startOf('month');
      to = currentDate.endOf('month');
      label = currentDate.format('MMMM YYYY');
    } else if (periodMode === 'quarter') {
      from = currentDate.startOf('quarter');
      to = currentDate.endOf('quarter');
      label = `${currentDate.year()} - Q${currentDate.quarter()} (${from.format('MMM')} – ${to.format('MMM')})`;
    } else {
      // year
      from = currentDate.startOf('year');
      to = currentDate.endOf('year');
      label = `${currentDate.format('YYYY')} ${t('financeOverview.yearSuffix', 'рік')}`;
    }

    return {
      dateFrom: from.format('YYYY-MM-DD'),
      dateTo: to.format('YYYY-MM-DD'),
      periodLabel: label,
    };
  }, [periodMode, currentDate, t]);

  // Загрузка данных платежей
  const fetchOverviewData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Получаем платежи за выбранный период дат
      const data = await paymentsApi.getPayments({
        date_from: dateFrom,
        date_to: dateTo,
      });
      setPayments(data);
    } catch (err: any) {
      console.error('Error fetching analytics:', err);
      setError(t('financeOverview.loadError', 'Не вдалося завантажити аналітику'));
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, t]);

  useEffect(() => {
    fetchOverviewData();
  }, [fetchOverviewData]);

  // Навигация стрелками < и >
  const handlePrev = () => {
    setCurrentDate((prev) => prev.subtract(1, periodMode));
  };

  const handleNext = () => {
    setCurrentDate((prev) => prev.add(1, periodMode));
  };

  const handleResetToCurrent = () => {
    setCurrentDate(dayjs());
  };

  // --- Группировка данных в строки аналитической таблицы ---
  const matrixData = useMemo(() => {
    // Определяем подинтервалы в зависимости от режима:
    // В режиме 'year' -> 12 месяцев
    // В режиме 'quarter' -> 3 месяца
    // В режиме 'month' -> список всех дней с операциями или группировка по неделям
    const groups: {
      key: string;
      label: string;
      fees: number;
      donations: number;
      sponsorships: number;
      grants: number;
      other: number;
      totalPaid: number;
      totalOwed: number;
    }[] = [];

    if (periodMode === 'year') {
      for (let m = 0; m < 12; m++) {
        const monthDate = currentDate.month(m);
        const monthKey = monthDate.format('YYYY-MM');
        groups.push({
          key: monthKey,
          label: monthDate.format('MMMM'),
          fees: 0,
          donations: 0,
          sponsorships: 0,
          grants: 0,
          other: 0,
          totalPaid: 0,
          totalOwed: 0,
        });
      }
    } else if (periodMode === 'quarter') {
      const startMonth = (currentDate.quarter() - 1) * 3;
      for (let m = startMonth; m < startMonth + 3; m++) {
        const monthDate = currentDate.month(m);
        const monthKey = monthDate.format('YYYY-MM');
        groups.push({
          key: monthKey,
          label: monthDate.format('MMMM YYYY'),
          fees: 0,
          donations: 0,
          sponsorships: 0,
          grants: 0,
          other: 0,
          totalPaid: 0,
          totalOwed: 0,
        });
      }
    } else {
      // month mode - группировка по датам
      const daysInMonth = currentDate.daysInMonth();
      for (let d = 1; d <= daysInMonth; d++) {
        const dayDate = currentDate.date(d);
        const dayKey = dayDate.format('YYYY-MM-DD');
        groups.push({
          key: dayKey,
          label: dayDate.format('DD.MM (dd)'),
          fees: 0,
          donations: 0,
          sponsorships: 0,
          grants: 0,
          other: 0,
          totalPaid: 0,
          totalOwed: 0,
        });
      }
    }

    const groupMap = new Map(groups.map((g) => [g.key, g]));

    // Распределяем суммы платежей
    payments.forEach((p) => {
      const amount = Number(p.amount) || 0;
      const key =
        periodMode === 'month'
          ? p.date
          : dayjs(p.date).format('YYYY-MM');

      let group = groupMap.get(key);
      if (!group) {
        // Запасной вариант для нестандартных дат
        group = {
          key,
          label: p.date,
          fees: 0,
          donations: 0,
          sponsorships: 0,
          grants: 0,
          other: 0,
          totalPaid: 0,
          totalOwed: 0,
        };
        groups.push(group);
        groupMap.set(key, group);
      }

      if (p.status === 'paid') {
        group.totalPaid += amount;
        if (p.type === 'membership_fee') group.fees += amount;
        else if (p.type === 'donation') group.donations += amount;
        else if (p.type === 'sponsorship') group.sponsorships += amount;
        else if (p.type === 'grant') group.grants += amount;
        else group.other += amount;
      } else if (p.status === 'owed') {
        group.totalOwed += amount;
      }
    });

    // Для месячного режима оставляем только дни с ненулевыми данными или отображаем все
    const finalRows =
      periodMode === 'month'
        ? groups.filter((g) => g.totalPaid > 0 || g.totalOwed > 0)
        : groups;

    return finalRows;
  }, [payments, periodMode, currentDate]);

  // Итоговые подсчеты для Total Row и KPI карточек
  const grandTotals = useMemo(() => {
    let fees = 0;
    let donations = 0;
    let sponsorships = 0;
    let grants = 0;
    let other = 0;
    let totalPaid = 0;
    let totalOwed = 0;

    payments.forEach((p) => {
      const amt = Number(p.amount) || 0;
      if (p.status === 'paid') {
        totalPaid += amt;
        if (p.type === 'membership_fee') fees += amt;
        else if (p.type === 'donation') donations += amt;
        else if (p.type === 'sponsorship') sponsorships += amt;
        else if (p.type === 'grant') grants += amt;
        else other += amt;
      } else if (p.status === 'owed') {
        totalOwed += amt;
      }
    });

    return { fees, donations, sponsorships, grants, other, totalPaid, totalOwed };
  }, [payments]);

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, md: 4 }, py: 4 }}>
      {/* 1. Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: '0.1em' }}>
            {t('financeOverview.subtitle', 'Фінансова звітність та аналіз')}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            {t('financeOverview.title', 'Фінансовий огляд')}
          </Typography>
        </Box>

        {/* Переключатель режимов: Месяц / Квартал / Год */}
        <ToggleButtonGroup
          value={periodMode}
          exclusive
          size="small"
          onChange={(_, val) => val && setPeriodMode(val)}
          sx={{ bgcolor: 'background.paper' }}
        >
          <ToggleButton value="month" sx={{ px: 2.5, fontWeight: 600 }}>
            {t('financeOverview.modes.month', 'Місяць')}
          </ToggleButton>
          <ToggleButton value="quarter" sx={{ px: 2.5, fontWeight: 600 }}>
            {t('financeOverview.modes.quarter', 'Квартал')}
          </ToggleButton>
          <ToggleButton value="year" sx={{ px: 2.5, fontWeight: 600 }}>
            {t('financeOverview.modes.year', 'Рік')}
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* 2. Навигатор по периодам с кнопками стрелок (Stepper) */}
      <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <Grid container spacing={2} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, md: 7 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton onClick={handlePrev} size="large" sx={{ bgcolor: 'action.hover' }}>
                <ChevronLeftIcon />
              </IconButton>

              <Box sx={{ flexGrow: 1, textAlign: 'center' }}>
                <Typography variant="h6" sx={{ fontWeight: 700, textTransform: 'capitalize' }}>
                  {periodLabel}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {dayjs(dateFrom).format('DD.MM.YYYY')} — {dayjs(dateTo).format('DD.MM.YYYY')}
                </Typography>
              </Box>

              <IconButton onClick={handleNext} size="large" sx={{ bgcolor: 'action.hover' }}>
                <ChevronRightIcon />
              </IconButton>

              <Button size="small" variant="text" onClick={handleResetToCurrent} sx={{ ml: 1, textTransform: 'none' }}>
                {t('financeOverview.today', 'Поточний')}
              </Button>
            </Box>
          </Grid>

          <Grid size={{ xs: 12, md: 5 }}>
            <Button
              variant="outlined"
              fullWidth
              startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <RefreshIcon />}
              onClick={fetchOverviewData}
              disabled={loading}
              sx={{ height: 44, borderRadius: 2 }}
            >
              {t('common.refresh', 'Оновити дані')}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* 3. Сводные KPI Карточки */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <AccountBalanceWalletIcon sx={{ fontSize: 36, color: 'primary.main' }} />
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t('financeOverview.totalIncomes', 'Всього отримано')}
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {formatAmount(grandTotals.totalPaid)}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <WarningAmberIcon sx={{ fontSize: 36, color: grandTotals.totalOwed > 0 ? 'warning.main' : 'text.disabled' }} />
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t('financeOverview.totalOwed', 'Заборгованість')}
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: grandTotals.totalOwed > 0 ? 'warning.main' : 'text.primary' }}>
                {formatAmount(grandTotals.totalOwed)}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <LayersIcon sx={{ fontSize: 36, color: 'success.main' }} />
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t('payments.types.membership_fee', 'Внески')} / {t('payments.types.grant', 'Гранти')}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {formatAmount(grandTotals.fees)} / {formatAmount(grandTotals.grants)}
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2, borderRadius: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
            <LayersIcon sx={{ fontSize: 36, color: 'info.main' }} />
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t('payments.types.donation', 'Пожертви')} / {t('payments.types.sponsorship', 'Спонсори')}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {formatAmount(grandTotals.donations)} / {formatAmount(grandTotals.sponsorships)}
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* 4. Аналитическая Таблица */}
      <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
        {error && <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : matrixData.length === 0 ? (
          <Box sx={{ p: 6, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              {t('financeOverview.empty', 'Немає фінансових операцій за цей період')}
            </Typography>
          </Box>
        ) : (
          <TableContainer sx={{ maxHeight: 600 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, bgcolor: 'background.paper' }}>
                    {periodMode === 'year'
                      ? t('financeOverview.monthCol', 'Місяць')
                      : periodMode === 'quarter'
                      ? t('financeOverview.monthCol', 'Місяць')
                      : t('financeOverview.dateCol', 'Дата')}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 700, bgcolor: 'background.paper', color: 'primary.dark' }}>
                    {t('payments.types.membership_fee', 'Членські внески')}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 700, bgcolor: 'background.paper' }}>
                    {t('payments.types.donation', 'Пожертви')}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 700, bgcolor: 'background.paper' }}>
                    {t('payments.types.sponsorship', 'Спонсорство')}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 700, bgcolor: 'background.paper' }}>
                    {t('payments.types.grant', 'Гранти')}
                  </TableCell>

                  {grandTotals.other > 0 && (
                    <TableCell align="right" sx={{ fontWeight: 700, bgcolor: 'background.paper' }}>
                      {t('payments.types.other', 'Інше')}
                    </TableCell>
                  )}

                  <TableCell align="right" sx={{ fontWeight: 800, bgcolor: 'background.paper', color: 'success.main' }}>
                    {t('financeOverview.totalPaidCol', 'Всього сплачено')}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 700, bgcolor: 'background.paper', color: 'warning.main' }}>
                    {t('financeOverview.totalOwedCol', 'Борг')}
                  </TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {matrixData.map((row) => (
                  <TableRow key={row.key} hover>
                    <TableCell sx={{ fontWeight: 600, textTransform: 'capitalize' }}>
                      {row.label}
                    </TableCell>

                    <TableCell align="right" sx={{ color: row.fees > 0 ? 'text.primary' : 'text.disabled' }}>
                      {row.fees > 0 ? formatAmount(row.fees) : '—'}
                    </TableCell>

                    <TableCell align="right" sx={{ color: row.donations > 0 ? 'text.primary' : 'text.disabled' }}>
                      {row.donations > 0 ? formatAmount(row.donations) : '—'}
                    </TableCell>

                    <TableCell align="right" sx={{ color: row.sponsorships > 0 ? 'text.primary' : 'text.disabled' }}>
                      {row.sponsorships > 0 ? formatAmount(row.sponsorships) : '—'}
                    </TableCell>

                    <TableCell align="right" sx={{ color: row.grants > 0 ? 'text.primary' : 'text.disabled' }}>
                      {row.grants > 0 ? formatAmount(row.grants) : '—'}
                    </TableCell>

                    {grandTotals.other > 0 && (
                      <TableCell align="right" sx={{ color: row.other > 0 ? 'text.primary' : 'text.disabled' }}>
                        {row.other > 0 ? formatAmount(row.other) : '—'}
                      </TableCell>
                    )}

                    <TableCell align="right" sx={{ fontWeight: 700, color: row.totalPaid > 0 ? 'success.dark' : 'text.disabled' }}>
                      {row.totalPaid > 0 ? formatAmount(row.totalPaid) : '—'}
                    </TableCell>

                    <TableCell align="right" sx={{ fontWeight: 600, color: row.totalOwed > 0 ? 'warning.main' : 'text.disabled' }}>
                      {row.totalOwed > 0 ? formatAmount(row.totalOwed) : '—'}
                    </TableCell>
                  </TableRow>
                ))}

                {/* ИТОГОВАЯ ЗАКРЕПЛЕННАЯ СТРОКА (TOTAL / РАЗОМ) */}
                <TableRow sx={{ bgcolor: 'action.hover', borderTop: '2px solid', borderColor: 'divider' }}>
                  <TableCell sx={{ fontWeight: 800, fontSize: '0.95rem' }}>
                    {t('common.total', 'РАЗОМ')}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    {formatAmount(grandTotals.fees)}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    {formatAmount(grandTotals.donations)}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    {formatAmount(grandTotals.sponsorships)}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 800 }}>
                    {formatAmount(grandTotals.grants)}
                  </TableCell>

                  {grandTotals.other > 0 && (
                    <TableCell align="right" sx={{ fontWeight: 800 }}>
                      {formatAmount(grandTotals.other)}
                    </TableCell>
                  )}

                  <TableCell align="right" sx={{ fontWeight: 900, color: 'success.dark', fontSize: '1rem' }}>
                    {formatAmount(grandTotals.totalPaid)}
                  </TableCell>

                  <TableCell align="right" sx={{ fontWeight: 800, color: grandTotals.totalOwed > 0 ? 'warning.main' : 'inherit' }}>
                    {formatAmount(grandTotals.totalOwed)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
};

export default FinanceOverviewPage;