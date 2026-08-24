import { buildThemeBootstrapScript } from "@/lib/theme";

/**
 * Blocking inline script that sets `data-theme` before React hydrates.
 * Must stay a Server Component so it ships in the initial HTML.
 */
export function ThemeBootstrapScript() {
  return (
    <script
      dangerouslySetInnerHTML={{ __html: buildThemeBootstrapScript() }}
    />
  );
}
