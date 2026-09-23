
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { AuthProvider } from './context/AuthContext';
import { MainLayout } from './layouts';
import Notifier from '@/components/Notifier';
import { Home, Login, MemberList, MemberDetail, MemberForm, Settings, FinanceOverview, FinanceChartsPage, CashDeskPage } from './pages';

import ProtectedRoute from './ProtectedRoute';

function App() {
  return (
    <AuthProvider>
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <>
        <Notifier />
          <Routes>
            {/* Публичные маршруты */}
            <Route path="/login" element={<Login />} />

            {/* Защищенные маршруты */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <MainLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/home" replace />} />
              <Route path="home" element={<Home />} />
              <Route path="members" element={<MemberList />} />
              <Route path="members/add" element={<MemberForm />} />
              <Route path="members/:id" element={<MemberDetail />} />
              <Route path="members/:id/edit" element={<MemberForm />} />
              <Route path="cashdesk" element={<CashDeskPage />} />
              <Route path="finance" element={<FinanceOverview />} />
              <Route path="charts" element={<FinanceChartsPage />} />
              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </>
      </BrowserRouter>
    </LocalizationProvider>
    </AuthProvider>
  );
}

export default App;