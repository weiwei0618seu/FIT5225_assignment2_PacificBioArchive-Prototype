import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AppRoutes } from "./App";
import { configureAuth } from "./auth/authClient";
import { readPublicConfig } from "./config";
import "./styles.css";

configureAuth(readPublicConfig(import.meta.env));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <AppRoutes />
    </BrowserRouter>
  </StrictMode>,
);
