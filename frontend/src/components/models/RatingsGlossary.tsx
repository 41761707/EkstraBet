import { ExpandableSection } from "@/components/ExpandableSection";
import { MathText } from "@/components/models/MathText";
import { MODEL_CONCEPT_GLOSSARY } from "@/lib/modelDocumentation";

/** Glossary of LSTM + rating systems used by pre-match models. */
export function RatingsGlossary() {
  return (
    <section className="space-y-4" aria-labelledby="concepts-glossary-heading">
      <div className="space-y-1">
        <h2
          id="concepts-glossary-heading"
          className="text-xl font-semibold text-white sm:text-2xl"
        >
          Pojęcia kluczowe
        </h2>
        <p className="text-sm text-slate-400">
          Zanim przejdziesz do kart modeli: czym są LSTM, logity i Softmax
          oraz ratingi Elo, GAP i Czech, z których korzystają modele
          przedmeczowe.
        </p>
      </div>

      <div className="space-y-3">
        {MODEL_CONCEPT_GLOSSARY.map((entry, index) => (
          <ExpandableSection
            key={entry.id}
            title={entry.title}
            defaultOpen={index === 0}
            id={`concept-${entry.id}`}
          >
            <div className="space-y-3">
              <MathText
                text={entry.summary}
                className="text-sm leading-relaxed text-slate-300"
              />
              <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-300">
                {entry.details.map((detail) => (
                  <MathText
                    key={detail}
                    as="li"
                    text={detail}
                    className="leading-relaxed"
                  />
                ))}
              </ul>
            </div>
          </ExpandableSection>
        ))}
      </div>
    </section>
  );
}
