import type { EpisodeWithDetails } from "../columns"

/** Props shared by all card overlay components. */
export type CardOverlayProps = { episode: EpisodeWithDetails }

/** Wrapper that adds negative top margin to tighten the gap between the image and the text. */
export function CardTextArea({ children }: { children: React.ReactNode }) {
  return <div className="-mt-6">{children}</div>
}

/**
 * Displays the favicon + show name on the left and a list of detail strings on the right.
 * Null values in `details` are filtered out.
 */
export function CardSourceRow({
  episode,
  details,
}: {
  episode: EpisodeWithDetails
  details: (string | null)[]
}) {
  return (
    <div className="flex">
      {/* This div contains the favicon and source name */}
      {/* flex - Make this a 2 column display */}
      {/* items-center - Vertically center the text so it is not butted up against the image */}
      {/* gap-2 - Small gap between the favicon and the source name */}
      {/* flex-1 - Make the favicon and source name take up as much space as possible so the date and duration will be as far right as possible */}
      {/* min-w-0 - Make sure all columns are always visible. Without this the show name can push the date and duration off of the card */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {episode.source.favicon_url && (
          <img
            src={episode.source.favicon_url}
            alt={episode.source.name ?? undefined}
            className="size-6"
          />
        )}
        <span className="font-bold text-base truncate group-hover:whitespace-normal group-hover:overflow-visible">
          {episode.show.name}
        </span>
      </div>
      {/* This div contains the date and duration */}
      {/* flex/flex-col - Make this a column based display  */}
      {/* items-end - Right justify the text */}{" "}
      <div className="flex flex-col items-end">
        {details
          .filter((d): d is string => d !== null)
          .map((detail) => (
            <span key={detail} className="text-xs text-muted-foreground">
              {detail}
            </span>
          ))}
      </div>
    </div>
  )
}

/** A single line of metadata with an optional label and a value. */
type CardMetaLine = {
  label?: string
  value: string | null | undefined
  /** Optional className applied to the value span (e.g. "font-bold"). */
  valueClassName?: string
}

/**
 * Displays one or more lines of secondary metadata (season/episode labels, playlist names, etc.).
 * Text truncates on small cards and expands on hover.
 * If label is provided, renders as `label: value`. Otherwise just `value`.
 */
export function CardMetaLines({ lines }: { lines: CardMetaLine[] }) {
  const baseClass =
    // group-hover:whitespace-normal - Expand card to show all of the text when it is hovered over.
    // group-hover:overflow-visible - Expand text when the card is hovered over.
    "text-sm text-muted-foreground truncate group-hover:whitespace-normal group-hover:overflow-visible"

  return (
    // flex/flex-col - Make this a column based display
    <div className="flex flex-col">
      {lines
        // Filter lines where line.value is not a string
        .filter(
          (line): line is CardMetaLine & { value: string } =>
            line.value != null,
        )
        .map((line) => (
          <span key={line.label ?? line.value} className={baseClass}>
            {line.label ? (
              <>
                {line.label}{" "}
                <span className={line.valueClassName}>{line.value}</span>
              </>
            ) : (
              <span className={line.valueClassName}>{line.value}</span>
            )}
          </span>
        ))}
    </div>
  )
}
