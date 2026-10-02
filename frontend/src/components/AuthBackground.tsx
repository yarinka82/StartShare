import { Box } from "@mui/material";

/**
 * Full-screen background for signed-out screens.
 * The picture is a plain file (public/auth-bg.svg): replace it with any image to rebrand.
 */
export default function AuthBackground() {
  return (
    <Box
      aria-hidden
      sx={{
        position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
        bgcolor: "#0b2142",
        backgroundImage: "url(/auth-bg.svg)",
        backgroundSize: "cover", backgroundPosition: "center", backgroundRepeat: "no-repeat",
      }}
    />
  );
}
