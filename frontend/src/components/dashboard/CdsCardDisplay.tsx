import {
  INDICATOR_STYLES,
  type CdsCard,
  type CdsIndicator,
} from "@/types/dashboard";

interface CdsCardDisplayProps {
  cards: CdsCard[];
}

/**
 * Renders a list of CDS Hooks 2.0 cards.
 *
 * Each card is styled according to its indicator level
 * (critical / warning / info) and renders markdown-like
 * detail content with suggestions.
 */
export function CdsCardDisplay({ cards }: CdsCardDisplayProps) {
  if (cards.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-700">
        Clinical Decision Support
      </h3>
      {cards.map((card, i) => (
        <CdsCardItem key={i} card={card} />
      ))}
    </div>
  );
}

function CdsCardItem({ card }: { card: CdsCard }) {
  const style = INDICATOR_STYLES[card.indicator];

  return (
    <div
      className={`rounded-xl border p-4 ${style.bg} ${style.border}`}
    >
      <div className="flex items-start gap-3">
        <IndicatorIcon indicator={card.indicator} className={style.icon} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-900">{card.summary}</p>

          {card.detail && (
            <div className="mt-2 text-sm leading-relaxed text-slate-700">
              <FormattedDetail text={card.detail} />
            </div>
          )}

          {card.suggestions.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {card.suggestions.map((s, j) => (
                <span
                  key={j}
                  className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium ${
                    s.is_recommended
                      ? "bg-primary-100 text-primary-800 ring-1 ring-primary-200"
                      : "bg-white text-slate-600 ring-1 ring-slate-200"
                  }`}
                >
                  {s.is_recommended && (
                    <svg
                      className="mr-1 h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9 12.75L11.25 15 15 9.75"
                      />
                    </svg>
                  )}
                  {s.label}
                </span>
              ))}
            </div>
          )}

          <p className="mt-2 text-[11px] text-slate-400">
            {card.source.label}
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Renders markdown-like bold (**text**), bullet lists, and newlines
 * from CDS card detail strings.
 */
function FormattedDetail({ text }: { text: string }) {
  const lines = text.split("\n");

  return (
    <>
      {lines.map((line, i) => {
        if (line.trim() === "") return <br key={i} />;

        const isBullet = line.trimStart().startsWith("- ");
        const content = isBullet ? line.replace(/^\s*-\s*/, "") : line;

        const parts = content.split(/(\*\*[^*]+\*\*)/g).map((part, j) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return (
              <strong key={j} className="font-semibold text-slate-900">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <span key={j}>{part}</span>;
        });

        if (isBullet) {
          return (
            <div key={i} className="flex gap-1.5 pl-2">
              <span className="mt-1.5 h-1 w-1 flex-shrink-0 rounded-full bg-slate-400" />
              <span>{parts}</span>
            </div>
          );
        }

        return <p key={i}>{parts}</p>;
      })}
    </>
  );
}

function IndicatorIcon({
  indicator,
  className,
}: {
  indicator: CdsIndicator;
  className: string;
}) {
  if (indicator === "critical") {
    return (
      <svg
        className={`mt-0.5 h-5 w-5 flex-shrink-0 ${className}`}
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={2}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
        />
      </svg>
    );
  }
  if (indicator === "warning") {
    return (
      <svg
        className={`mt-0.5 h-5 w-5 flex-shrink-0 ${className}`}
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={2}
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
        />
      </svg>
    );
  }
  return (
    <svg
      className={`mt-0.5 h-5 w-5 flex-shrink-0 ${className}`}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
      />
    </svg>
  );
}
