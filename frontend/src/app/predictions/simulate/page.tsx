import { PredictionSimulationForm } from "@/components/predictions/PredictionSimulationForm";
import { StatusMessage } from "@/components/StatusMessage";
import { ApiError, getFootballTeams } from "@/lib/api";

export default async function PredictionSimulationPage() {
  try {
    const response = await getFootballTeams();
    const teams = response.teams.sort((left, right) =>
      left.name.localeCompare(right.name, "pl"),
    );

    return (
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold text-white">
            Symulacja predykcji
          </h1>
          <p className="text-sm text-slate-400">
            Wybierz gospodarza i gościa, aby sprawdzić prognozę modeli dla
            przyszłego meczu piłkarskiego.
          </p>
        </header>

        {teams.length >= 2 ? (
          <PredictionSimulationForm teams={teams} />
        ) : (
          <StatusMessage
            title="Brak drużyn"
            message="Do symulacji potrzebne są co najmniej dwie drużyny piłkarskie."
            variant="empty"
          />
        )}
      </main>
    );
  } catch (error) {
    return (
      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <header>
          <h1 className="text-3xl font-bold text-white">
            Symulacja predykcji
          </h1>
        </header>
        <StatusMessage
          title="Nie udało się pobrać drużyn"
          message={
            error instanceof ApiError
              ? error.message
              : "Spróbuj ponownie za chwilę."
          }
          variant="error"
        />
      </main>
    );
  }
}
