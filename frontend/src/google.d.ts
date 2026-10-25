// Minimal types for Google Identity Services (https://accounts.google.com/gsi/client).
interface GoogleCredentialResponse {
  credential: string;
}

interface GoogleIdentity {
  accounts: {
    id: {
      initialize(options: { client_id: string; callback: (response: GoogleCredentialResponse) => void }): void;
      renderButton(element: HTMLElement, options: Record<string, string | number>): void;
      disableAutoSelect(): void;
    };
  };
}

interface Window {
  google?: GoogleIdentity;
}
