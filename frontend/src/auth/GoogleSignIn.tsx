import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { usePublicConfig } from "../api/hooks";
import { useAuth } from "./AuthProvider";

const SCRIPT_SRC = "https://accounts.google.com/gsi/client";
let scriptPromise: Promise<void> | null = null;

function loadGoogleScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Couldn't load Google sign-in."));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

export function GoogleSignIn() {
  const { data: config } = usePublicConfig();
  const { signIn } = useAuth();
  const slot = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const clientId = config?.google_client_id;

  useEffect(() => {
    if (!clientId || !slot.current) return;
    let cancelled = false;
    loadGoogleScript()
      .then(() => {
        if (cancelled || !slot.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async ({ credential }) => {
            setError(null);
            try {
              await signIn(credential);
            } catch (e) {
              setError(e instanceof ApiError ? e.message : "Sign-in failed. Please try again.");
            }
          },
        });
        window.google.accounts.id.renderButton(slot.current, {
          theme: "filled_black",
          size: "large",
          shape: "rectangular",
          text: "signin_with",
          width: 280,
        });
      })
      .catch((e: Error) => setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [clientId, signIn]);

  if (config && !clientId) {
    return <p className="form-error">Google sign-in isn't configured yet (auth.google.client_id in config.yaml).</p>;
  }
  return (
    <div className="signin">
      <div ref={slot} className="google-slot" />
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}
