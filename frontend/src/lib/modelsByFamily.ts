import type {
  FilterOption,
  ModelDetailsResponse,
  ModelListResponse,
  ModelSummary,
} from "@/types/api";

export interface ModelsByFamily {
  result: FilterOption[];
  ou: FilterOption[];
  btts: FilterOption[];
}

export interface ModelsByFamilyFetchers {
  getModels: () => Promise<ModelListResponse>;
  getModelDetails: (modelId: number) => Promise<ModelDetailsResponse>;
}

const FAMILY_RESULT = "REZULTAT";
const FAMILY_OU = "OU";
const FAMILY_BTTS = "BTTS";

function emptyModelsByFamily(): ModelsByFamily {
  return {
    result: [],
    ou: [],
    btts: [],
  };
}

function sortModelsByFamily(grouped: ModelsByFamily): ModelsByFamily {
  for (const key of Object.keys(grouped) as (keyof ModelsByFamily)[]) {
    grouped[key].sort((left, right) =>
      left.label.localeCompare(right.label, "pl"),
    );
  }
  return grouped;
}

function assignModelToFamilies(
  grouped: ModelsByFamily,
  details: ModelDetailsResponse,
): void {
  const option = { id: details.id, label: details.name };
  const familyNames = new Set(
    details.event_families.map((family) => family.name.toUpperCase()),
  );
  if (familyNames.has(FAMILY_RESULT)) {
    grouped.result.push(option);
  }
  if (familyNames.has(FAMILY_OU)) {
    grouped.ou.push(option);
  }
  if (familyNames.has(FAMILY_BTTS)) {
    grouped.btts.push(option);
  }
}

/** Groups active models of a sport into REZULTAT / OU / BTTS filter options. */
export function groupActiveModelsByFamily(
  models: ModelSummary[],
  detailsList: Array<ModelDetailsResponse | null>,
  sportId: number,
): ModelsByFamily {
  const detailsById = new Map<number, ModelDetailsResponse>();
  for (const details of detailsList) {
    if (details) {
      detailsById.set(details.id, details);
    }
  }

  const grouped = emptyModelsByFamily();
  for (const model of models) {
    if (model.active !== 1 || model.sport_id !== sportId) {
      continue;
    }
    const details = detailsById.get(model.id);
    if (!details) {
      continue;
    }
    assignModelToFamilies(grouped, details);
  }

  return sortModelsByFamily(grouped);
}

/** Loads models via injected fetchers, then groups them by event family. */
export async function loadModelsGroupedByFamily(
  sportId: number,
  fetchers: ModelsByFamilyFetchers,
): Promise<ModelsByFamily> {
  const { models } = await fetchers.getModels();
  const activeModels = models.filter(
    (model) => model.active === 1 && model.sport_id === sportId,
  );

  const detailsList = await Promise.all(
    activeModels.map(async (model) => {
      try {
        return await fetchers.getModelDetails(model.id);
      } catch {
        // jeden padnięty details nie może wywalić całego grupowania
        return null;
      }
    }),
  );

  return groupActiveModelsByFamily(models, detailsList, sportId);
}
