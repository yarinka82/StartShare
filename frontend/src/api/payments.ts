import apiClient, { apiFetch } from '@/api/client';
import type {
  Payment,
  PaymentFormData,
  PaymentListParams,
  FinancialOverview,
} from '@/types/payments';

const BASE_URL = '/api/payments/';
const OVERVIEW_URL = '/api/payments/financial-overview/';

function buildQuery(params?: Record<string, string | number | undefined>): string {
  if (!params) return '';
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      usp.set(key, String(value));
    }
  });
  const qs = usp.toString();
  return qs ? `?${qs}` : '';
}



export const paymentsApi = {
  // 1. Получение списка платежей (с безопасным приведением параметров для query)
  getPayments: async (params?: PaymentListParams): Promise<Payment[]> => {
    return apiClient.get(`${BASE_URL}${buildQuery(params as Record<string, any>)}`);
  },

  // 2. Получение одного платежа
  getPayment: async (id: number): Promise<Payment> => {
    return apiClient.get(`${BASE_URL}${id}/`);
  },

  // 3. Создание платежа
  createPayment: async (payload: PaymentFormData): Promise<Payment> => {
    return apiClient.post(BASE_URL, payload);
  },

  // 4. Полное обновление (PUT) через apiFetch с заголовком application/json
  updatePayment: async (id: number, payload: PaymentFormData): Promise<Payment> => {
    const response = await apiFetch(`${BASE_URL}${id}/`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Failed to update payment: ${response.statusText}`);
    }

    return response.json();
  },

  // 5. Частичное обновление (PATCH)
  patchPayment: async (id: number, payload: Partial<PaymentFormData>): Promise<Payment> => {
    return apiClient.patch(`${BASE_URL}${id}/`, payload);
  },

  // 6. Удаление платежа
  deletePayment: async (id: number): Promise<void> => {
    await apiClient.delete(`${BASE_URL}${id}/`);
  },

  // 7. Финансовая сводка
  getFinancialOverview: async (params?: {
    date_from?: string;
    date_to?: string;
  }): Promise<FinancialOverview> => {
    return apiClient.get(`${OVERVIEW_URL}${buildQuery(params as Record<string, any>)}`);
  },
};

export default paymentsApi;