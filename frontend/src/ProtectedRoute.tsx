
import React from 'react';
import { Navigate } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import {tokens} from "@/pages/Members/components/theme.ts";
import {useAuth} from "@/hooks";



const ProtectedRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { username, loading } = useAuth();

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress sx={{ color: tokens.registry }} />
      </Box>
    );
  }

  if (!username) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;