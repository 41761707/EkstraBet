import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";
import { LoadingSpinner } from "@/components/LoadingSpinner";

export default function LoginPage() {
  return (
    <Suspense fallback={<LoadingSpinner label="Ładowanie formularza…" />}>
      <LoginForm />
    </Suspense>
  );
}
