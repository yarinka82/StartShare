
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';
import { Box, Typography, Button, Paper } from '@mui/material';
import GroupsIcon from '@mui/icons-material/Groups';
import {useAuth} from "@/hooks";
import {tokens} from "@/pages/Members/components/theme.ts";


const Home: React.FC = () => {
  const { t } = useTranslation();
  const { username } = useAuth();

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', px: { xs: 2, md: 4 }, py: 6 }}>
      <Paper
        variant="outlined"
        sx={{
          bgcolor: tokens.ink,
          borderColor: tokens.ink,
          borderRadius: 2,
          p: { xs: 4, md: 6 },
          textAlign: 'center',
          mb: 4,
        }}
      >
        <Box
          sx={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            bgcolor: tokens.registryDark,
            border: `2px solid ${tokens.sealGold}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mx: 'auto',
            mb: 3,
          }}
        >
          <Typography
            sx={{ fontFamily: '"Fraunces", serif', fontWeight: 600, fontSize: 32, color: tokens.paperElevated }}
          >
            V
          </Typography>
        </Box>
        <Typography variant="h4" sx={{ color: tokens.paperElevated, mb: 1 }}>
          {t('home.welcome')}{username ? `, ${username}` : ''}
        </Typography>
        <Typography variant="body1" sx={{ color: tokens.muted, maxWidth: 460, mx: 'auto' }}>
          {t('home.description')}
        </Typography>
      </Paper>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Paper
          variant="outlined"
          sx={{ borderColor: tokens.divider, bgcolor: tokens.paperElevated, p: 3, flex: 1, minWidth: 240 }}
        >
          <GroupsIcon sx={{ color: tokens.registry, fontSize: 32, mb: 1 }} />
          <Typography variant="h6" sx={{ color: tokens.ink, mb: 0.5 }}>
            {t('home.membersTitle')}
          </Typography>
          <Typography variant="body2" sx={{ color: tokens.muted, mb: 2 }}>
            {t('home.membersDescription')}
          </Typography>
          <Button component={RouterLink} to="/members" variant="outlined" size="small">
            {t('home.openRegistry')}
          </Button>
        </Paper>
      </Box>
    </Box>
  );
};

export default Home;