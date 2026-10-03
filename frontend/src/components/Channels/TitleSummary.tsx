// TODO: Validate
import { type ReactNode, useLayoutEffect, useRef, useState } from "react"
import type { ChannelTitleStats, TitleCardDetails } from "@/client"
import { ScoreBadges } from "@/components/ChannelCommon/ScoreBadges"
import type { Title } from "@/components/Channels/TitleCards"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

// TODO: Validate
function titleFacts(
  tmdbTitle: Title | undefined,
  stats: ChannelTitleStats | undefined,
): string[] {
  const facts = [tmdbTitle?.media_type ?? "Not linked to TMDB"]
  // A movie is one episode of one season by construction, so counting them says
  // nothing the "Movie" note has not already said.
  const countsAreImplied =
    tmdbTitle?.media_type === "Movie" &&
    stats?.season_count === 1 &&
    stats?.episode_count === 1
  if (countsAreImplied) {
    return facts
  }
  if (stats?.season_count) {
    const seasonCount = stats.season_count
    facts.push(`${seasonCount} ${seasonCount === 1 ? "season" : "seasons"}`)
  }
  if (stats?.episode_count) {
    const episodeCount = stats.episode_count
    facts.push(`${episodeCount} ${episodeCount === 1 ? "episode" : "episodes"}`)
  }
  return facts
}

// TODO: Validate
function formatRuntime(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`
}

// TODO: Validate
function runtimeFact(
  tmdbTitle: Title | undefined,
  details: TitleCardDetails | undefined,
): string | null {
  if (!details?.runtime) return null
  const runtime = formatRuntime(details.runtime)
  return tmdbTitle?.media_type === "Movie" ? runtime : `${runtime} / episode`
}

// TODO: Validate
function languageName(code: string): string {
  try {
    return new Intl.DisplayNames(["en"], { type: "language" }).of(code) ?? code
  } catch {
    return code
  }
}

// TODO: Validate
function languageNames(
  tmdbTitle: Title | undefined,
  details: TitleCardDetails | undefined,
): string[] {
  const codes = [tmdbTitle?.original_language, ...(details?.languages ?? [])]
  return [
    ...new Set(
      codes.filter((code): code is string => !!code).map(languageName),
    ),
  ]
}

// TODO: Validate
export function FilledDescription({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false)
  const [lines, setLines] = useState(4)
  const [overflowing, setOverflowing] = useState(false)
  const boxRef = useRef<HTMLDivElement>(null)
  const textRef = useRef<HTMLParagraphElement>(null)

  useLayoutEffect(() => {
    const box = boxRef.current
    const paragraph = textRef.current
    if (!box || !paragraph || expanded) return
    // TODO: Validate
    const measure = () => {
      const lineHeight = Number.parseFloat(
        getComputedStyle(paragraph).lineHeight,
      )
      const fitting = Math.max(1, Math.floor(box.clientHeight / lineHeight))
      setLines(fitting)
      setOverflowing(paragraph.scrollHeight > fitting * lineHeight + 1)
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(box)
    return () => observer.disconnect()
  }, [expanded])

  return (
    <>
      <div
        ref={boxRef}
        className={expanded ? undefined : "relative min-h-20 flex-1"}
      >
        <p
          ref={textRef}
          className={`text-sm text-muted-foreground${expanded ? " whitespace-pre-wrap" : " absolute inset-x-0 top-0 overflow-hidden"}`}
          style={
            expanded
              ? undefined
              : {
                  display: "-webkit-box",
                  WebkitBoxOrient: "vertical",
                  WebkitLineClamp: lines,
                }
          }
        >
          {text}
        </p>
      </div>
      {(overflowing || expanded) && (
        <button
          type="button"
          className="relative z-10 self-start text-xs font-medium text-primary hover:underline"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </>
  )
}

// TODO: Validate
function summaryLines(
  title: Title | undefined,
  stats: ChannelTitleStats | null | undefined,
  details: TitleCardDetails | undefined,
) {
  const [mediaType, ...counts] = titleFacts(title, stats ?? undefined)
  const lengthFacts = [...counts, runtimeFact(title, details)].filter(
    (fact): fact is string => !!fact,
  )
  const typeAndLengthLines = (
    mediaType === "Movie"
      ? [[mediaType, ...lengthFacts].join(" · ")]
      : [mediaType === "Series" ? null : mediaType, lengthFacts.join(" · ")]
  ).filter((line): line is string => !!line)
  const [mainLanguage, ...otherLanguages] = languageNames(title, details)
  const languageLine = mainLanguage
    ? `${mainLanguage}${otherLanguages.length > 0 ? ` · Also ${otherLanguages.join(", ")}` : ""}`
    : null
  return { languageLine, typeAndLengthLines }
}

// TODO: Validate
export function TitleSummaryLayout({
  artwork,
  artworkAlt,
  artworkOverlay,
  title,
  stats,
  details,
  heading,
  extraLines = [],
  description,
  footer,
  contentClassName,
}: {
  artwork?: string | null
  artworkAlt: string
  artworkOverlay?: ReactNode
  title?: Title
  stats?: ChannelTitleStats | null
  details?: TitleCardDetails
  heading: ReactNode
  extraLines?: string[]
  description?: ReactNode
  footer?: ReactNode
  contentClassName?: string
}) {
  const { languageLine, typeAndLengthLines } = summaryLines(
    title,
    stats,
    details,
  )
  const genres = details?.genres ?? []

  return (
    <div className="flex w-full gap-3 p-3 text-left">
      <div className="flex w-36 shrink-0 flex-col gap-2">
        <div className="relative aspect-2/3 w-full overflow-hidden rounded-md bg-muted">
          <img
            referrerPolicy="no-referrer"
            loading="lazy"
            decoding="async"
            src={artwork ?? "/no-image.svg"}
            alt={artworkAlt}
            className="size-full object-cover"
          />
          {artworkOverlay}
        </div>
        {title && (
          <div className="relative z-10 flex flex-col items-start gap-1">
            <ScoreBadges title={title} />
          </div>
        )}
      </div>
      <div
        className={cn("flex min-w-0 flex-1 flex-col gap-2", contentClassName)}
      >
        <div className="flex flex-col gap-0.5">
          {heading}
          {languageLine && (
            <span className="text-sm text-muted-foreground">
              {languageLine}
            </span>
          )}
          {genres.length > 0 && (
            <div className="my-1 flex flex-wrap gap-1">
              {genres.map((genre) => (
                <Badge key={genre} variant="outline">
                  {genre}
                </Badge>
              ))}
            </div>
          )}
          {[...extraLines, ...typeAndLengthLines].map((line) => (
            <span key={line} className="text-sm text-muted-foreground">
              {line}
            </span>
          ))}
        </div>
        {description}
        {footer}
      </div>
    </div>
  )
}
