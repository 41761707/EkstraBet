import { HomeSection } from "@/components/home/HomeSection";
import { APP_RELEASE, getAppReleaseTitle } from "@/lib/appRelease";

interface ReleaseMetaLineProps {
  label: string;
  value: string;
}

function ReleaseMetaLine({ label, value }: ReleaseMetaLineProps) {
  return (
    <p className="text-sm leading-relaxed text-muted">
      <span className="font-medium text-text">{label}</span> {value}
    </p>
  );
}

export function HomeReleaseNotes() {
  return (
    <HomeSection title={getAppReleaseTitle()}>
      <div className="space-y-4">
        <h3 className="border-b border-accent/40 pb-2 text-lg font-semibold text-accent-text">
          {APP_RELEASE.heading}
        </h3>
        <ReleaseMetaLine
          label="Data wydania:"
          value={APP_RELEASE.releaseDate}
        />
        <ReleaseMetaLine
          label="Charakter wydania:"
          value={APP_RELEASE.character}
        />
        <h4 className="text-sm font-semibold text-text">Wprowadzone zmiany</h4>
        <ul className="list-disc space-y-1 pl-5 text-sm leading-relaxed text-muted">
          {APP_RELEASE.changes.map((change) => (
            <li key={change}>{change}</li>
          ))}
        </ul>
      </div>
    </HomeSection>
  );
}
