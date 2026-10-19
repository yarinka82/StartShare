import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    // brand blue: the same value the pages used to hard-code as "#17407a" / "#0b2142"
    primary: { main: "#17407a", dark: "#0b2142" },
    background: { default: "#f5f7fa" },
  },
  shape: { borderRadius: 10 },
  typography: { fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif' },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { textTransform: "none", fontWeight: 600 } },
    },
    MuiTextField: { defaultProps: { fullWidth: true, size: "medium" } },
  },
});
