import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { paymentsApi } from '@/api/payments';
import type { FinancialOverview } from '@/types/payments';

interface DateRange {
  date_from: string;
  date_to: string;
}

function SummaryCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: 'default' | 'warning';
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div
        className={`mt-1 text-2xl font-semibold ${
          tone === 'warning' ? 'text-amber-600' : 'text-gray-900'
        }`}
      >
        {value}
      </div>
    </div>
  );
}

export default function FinancialOverviewPage() {
  const { t, i18n } = useTranslation();

  const [range, setRange] = useState<DateRange>({ date_from: '', date_to: '' });
  const [overview, setOverview] = useState<FinancialOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Динамический формат валюты под выбранный язык
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

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await paymentsApi.getFinancialOverview({
        date_from: range.date_from || undefined,
        date_to: range.date_to || undefined,
      });
      setOverview(data);
    } catch (e) {
      setError(t('financeOverview.loadError', 'Не вдалося завантажити фінансовий огляд'));
    } finally {
      setLoading(false);
    }
  }, [range, t]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      {/* Шапка и фильтры по дате */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-xl font-semibold text-gray-900">
          {t('financeOverview.title', 'Фінансовий огляд')}
        </h1>

        <div className="flex items-end gap-3">
          <label className="flex flex-col text-sm text-gray-600">
            {t('common.dateFrom', 'Від')}
            <input
              type="date"
              className="mt-1 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
              value={range.date_from}
              onChange={(e) => setRange((r) => ({ ...r, date_from: e.target.value }))}
            />
          </label>
          <label className="flex flex-col text-sm text-gray-600">
            {t('common.dateTo', 'До')}
            <input
              type="date"
              className="mt-1 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
              value={range.date_to}
              onChange={(e) => setRange((r) => ({ ...r, date_to: e.target.value }))}
            />
          </label>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading && !overview ? (
        <div className="py-8 text-center text-sm text-gray-500">
          {t('common.loading', 'Завантаження...')}
        </div>
      ) : overview ? (
        <>
          {/* Картки зведення */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SummaryCard
              label={t('financeOverview.totalPaid', 'Отримано (оплачено)')}
              value={formatAmount(overview.total)}
            />
            <SummaryCard
              label={t('financeOverview.totalOwed', 'Заборгованість')}
              value={formatAmount(overview.owed_total)}
              tone="warning"
            />
          </div>

          {/* Графік динаміки по місяцях */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <h2 className="mb-4 text-sm font-medium text-gray-700">
              {t('financeOverview.monthlyDynamics', 'Динаміка по місяцях')}
            </h2>
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={overview.by_period}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip
                    formatter={(value: any) => [formatAmount(Number(value || 0)), '']}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="total"
                    name={t('payments.statuses.paid', 'Оплачено')}
                    stroke="#2563eb"
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="owed"
                    name={t('payments.statuses.owed', 'Заборговано')}
                    stroke="#d97706"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Таблиця розбивки по типах */}
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">
                    {t('payments.fields.type', 'Тип')}
                  </th>
                  <th className="px-4 py-2 text-right font-medium text-gray-600">
                    {t('payments.statuses.paid', 'Оплачено')}
                  </th>
                  <th className="px-4 py-2 text-right font-medium text-gray-600">
                    {t('payments.statuses.owed', 'Заборговано')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {overview.breakdown.map((row) => (
                  <tr key={row.type}>
                    <td className="px-4 py-2 text-gray-800">
                      {t(`payments.types.${row.type}`, row.type_display)}
                    </td>
                    <td className="px-4 py-2 text-right font-medium text-gray-800">
                      {formatAmount(row.total)}
                    </td>
                    <td className="px-4 py-2 text-right font-medium text-amber-700">
                      {formatAmount(row.owed)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}