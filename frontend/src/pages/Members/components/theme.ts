import { createTheme } from '@mui/material/styles';

// Verein Registry theme — ink/registry-blue/seal-gold palette
// Evokes an official association ledger with a Ukrainian civic accent,
// not a generic SaaS dashboard.

export const tokens = {
  ink: '#16233B',
  paper: '#EDEFEA',
  paperElevated: '#F7F8F5',
  registry: '#0057B7',
  registryDark: '#003D82',
  sealGold: '#FFC72C',
  muted: '#9AA5A0',
  divider: '#D8DCD4',
  danger: '#A44A3F',
};

const theme = createTheme({
  palette: {
    background: {
      default: tokens.paper,
      paper: tokens.paperElevated,
    },
    primary: {
      main: tokens.registry,
      dark: tokens.registryDark,
      contrastText: '#F7F8F5',
    },
    secondary: {
      main: tokens.sealGold,
      contrastText: '#16233B',
    },
    text: {
      primary: tokens.ink,
      secondary: tokens.muted,
    },
    divider: tokens.divider,
    error: {
      main: tokens.danger,
    },
  },
  typography: {
    fontFamily: '"Inter", "Helvetica Neue", sans-serif',
    h1: { fontFamily: '"Fraunces", serif', fontWeight: 600 },
    h2: { fontFamily: '"Fraunces", serif', fontWeight: 600 },
    h3: { fontFamily: '"Fraunces", serif', fontWeight: 600 },
    h4: { fontFamily: '"Fraunces", serif', fontWeight: 600, letterSpacing: '-0.01em' },
    h5: { fontFamily: '"Fraunces", serif', fontWeight: 600 },
    h6: { fontFamily: '"Fraunces", serif', fontWeight: 600 },
  },
  shape: {
    borderRadius: 6,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontFamily: '"IBM Plex Mono", monospace',
          fontSize: '0.72rem',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: tokens.muted,
          borderBottom: `2px solid ${tokens.ink}`,
        },
        body: {
          borderBottom: `1px solid ${tokens.divider}`,
        },
      },
    },
  },
});

export default theme;