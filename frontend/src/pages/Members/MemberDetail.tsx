
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Box,
  Button,
  Paper,
  Typography,
  Grid,
  Chip,
  Divider,
  CircularProgress,
  Alert,
  Stack
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  Email as EmailIcon,
  Phone as PhoneIcon,
  LocationOn as LocationIcon,
  CalendarToday as CalendarIcon,
  Star as StarIcon,
  StarOutlined as StarOutlineIcon,
} from '@mui/icons-material';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/uk';
import membersApi from "@/api/members.ts";
import {Member} from "@/types/members.ts";
import MemberPaymentsHistory from "@/pages/Payments/MemberPaymentsHistory"

dayjs.extend(relativeTime);
dayjs.locale('uk');



const MemberDetail = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  const [member, setMember] = useState<Member | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      fetchMember(parseInt(id));
    }
  }, [id]);

  const fetchMember = async (memberId: number) => {
    try {
      const data = await membersApi.getMember(memberId);
      setMember(data);
    } catch (error) {
      console.error('Error fetching member:', error);
      setError('Помилка завантаження даних члена');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    return status === 'active' ? 'success' : 'error';
  };

  
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !member) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Члена не знайдено'}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Заголовок */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/members')}
          >
            {t('common.back')}
          </Button>
          <Typography variant="h4" component="h1">
            {member.first_name} {member.last_name}
          </Typography>
          {member.is_founder && (
            <Chip
              icon={<StarIcon />}
              label={t('members.founder')}
              color="warning"
              size="medium"
            />
          )}
        </Box>
        <Button
          variant="contained"
          startIcon={<EditIcon />}
          onClick={() => navigate(`/members/${member.id}/edit`)}
        >
          {t('common.edit')}
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Основная информация */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              {t('members.personalInfo')}
            </Typography>
            <Divider sx={{ mb: 3 }} />

            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.fullName')}
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                  {member.first_name} {member.last_name}
                </Typography>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.status')}
                </Typography>
                <Chip
                  label={member.status === 'active' ? t('members.statusActive') : t('members.statusInactive')}
                  color={getStatusColor(member.status)}
                  size="small"
                  sx={{ mt: 0.5 }}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.email')}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <EmailIcon fontSize="small" color="action" />
                  <Typography variant="body1">{member.email}</Typography>
                </Box>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.phone')}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <PhoneIcon fontSize="small" color="action" />
                  <Typography variant="body1">{member.phone || '—'}</Typography>
                </Box>
              </Grid>

              <Grid size={{ xs: 12 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.address')}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <LocationIcon fontSize="small" color="action" />
                  <Typography variant="body1">{member.address || '—'}</Typography>
                </Box>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.birthDate')}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CalendarIcon fontSize="small" color="action" />
                  <Typography variant="body1">
                    {member.birth_date ? dayjs(member.birth_date).format('DD.MM.YYYY') : '—'}
                  </Typography>
                </Box>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {t('members.joinedDate')}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CalendarIcon fontSize="small" color="action" />
                  <Typography variant="body1">
                    {dayjs(member.join_date).format('DD.MM.YYYY')}
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {member.notes && (
              <>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                  {t('members.notes')}
                </Typography>
                <Typography variant="body1" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                  {member.notes}
                </Typography>
              </>
            )}
          </Paper>
        </Grid>

        {/* Информационные карточки */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Stack spacing={3}>
            {/* Статус засновника */}
            <Paper sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {member.is_founder ? (
                  <StarIcon sx={{ fontSize: 48, color: 'warning.main' }} />
                ) : (
                  <StarOutlineIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
                )}
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    {member.is_founder ? t('members.isFounder') : t('members.notFounder')}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {member.is_founder
                      ? t('members.founderDescription')
                      : t('members.notFounderDescription')}
                  </Typography>
                </Box>
              </Box>
            </Paper>

            {/* Дата регистрации */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="caption" color="text.secondary">
                {t('members.memberSince')}
              </Typography>
              <Typography variant="h6">
                {dayjs(member.join_date).format('DD MMMM YYYY')}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {dayjs(member.join_date).fromNow()}
              </Typography>
            </Paper>

            {/* Действия */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                {t('common.actions')}
              </Typography>
              <Stack spacing={1}>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<EditIcon />}
                  onClick={() => navigate(`/members/${member.id}/edit`)}
                >
                  {t('common.edit')}
                </Button>
                {/* другие действия */}
              </Stack>
            </Paper>
          </Stack>
        </Grid>

      </Grid>

      <MemberPaymentsHistory memberId={member.id} />

    </Box>
  );
};

export default MemberDetail;