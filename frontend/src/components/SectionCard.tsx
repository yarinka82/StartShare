import { Box, Paper, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

export default function SectionCard({ title, hint, icon, tone = "default", children }: {
  title: string; hint?: string; icon?: ReactNode; tone?: "default" | "danger"; children: ReactNode;
}) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: { xs: 2, sm: 3 }, borderRadius: 3,
        border: "1px solid", borderColor: tone === "danger" ? "error.light" : "divider",
        boxShadow: "0 1px 2px rgba(16,24,40,0.04), 0 4px 12px rgba(16,24,40,0.04)",
      }}
    >
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "flex-start", mb: 2.5 }}>
        {icon && (
          <Box sx={{ display: "grid", placeItems: "center", width: 36, height: 36, borderRadius: 2, bgcolor: "action.hover", color: "primary.main", flexShrink: 0 }}>
            {icon}
          </Box>
        )}
        <Box>
          <Typography variant="h6" component="h2" sx={{ lineHeight: 1.3 }}>{title}</Typography>
          {hint && <Typography variant="body2" color="text.secondary">{hint}</Typography>}
        </Box>
      </Stack>
      {children}
    </Paper>
  );
}
