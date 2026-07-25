import type { Metadata } from "next";

import { ModelsCatalog } from "@/components/models/ModelsCatalog";
import { PredictionOutcomeExample } from "@/components/models/PredictionOutcomeExample";
import { StatusMessage } from "@/components/StatusMessage";
import { getModelDetails, getModels } from "@/lib/api";
import {
  MODEL_DOCUMENTATION,
  toDocumentedModelView,
  type DocumentedModelView,
} from "@/lib/modelDocumentation";
import type { ModelDetailsResponse, ModelSummary } from "@/types/api";

export const metadata: Metadata = {
  title: "O modelach | EkstraBet",
  description:
    "Opis modeli predykcyjnych EkstraBet: dane wejściowe, algorytmy, " +
    "interpretacja wyników, ograniczenia oraz interaktywny przykład rozliczenia.",
};

function detailsFromSummary(summary: ModelSummary): ModelDetailsResponse {
  return {
    id: summary.id,
    name: summary.name,
    active: summary.active,
    sport_id: summary.sport_id,
    sport_name: summary.sport_name,
    event_families: [],
    supported_events: [],
    total_events: 0,
  };
}

async function loadDocumentedModels(): Promise<{
  models: DocumentedModelView[];
  apiUnavailable: boolean;
}> {
  let summaries: ModelSummary[] = [];
  try {
    const response = await getModels();
    summaries = response.models;
  } catch {
    return {
      models: MODEL_DOCUMENTATION.map((documentation) =>
        toDocumentedModelView(documentation, null),
      ),
      apiUnavailable: true,
    };
  }

  const summaryByName = new Map(
    summaries.map((summary) => [summary.name, summary]),
  );
  const matchedSummaries = MODEL_DOCUMENTATION.map((documentation) =>
    summaryByName.get(documentation.name),
  ).filter((summary): summary is ModelSummary => summary !== undefined);

  const settledDetails = await Promise.allSettled(
    matchedSummaries.map((summary) => getModelDetails(summary.id)),
  );

  const detailsByName = new Map<string, ModelDetailsResponse>();
  matchedSummaries.forEach((summary, index) => {
    const result = settledDetails[index];
    if (result?.status === "fulfilled") {
      detailsByName.set(summary.name, result.value);
    }
  });

  const models = MODEL_DOCUMENTATION.map((documentation) => {
    const summary = summaryByName.get(documentation.name);
    if (!summary) {
      return {
        ...toDocumentedModelView(documentation, null),
        availabilityNote: "Model niedostępny w API",
      };
    }

    const details =
      detailsByName.get(documentation.name) ?? detailsFromSummary(summary);
    return toDocumentedModelView(documentation, details);
  });

  return { models, apiUnavailable: false };
}

export default async function AboutModelsPage() {
  const { models, apiUnavailable } = await loadDocumentedModels();

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <h1 className="text-3xl font-bold text-white">O modelach</h1>
        <p className="max-w-3xl text-sm leading-relaxed text-slate-300 sm:text-base">
          Poniżej znajdziesz opis pięciu aktualnych modeli: jak powstają cechy,
          jak działa inferencja, co oznaczają wyjścia i jakie są ograniczenia.
          Informacje o dostępności modeli pochodzą z API, treść algorytmów jest
          wersjonowaną dokumentacją.
        </p>
      </header>

      {apiUnavailable ? (
        <StatusMessage
          variant="info"
          title="Status dostępności nie został pobrany"
          message="Dokumentacja modeli jest nadal dostępna poniżej. Spróbuj odświeżyć stronę później, aby zobaczyć aktualny status w API."
        />
      ) : null}

      <ModelsCatalog models={models} />
      <PredictionOutcomeExample />
    </div>
  );
}
