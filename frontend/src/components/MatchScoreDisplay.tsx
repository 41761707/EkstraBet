import { resolveMatchScore, type MatchScoreInput } from "@/lib/matchScore";

type MatchScoreSize = "sm" | "md" | "lg";

interface MatchScoreDisplayProps {
  match: MatchScoreInput;
  size?: MatchScoreSize;
  className?: string;
}

const sizeStyles: Record<
  MatchScoreSize,
  { main: string; note: string; wrapper: string }
> = {
  sm: {
    main: "font-semibold text-sky-200",
    note: "text-[0.7rem] font-normal leading-tight text-sky-300/75",
    wrapper: "inline-flex items-baseline gap-1",
  },
  md: {
    main: "text-lg font-semibold text-sky-200",
    note: "text-xs font-normal leading-tight text-sky-300/75",
    wrapper: "inline-flex items-baseline gap-1",
  },
  lg: {
    main: "text-2xl font-bold text-sky-200 sm:text-3xl",
    note: "text-xs font-medium leading-tight text-sky-300/80 sm:text-sm",
    wrapper: "inline-flex flex-col items-center gap-0.5",
  },
};

export function MatchScoreDisplay({
  match,
  size = "md",
  className = "",
}: MatchScoreDisplayProps) {
  const { main, note } = resolveMatchScore(match);
  const styles = sizeStyles[size];

  return (
    <span className={`${styles.wrapper} ${className}`.trim()}>
      <span className={styles.main}>{main}</span>
      {note ? <span className={styles.note}>{note}</span> : null}
    </span>
  );
}
