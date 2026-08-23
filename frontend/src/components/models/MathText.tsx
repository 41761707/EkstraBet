import katex from "katex";
import "katex/dist/katex.min.css";

interface MathTextProps {
  text: string;
  className?: string;
  as?: "p" | "span" | "li";
}

type Segment =
  | { type: "text"; value: string }
  | { type: "math"; value: string; display: boolean };

/** Split plain text into prose and `$...$` / `$$...$$` math segments. */
function splitMathSegments(source: string): Segment[] {
  const segments: Segment[] = [];
  const pattern = /\$\$([\s\S]+?)\$\$|\$([^$\n]+?)\$/g;
  let lastIndex = 0;

  for (const match of source.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      segments.push({ type: "text", value: source.slice(lastIndex, index) });
    }

    const displayBody = match[1];
    const inlineBody = match[2];
    if (displayBody !== undefined) {
      segments.push({ type: "math", value: displayBody, display: true });
    } else if (inlineBody !== undefined) {
      segments.push({ type: "math", value: inlineBody, display: false });
    }

    lastIndex = index + match[0].length;
  }

  if (lastIndex < source.length) {
    segments.push({ type: "text", value: source.slice(lastIndex) });
  }

  return segments.length > 0 ? segments : [{ type: "text", value: source }];
}

function renderKatex(tex: string, displayMode: boolean): string {
  return katex.renderToString(tex, {
    throwOnError: false,
    displayMode,
    strict: "ignore",
    // HTML only — MathML dual output can inflate inline box size
    output: "html",
  });
}

/**
 * Renders documentation copy with optional KaTeX fragments.
 * Use `$...$` for inline and `$$...$$` for display math.
 */
export function MathText({ text, className, as: Tag = "p" }: MathTextProps) {
  const segments = splitMathSegments(text);

  return (
    <Tag className={className}>
      {segments.map((segment, index) => {
        if (segment.type === "text") {
          return <span key={`t-${index}`}>{segment.value}</span>;
        }

        return (
          <span
            key={`m-${index}`}
            className={
              segment.display
                ? "my-3 block overflow-x-auto text-text"
                : "mx-0.5 text-text"
            }
            dangerouslySetInnerHTML={{
              __html: renderKatex(segment.value, segment.display),
            }}
          />
        );
      })}
    </Tag>
  );
}
