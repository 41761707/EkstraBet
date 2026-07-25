import type { ReactNode } from "react";

import { ExpandableSection } from "@/components/ExpandableSection";
import { MathText } from "@/components/models/MathText";
import { formatProbability } from "@/lib/format";
import type { DocumentedModelView } from "@/lib/modelDocumentation";

interface ModelDocumentationCardProps {
  model: DocumentedModelView;
  defaultOpen?: boolean;
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
      {items.map((item) => (
        <MathText key={item} as="li" text={item} className="leading-relaxed" />
      ))}
    </ul>
  );
}

function SectionHeading({ children }: { children: string }) {
  return (
    <h4 className="mb-2 text-sm font-semibold uppercase tracking-wide text-sky-300/90">
      {children}
    </h4>
  );
}

function ContentBlock({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <SectionHeading>{title}</SectionHeading>
      {children}
    </div>
  );
}

function formatMetricValue(key: string, value: number | null): string {
  if (value === null) {
    return "niedostępna";
  }
  // tylko accuracy prezentujemy jako procent; MAE / log-loss / NLL to skale liczbowe
  if (key === "accuracy") {
    return formatProbability(value);
  }
  return value.toFixed(3);
}

function MetricsBlock({ model }: { model: DocumentedModelView }) {
  return (
    <ContentBlock title="Metryki walidacyjne">
      <ul className="space-y-3 text-sm text-slate-300">
        {model.metrics.map((metric) => (
          <li
            key={`${model.name}-${metric.key}`}
            className="rounded-lg border border-slate-700/60 bg-slate-950/40 px-3 py-2"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-medium text-slate-100">{metric.label}</span>
              <span className="font-mono text-sky-200">
                {formatMetricValue(metric.key, metric.value)}
              </span>
            </div>
            {metric.artifactVersion ? (
              <p className="mt-1 text-xs text-slate-500">
                Artefakt v{metric.artifactVersion}
              </p>
            ) : null}
            <p className="mt-1 text-xs text-slate-400">{metric.note}</p>
          </li>
        ))}
      </ul>
    </ContentBlock>
  );
}

function AvailabilityBadge({ model }: { model: DocumentedModelView }) {
  if (!model.availabilityNote) {
    return (
      <span className="rounded-full border border-emerald-500/40 bg-emerald-950/40 px-2.5 py-0.5 text-xs font-medium text-emerald-200">
        Dostępny
      </span>
    );
  }

  return (
    <span className="rounded-full border border-amber-500/40 bg-amber-950/30 px-2.5 py-0.5 text-xs font-medium text-amber-100">
      {model.availabilityNote}
    </span>
  );
}

function PhaseBadge({ phase }: { phase: DocumentedModelView["phase"] }) {
  const label = phase === "pre_match" ? "Przed meczem" : "Po meczu";
  return (
    <span className="rounded-full border border-slate-600 bg-slate-800/80 px-2.5 py-0.5 text-xs text-slate-300">
      {label}
    </span>
  );
}

export function ModelDocumentationCard({
  model,
  defaultOpen = false,
}: ModelDocumentationCardProps) {
  const title = `${model.displayName} · v${model.version}`;

  return (
    <ExpandableSection title={title} defaultOpen={defaultOpen} id={model.name}>
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <PhaseBadge phase={model.phase} />
          <AvailabilityBadge model={model} />
          <span className="font-mono text-xs text-slate-500">{model.name}</span>
        </div>

        <ContentBlock title="Przeznaczenie">
          <MathText
            text={model.purpose}
            className="text-sm leading-relaxed text-slate-300"
          />
        </ContentBlock>

        <ContentBlock title="Algorytm">
          <MathText
            text={model.algorithm}
            className="text-sm leading-relaxed text-slate-300"
          />
        </ContentBlock>

        <ContentBlock title="Wejścia">
          <BulletList items={model.inputs} />
        </ContentBlock>

        <ContentBlock title="Przygotowanie cech">
          <BulletList items={model.featureEngineering} />
        </ContentBlock>

        <ContentBlock title="Etapy predykcji">
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-300">
            {model.predictionSteps.map((step) => (
              <MathText
                key={step}
                as="li"
                text={step}
                className="leading-relaxed"
              />
            ))}
          </ol>
        </ContentBlock>

        <ContentBlock title="Wyjścia i interpretacja">
          <BulletList items={model.outputs} />
        </ContentBlock>

        <MetricsBlock model={model} />

        <ContentBlock title="Ograniczenia">
          <BulletList items={model.limitations} />
        </ContentBlock>
      </div>
    </ExpandableSection>
  );
}
