import { ModelDocumentationCard } from "@/components/models/ModelDocumentationCard";
import type { DocumentedModelView } from "@/lib/modelDocumentation";

interface ModelsCatalogProps {
  models: DocumentedModelView[];
}

function CatalogGroup({
  id,
  title,
  description,
  models,
}: {
  id: string;
  title: string;
  description: string;
  models: DocumentedModelView[];
}) {
  if (models.length === 0) {
    return null;
  }

  const headingId = `${id}-heading`;

  return (
    <section className="space-y-4" aria-labelledby={headingId}>
      <div className="space-y-1">
        <h2
          id={headingId}
          className="text-xl font-semibold text-white sm:text-2xl"
        >
          {title}
        </h2>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <div className="space-y-3">
        {models.map((model, index) => (
          <ModelDocumentationCard
            key={model.name}
            model={model}
            defaultOpen={index === 0}
          />
        ))}
      </div>
    </section>
  );
}

export function ModelsCatalog({ models }: ModelsCatalogProps) {
  const preMatch = models.filter((model) => model.phase === "pre_match");
  const postMatch = models.filter((model) => model.phase === "post_match");

  return (
    <div className="space-y-10">
      <CatalogGroup
        id="models-pre-match"
        title="Modele przedmeczowe"
        description="Predykcje powstają przed rozpoczęciem spotkania na podstawie historii, ratingów i kontekstu ligi."
        models={preMatch}
      />
      <CatalogGroup
        id="models-post-match"
        title="Ocena po meczu"
        description="Modele oceniają jakość gry na podstawie statystyk pomeczowych — niezależnie od samego rezultatu bramkowego."
        models={postMatch}
      />
    </div>
  );
}
