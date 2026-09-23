
import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Box, Typography, TextField, Button, Alert, IconButton, InputAdornment } from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import {tokens} from "@/pages/Members/components/theme.ts";
import {useAuth} from "@/hooks";
import LanguageSwitcher from "@/components/LanguageSwitcher.tsx";



// Original geometric illustration — a wax-seal + open ledger motif,
// echoing the "founders signed the statute" theme of the app, not any
// existing artwork or brand mark.
const RegistrySeal: React.FC = () => (
  <svg viewBox="0 0 420 420" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
    <circle cx="210" cy="180" r="150" fill="none" stroke={tokens.sealGold} strokeWidth="1.5" opacity="0.35" />
    <circle cx="210" cy="180" r="118" fill={tokens.registryDark} />
    <circle cx="210" cy="180" r="118" fill="none" stroke={tokens.sealGold} strokeWidth="2" />
    <circle cx="210" cy="180" r="100" fill="none" stroke={tokens.sealGold} strokeWidth="1" opacity="0.5" />
    <text
      x="210"
      y="205"
      textAnchor="middle"
      fontFamily="'Fraunces', serif"
      fontWeight="600"
      fontSize="96"
      fill={tokens.paperElevated}
    >
      V
    </text>
    {/* ribbon */}
    <path d="M170 288 L170 360 L210 335 L250 360 L250 288 Z" fill={tokens.sealGold} opacity="0.9" />
    {/* ledger lines beneath */}
    <g stroke={tokens.paperElevated} strokeWidth="2" opacity="0.25">
      <line x1="70" y1="380" x2="350" y2="380" />
      <line x1="90" y1="392" x2="330" y2="392" />
    </g>
  </svg>
);

const Login: React.FC = () => {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: Location })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : t('login.errorGeneric'));
    } finally {
      setSubmitting(false);
    }
  };

  return (

    <Box sx={{ display: 'flex', minHeight: '100vh', position: 'relative', flexDirection: 'column' }}>
      {/* Прапорна смужка */}
      <Box sx={{ display: 'flex', height: 6, flexShrink: 0 }}>
        <Box sx={{ flex: 1, bgcolor: tokens.registry }} />
        <Box sx={{ flex: 1, bgcolor: tokens.sealGold }} />
      </Box>

      <Box sx={{ display: 'flex', flex: 1 }}>
        {/* Переключатель языка */}
        <Box sx={{ position: 'absolute', top: 22, right: 16, zIndex: 1 }}>
          <LanguageSwitcher />
        </Box>


      {/* Left — illustration panel, hidden on narrow screens */}
      <Box
        sx={{
          display: { xs: 'none', md: 'flex' },
          flex: 1,
          bgcolor: tokens.ink,
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          p: 6,
        }}
      >
        <Box sx={{ width: '100%', maxWidth: 380 }}>
          <RegistrySeal />
        </Box>
        <Typography
          variant="h5"
          sx={{ color: tokens.paperElevated, mt: 2, textAlign: 'center' }}
        >
          {t('login.brandTitle')}
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: tokens.muted, mt: 1, textAlign: 'center', maxWidth: 320 }}
        >
          {t('login.brandSubtitle')}
        </Typography>
      </Box>

      {/* Right — login form */}
      <Box
        sx={{
          flex: 1,
          bgcolor: tokens.paper,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          px: 4,
        }}
      >
        <Box sx={{ width: '100%', maxWidth: 360 }}>
          <Typography variant="h4" sx={{ color: tokens.ink, mb: 0.5 }}>
            {t('login.title')}
          </Typography>
          <Typography variant="body2" sx={{ color: tokens.muted, mb: 4 }}>
            {t('login.subtitle')}
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label={t('login.usernameLabel')}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              margin="normal"
              autoFocus
              sx={{ bgcolor: tokens.paperElevated }}
            />
            <TextField
              fullWidth
              type={showPassword ? 'text' : 'password'}
              label={t('login.passwordLabel')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              sx={{ bgcolor: tokens.paperElevated }}
              slotProps={{
                input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label={showPassword ? t('login.hidePassword') : t('login.showPassword')}
                        onClick={() => setShowPassword((prev) => !prev)}
                        edge="end"
                        tabIndex={-1}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={submitting}
              sx={{
                mt: 3,
                py: 1.2,
                bgcolor: tokens.registry,
                '&:hover': { bgcolor: tokens.registryDark },
              }}
            >
              {submitting ? t('login.submitting') : t('login.submit')}
            </Button>
          </Box>
        </Box>
      </Box>
    </Box>
    </Box>
  );
};

export default Login;