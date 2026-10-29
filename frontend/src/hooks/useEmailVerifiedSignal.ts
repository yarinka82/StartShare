
import { useEffect, useRef } from "react";

/** Runs the callback when the e-mail was verified in another tab of this browser. */
export function useEmailVerifiedSignal(onVerified: () => void) {
  const cb = useRef(onVerified);
  cb.current = onVerified;

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const ch = new BroadcastChannel("auth");
    ch.onmessage = (e) => {
      console.log("[signal] got", e.data);
      if (e.data === "email_verified") cb.current();
    };
    return () => ch.close();
  }, []);
}