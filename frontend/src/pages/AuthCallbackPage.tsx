import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { LoadingScreen } from "../components/LoadingScreen";

export function AuthCallbackPage() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    void refresh().then(() => navigate("/", { replace: true }));
  }, [navigate, refresh]);

  return <LoadingScreen />;
}
