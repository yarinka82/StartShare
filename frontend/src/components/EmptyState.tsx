import { Box, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

export default function EmptyState({ icon, title, text, action }: {
  icon: ReactNode; title: string; text?: string; action?: ReactNode;
}) {
  return (
    <Stack
      spacing={1.5}
      sx={{
        alignItems: "center", textAlign: "center", py: { xs: 5, sm: 7 }, px: 2,
        border: "1px dashed", borderColor: "divider", borderRadius: 3, bgcolor: "background.paper",
      }}
    >
      <Box sx={{ display: "grid", placeItems: "center", width: 56, height: 56, borderRadius: "50%", bgcolor: "action.hover", color: "text.secondary" }}>
        {icon}
      </Box>
      <Typography variant="h6" component="h2">{title}</Typography>
      {text && <Typography color="text.secondary" sx={{ maxWidth: 420 }}>{text}</Typography>}
      {action}
    </Stack>
  );
}