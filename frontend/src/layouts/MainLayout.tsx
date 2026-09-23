
import React from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, Button } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import Sidebar from '../components/Sidebar';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { useAuth } from '../hooks/useAuth';

const MainLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: '#f5f5f5' }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top Bar */}
        <AppBar
          position="static"
          color="default"
          elevation={1}
          sx={{
            bgcolor: 'background.paper',
            borderBottom: '1px solid',
            borderColor: 'divider',
            flexShrink: 0,
          }}
        >
          <Toolbar sx={{ gap: 1 }}>
            <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
              CRM Verien
            </Typography>

            {/* Language Switcher */}
            <LanguageSwitcher />

            {/* User info + Logout */}
            {user && (
              <Button
                size="small"
                onClick={handleLogout}
                startIcon={<LogoutIcon fontSize="small" />}
                sx={{ color: 'text.secondary' }}
              >
                {user.username}
              </Button>
            )}
          </Toolbar>
        </AppBar>

        {/* Page Content */}
        <Box
          component="main"
          sx={{
            flex: 1,
            overflow: 'auto',
            p: 2,
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};

export default MainLayout;