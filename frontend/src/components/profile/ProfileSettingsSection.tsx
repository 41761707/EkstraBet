import { ThemeToggle } from "@/components/preferences/ThemeToggle";
import { ProfileSection } from "@/components/profile/ProfileSection";

export const PROFILE_SETTINGS_TITLE = "Ustawienia";
export const PROFILE_SETTINGS_DESCRIPTION =
  "Wygląd aplikacji i sposób wyświetlania danych.";
export const COLOR_SCHEME_LABEL = "Schemat kolorów";
export const COLOR_SCHEME_DESCRIPTION =
  "Wybierz jasny lub ciemny motyw interfejsu.";

/**
 * Profile card for scalar account preferences. v1 exposes only color scheme;
 * later settings (e.g. odds format) belong here as extra rows, not a new page.
 */
export function ProfileSettingsSection() {
  return (
    <ProfileSection
      title={PROFILE_SETTINGS_TITLE}
      description={PROFILE_SETTINGS_DESCRIPTION}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium text-slate-200">
            {COLOR_SCHEME_LABEL}
          </p>
          <p className="text-sm text-slate-400">{COLOR_SCHEME_DESCRIPTION}</p>
        </div>
        <ThemeToggle />
      </div>
    </ProfileSection>
  );
}
