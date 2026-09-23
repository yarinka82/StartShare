
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Alert,
  Divider,
  FormControlLabel,
  Checkbox,
  Switch,
  Select,
  MenuItem,
  IconButton,
  InputAdornment,
  Tooltip,
} from '@mui/material';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import {apiFetch} from "@/api/client.ts";
import {useAuth} from "@/hooks";
import { tokens } from "../Members/components/theme";

interface AppUser {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  is_active: boolean;
  date_joined: string;
}

// ---- Компонент для поля пароля з глазиком ----
const PasswordField: React.FC<{
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  size?: 'small' | 'medium';
  autoFocus?: boolean;
  required?: boolean;
  fullWidth?: boolean;
}> = ({ label, value, onChange, size = 'small', autoFocus = false, required = false, fullWidth = false }) => {
  const [showPassword, setShowPassword] = useState(false);

  const handleClickShowPassword = () => setShowPassword(!showPassword);

  return (
    <TextField
      type={showPassword ? 'text' : 'password'}
      label={label}
      value={value}
      onChange={onChange}
      size={size}
      autoFocus={autoFocus}
      required={required}
      fullWidth={fullWidth}
      slotProps={{
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label="toggle password visibility"
                onClick={handleClickShowPassword}
                edge="end"
                size="small"
              >
                {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
  );
};

const Preferences: React.FC = () => {
  const { t } = useTranslation();
  const { isStaff } = useAuth();

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', px: { xs: 2, md: 4 }, py: 4 }}>
      <Typography
        variant="overline"
        sx={{ color: tokens.muted, fontFamily: '"IBM Plex Mono", monospace', letterSpacing: '0.12em' }}
      >
        {t('settings.title')}
      </Typography>
      <Typography variant="h4" sx={{ color: tokens.ink, mb: 4 }}>
        {t('settings.subtitle')}
      </Typography>

      <ChangePasswordSection />

      {isStaff && (
        <>
          <Divider sx={{ my: 5, borderColor: tokens.divider }} />
          <UserManagementSection />
        </>
      )}
    </Box>
  );
};

// ---- Self-service password change ----
const ChangePasswordSection: React.FC = () => {
  const { t } = useTranslation();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError(t('settings.passwordMismatch'));
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiFetch('/api/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const message =
          data.old_password?.[0] ||
          data.new_password?.[0] ||
          data.detail ||
          t('settings.passwordChangeError');
        throw new Error(message);
      }
      setSuccess(true);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.passwordChangeError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper variant="outlined" sx={{ borderColor: tokens.divider, bgcolor: tokens.paperElevated, p: 3 }}>
      <Typography variant="h6" sx={{ color: tokens.ink, mb: 2 }}>
        {t('settings.changePassword')}
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{t('settings.passwordUpdated')}</Alert>}

      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 360 }}>
        <PasswordField
          label={t('settings.currentPassword')}
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
        />
        <PasswordField
          label={t('settings.newPassword')}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
        <PasswordField
          label={t('settings.confirmNewPassword')}
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
        <Button
          type="submit"
          variant="contained"
          disabled={submitting}
          sx={{ alignSelf: 'flex-start', bgcolor: tokens.registry, '&:hover': { bgcolor: tokens.registryDark } }}
        >
          {submitting ? t('common.saving') : t('common.save')}
        </Button>
      </Box>
    </Paper>
  );
};

// ---- User management (staff only) ----
const UserManagementSection: React.FC = () => {
  const { t } = useTranslation();
  const { userId } = useAuth();
  const [users, setUsers] = useState<AppUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<AppUser | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AppUser | null>(null);

  const loadUsers = () => {
    setLoading(true);
    setLoadError(null);
    apiFetch('/api/users/')
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok || !Array.isArray(data)) {
          throw new Error(t('settings.unexpectedResponse'));
        }
        setUsers(data);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : t('settings.loadUsersError')))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadUsers();
  }, []);

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ color: tokens.ink }}>
          {t('settings.systemUsers')}
        </Typography>
        <Button
          startIcon={<PersonAddIcon />}
          variant="outlined"
          size="small"
          onClick={() => setAddDialogOpen(true)}
        >
          {t('settings.addUser')}
        </Button>
      </Box>

      {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}

      <Paper variant="outlined" sx={{ borderColor: tokens.divider, bgcolor: tokens.paperElevated, overflow: 'hidden' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('settings.username')}</TableCell>
              <TableCell>{t('settings.email')}</TableCell>
              <TableCell>{t('settings.role')}</TableCell>
              <TableCell>{t('settings.status')}</TableCell>
              <TableCell align="right" />
            </TableRow>
          </TableHead>
          <TableBody>
            {!loading && users.map((u) => {
              const isSelf = u.id === userId;
              return (
                <TableRow key={u.id}>
                  <TableCell sx={{ fontWeight: 500 }}>
                    {u.username}
                    {isSelf && (
                      <Chip
                        label={t('settings.you')}
                        size="small"
                        sx={{ ml: 1, height: 18, fontSize: '0.7rem', bgcolor: tokens.divider, color: tokens.muted }}
                      />
                    )}
                  </TableCell>
                  <TableCell sx={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '0.85rem' }}>
                    {u.email || '—'}
                  </TableCell>
                  <TableCell>
                    {u.is_staff ? (
                      <Chip label={t('settings.admin')} size="small" sx={{ bgcolor: 'rgba(184,134,59,0.15)', color: tokens.sealGold }} />
                    ) : (
                      <Chip label={t('settings.user')} size="small" sx={{ bgcolor: 'rgba(154,165,160,0.15)', color: tokens.muted }} />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={u.is_active ? t('settings.active') : t('settings.inactive')}
                      size="small"
                      sx={{
                        bgcolor: u.is_active ? 'rgba(47,111,94,0.12)' : 'rgba(164,74,63,0.12)',
                        color: u.is_active ? tokens.registryDark : tokens.danger,
                      }}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title={t('settings.edit')}>
                      <IconButton size="small" sx={{ color: tokens.muted }} onClick={() => setEditTarget(u)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={isSelf ? t('settings.cannotDeleteSelf') : t('settings.delete')}>
                      <span>
                        <IconButton
                          size="small"
                          disabled={isSelf}
                          sx={{ color: tokens.muted, '&:hover': { color: tokens.danger } }}
                          onClick={() => setDeleteTarget(u)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Paper>

      <AddUserDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        onCreated={() => {
          setAddDialogOpen(false);
          loadUsers();
        }}
      />

      <EditUserDialog
        user={editTarget}
        isSelf={editTarget?.id === userId}
        onClose={() => setEditTarget(null)}
        onSaved={() => {
          setEditTarget(null);
          loadUsers();
        }}
      />

      <DeleteUserDialog
        user={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onDeleted={() => {
          setDeleteTarget(null);
          loadUsers();
        }}
      />
    </Box>
  );
};

// ---- Add user ----
const AddUserDialog: React.FC<{ open: boolean; onClose: () => void; onCreated: () => void }> = ({
  open,
  onClose,
  onCreated,
}) => {
  const { t } = useTranslation();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isStaffFlag, setIsStaffFlag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch('/api/users/', {
        method: 'POST',
        body: JSON.stringify({ username, email, password, is_staff: isStaffFlag }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const message =
          data.username?.[0] || data.password?.[0] || data.email?.[0] || data.detail || t('settings.createUserError');
        throw new Error(message);
      }
      setUsername('');
      setEmail('');
      setPassword('');
      setIsStaffFlag(false);
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.createUserError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Box component="form" onSubmit={handleSubmit}>
        <DialogTitle sx={{ color: tokens.ink, pb: 2 }}>{t('settings.newUser')}</DialogTitle>
        <Divider sx={{ borderColor: tokens.divider }} />
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 3 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            label={t('settings.username')}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
            fullWidth
          />
          <TextField
            label={t('settings.email')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
          />
          <PasswordField
            label={t('settings.password')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            fullWidth
          />
          <FormControlLabel
            control={<Checkbox checked={isStaffFlag} onChange={(e) => setIsStaffFlag(e.target.checked)} />}
            label={t('settings.adminLabel')}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={submitting}
            sx={{ bgcolor: tokens.registry, '&:hover': { bgcolor: tokens.registryDark } }}
          >
            {submitting ? t('common.creating') : t('common.create')}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
};

// ---- Edit user: role + active status ----
const EditUserDialog: React.FC<{
  user: AppUser | null;
  isSelf: boolean;
  onClose: () => void;
  onSaved: () => void;
}> = ({ user, isSelf, onClose, onSaved }) => {
  const { t } = useTranslation();
  const [role, setRole] = useState<'admin' | 'user'>('user');
  const [active, setActive] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      setRole(user.is_staff ? 'admin' : 'user');
      setActive(user.is_active);
      setError(null);
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch(`/api/users/${user.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_staff: role === 'admin', is_active: active }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const message = data.detail || data.non_field_errors?.[0] || t('settings.updateUserError');
        throw new Error(message);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.updateUserError'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={Boolean(user)} onClose={onClose} maxWidth="sm" fullWidth>
      <Box component="form" onSubmit={handleSubmit}>
        <DialogTitle sx={{ color: tokens.ink }}>
          {t('settings.editUser')} — {user?.username}
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          {isSelf && (
            <Alert severity="info">{t('settings.cannotEditSelfRole')}</Alert>
          )}

          <Select
            value={role}
            onChange={(e) => setRole(e.target.value as 'admin' | 'user')}
            fullWidth
            disabled={isSelf}
          >
            <MenuItem value="user">{t('settings.user')}</MenuItem>
            <MenuItem value="admin">{t('settings.admin')}</MenuItem>
          </Select>

          <FormControlLabel
            control={
              <Switch
                checked={active}
                onChange={(e) => setActive(e.target.checked)}
                disabled={isSelf}
              />
            }
            label={active ? t('settings.active') : t('settings.inactive')}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={submitting || isSelf}
            sx={{ bgcolor: tokens.registry, '&:hover': { bgcolor: tokens.registryDark } }}
          >
            {submitting ? t('common.saving') : t('common.save')}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
};

// ---- Delete user ----
const DeleteUserDialog: React.FC<{
  user: AppUser | null;
  onClose: () => void;
  onDeleted: () => void;
}> = ({ user, onClose, onDeleted }) => {
  const { t } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    console.log('handleDelete called, user =', user);
    if (!user) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/users/${user.id}/`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || t('settings.deleteUserError'));
      }
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('settings.deleteUserError'));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Dialog open={Boolean(user)} onClose={() => !deleting && onClose()}>
      <DialogTitle sx={{ color: tokens.ink }}>{t('settings.deleteUserTitle')}</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <DialogContentText>
          {user && t('settings.deleteUserConfirm', { username: user.username })}
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={deleting}>{t('common.cancel')}</Button>
        <Button onClick={handleDelete} color="error" variant="contained" disabled={deleting}>
          {deleting ? t('common.deleting') : t('common.delete')}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default Preferences;