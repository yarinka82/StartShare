

import { useState, useEffect, useCallback } from 'react';
import { membersApi } from '../api/members';
import { Member, MemberFilters, MemberFormData } from '../types/members';
import { toast } from '../components/Notifier';

export const useMembers = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<MemberFilters>({});
  const [total, setTotal] = useState(0);

  const fetchMembers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await membersApi.getMembers(filters);
      // Исправлено: используем response.results, а не response напрямую
      setMembers(response.results || []);
      setTotal(response.count || 0);
    } catch (error) {
      console.error('Error fetching members:', error);
      toast('Помилка завантаження списку членів', 'error');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  const createMember = async (data: MemberFormData) => {
    try {
      const newMember = await membersApi.createMember(data);
      setMembers(prev => [...prev, newMember]);
      toast('Члена успішно додано!', 'success');
      return newMember;
    } catch (error: any) {
      const message = error.response?.data?.error || 'Помилка додавання члена';
      toast(message, 'error');
      throw error;
    }
  };

  const updateMember = async (id: number, data: Partial<MemberFormData>) => {
    try {
      const updated = await membersApi.updateMember(id, data);
      setMembers(prev => prev.map(m => m.id === id ? updated : m));
      toast('Дані члена оновлено!', 'success');
      return updated;
    } catch (error: any) {
      const message = error.response?.data?.error || 'Помилка оновлення члена';
      toast(message, 'error');
      throw error;
    }
  };

  const deleteMember = async (id: number) => {
    if (!window.confirm('Ви впевнені, що хочете видалити цього члена?')) return;

    try {
      await membersApi.deleteMember(id);
      setMembers(prev => prev.filter(m => m.id !== id));
      toast('Члена видалено', 'success');
    } catch (error: any) {
      const message = error.response?.data?.error || 'Помилка видалення члена';
      toast(message, 'error');
      throw error;
    }
  };

  return {
    members,
    loading,
    filters,
    setFilters,
    total,
    fetchMembers,
    createMember,
    updateMember,
    deleteMember,
  };
};

export default useMembers;