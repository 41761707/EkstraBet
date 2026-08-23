import type { ReactNode } from "react";

interface ProfilePageProps {
  username: string;
  displayName: string;
  children?: ReactNode;
}

export function ProfilePage({
  username,
  displayName,
  children,
}: ProfilePageProps) {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold text-text">{displayName}</h1>
        <p className="text-sm text-muted">@{username}</p>
      </header>
      {children ? <div className="space-y-4">{children}</div> : null}
    </div>
  );
}
