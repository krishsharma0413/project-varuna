import "./styles/app.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";
import { AuthProvider } from "./auth/AuthProvider";
import { AdminLogs } from "./pages/AdminLogs";
import { AdminRecords } from "./pages/AdminRecords";
import { Layout } from "./components/Layout";
import { Check, JobPage } from "./pages/Check";
import { CreatorPage, Creators } from "./pages/Creators";
import { Home } from "./pages/Home";
import { Method, NotFound } from "./pages/Method";
import { Result } from "./pages/Result";
import { Transparency } from "./pages/Transparency";

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: false } },
});

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/r/:reelId", element: <Result /> },
      { path: "/creators", element: <Creators /> },
      { path: "/c/:handle", element: <CreatorPage /> },
      { path: "/check", element: <Check /> },
      { path: "/check/:jobId", element: <JobPage /> },
      { path: "/method", element: <Method /> },
      { path: "/transparency", element: <Transparency /> },
      { path: "/admin/logs", element: <AdminLogs /> },
      { path: "/admin/records", element: <AdminRecords /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
