import { ThemeToggle } from "@/components/preferences/ThemeToggle";
import {
  TEAM_NAME_DISPLAY_DESCRIPTION,
  TEAM_NAME_DISPLAY_LABEL,
  TeamNameDisplayControl,
} from "@/components/preferences/TeamNameDisplayControl";
import { ProfileSection } from "@/components/profile/ProfileSection";

export const PROFILE_SETTINGS_TITLE = "Ustawienia";
export const PROFILE_SETTINGS_DESCRIPTION =
  "Wygląd aplikacji i sposób wyświetlania danych.";
export const COLOR_SCHEME_LABEL = "Schemat kolorów";
export const COLOR_SCHEME_DESCRIPTION =
  "Wybierz jasny lub ciemny motyw interfejsu.";

/**
 * Profile card for scalar account preferences. Each preference is one row:
 * color scheme and team-name display. Later settings (e.g. odds format)
 * belong here as extra rows, not a new page.
 */
export function ProfileSettingsSection() {
  return (
    <ProfileSection
      title={PROFILE_SETTINGS_TITLE}
      description={PROFILE_SETTINGS_DESCRIPTION}
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium text-text">
              {COLOR_SCHEME_LABEL}
            </p>
            <p className="text-sm text-muted">{COLOR_SCHEME_DESCRIPTION}</p>
          </div>
          <ThemeToggle />
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium text-text">
              {TEAM_NAME_DISPLAY_LABEL}
            </p>
            <p className="text-sm text-muted">
              {TEAM_NAME_DISPLAY_DESCRIPTION}
            </p>
          </div>
          <TeamNameDisplayControl />
        </div>
      </div>
    </ProfileSection>
  );
}
