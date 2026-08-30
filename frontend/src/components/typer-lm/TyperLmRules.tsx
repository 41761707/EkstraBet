import { ExpandableSection } from "@/components/ExpandableSection";
import {
  TYPER_LM_RULES_SECTIONS,
  TYPER_LM_RULES_TITLE,
} from "@/lib/typerLmRules";

export function TyperLmRules() {
  return (
    <ExpandableSection title={TYPER_LM_RULES_TITLE} defaultOpen={false}>
      <div className="space-y-4">
        {TYPER_LM_RULES_SECTIONS.map((section) => (
          <section key={section.heading} className="space-y-2">
            <h2 className="text-sm font-semibold text-text">
              {section.heading}
            </h2>
            <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted">
              {section.items.map((item) => (
                <li key={item} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </ExpandableSection>
  );
}
