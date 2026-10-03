// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { SquareArrowOutUpRight } from "lucide-react"

import type { EpisodeInformationSide } from "@/client"
import { EpisodesService } from "@/client"
import { EpisodeTitle } from "@/components/ChannelCommon/EpisodeTitle"
import { InformationHero } from "@/components/ChannelCommon/InformationHero"
import { formatInformationDate } from "@/components/ChannelCommon/InformationTable"

// TODO: Validate
export function formatDuration(value: number | null | undefined) {
  if (value == null) return null
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return `${value}s (${minutes}m ${seconds}s)`
}

// TODO: Validate
export function durationText(value: number | null | undefined) {
  if (value == null) return null
  return `${Math.floor(value / 60)}m ${value % 60}s`
}

// TODO: Validate
function seasonLine(side: EpisodeInformationSide) {
  const seasonName = side.season.name
  const seasonNumber = side.season.season_number
  return seasonName ?? (seasonNumber != null ? `Season ${seasonNumber}` : null)
}

// TODO: Validate
function heroSubtitle(
  side: EpisodeInformationSide,
  onOpenTitle: ((titleId: string) => void) | undefined,
) {
  const season = seasonLine(side)
  return (
    <>
      {season ? <span>{season}</span> : null}
      {onOpenTitle ? (
        <button
          type="button"
          className="flex cursor-pointer items-center gap-1 self-start text-left font-medium text-primary underline underline-offset-2 hover:no-underline"
          onClick={() => onOpenTitle(side.title.id)}
        >
          {side.title.name ?? "Unnamed title"}
          <SquareArrowOutUpRight className="h-3 w-3 shrink-0" />
        </button>
      ) : (
        <span>{side.title.name}</span>
      )}
    </>
  )
}

// TODO: Validate
function heroFacts(side: EpisodeInformationSide, spelledOutDuration: boolean) {
  const facts = [
    spelledOutDuration
      ? durationText(side.episode.duration)
      : formatDuration(side.episode.duration),
    formatInformationDate(side.episode.air_date),
    side.absolute_number != null
      ? `Absolute Episode #${side.absolute_number}`
      : null,
  ]
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function sideLinks(side: EpisodeInformationSide) {
  return [
    {
      label: `${side.label} Episode`,
      href: side.episode.tmdb_url ?? side.episode.url,
    },
    {
      label: `${side.label} Season`,
      href: side.season.tmdb_url ?? side.season.url,
    },
    {
      label: `${side.label} Title`,
      href: side.title.tmdb_url ?? side.title.url,
    },
  ]
}

// TODO: Validate
function heroLinks(side: EpisodeInformationSide) {
  const links: { label: string; href: string }[] = []
  for (const { label, href } of sideLinks(side)) {
    if (href && !links.some((link) => link.href === href)) {
      links.push({ label, href })
    }
  }
  return links
}

// TODO: Validate
/** Where the episode's information is held, which every reader of it shares. */
export const episodeInformationQueryKey = (episodeId: string) => [
  "episode-information",
  episodeId,
]

// TODO: Validate
export function useEpisodeInformation(episodeId: string, enabled = true) {
  return useQuery({
    queryKey: episodeInformationQueryKey(episodeId),
    queryFn: () => EpisodesService.getEpisodeInformation({ episodeId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

interface EpisodeInformationHeroProps {
  episodeId: string
  /** Whether the information is wanted yet, so a closed window fetches nothing. */
  enabled?: boolean
  spelledOutDuration?: boolean
  onOpenTitle?: (titleId: string) => void
}

// TODO: Validate
/**
 * The episode at a glance: its image, what it is called, where it sits, and how
 * long it runs.
 *
 * Its own component because it is read wherever an episode is worked on rather
 * than only where it is read about - a window settling which episode a row
 * stands for wants the same few lines above it, and reading them off a second
 * shape of the same data is how the two drift apart.
 */
export function EpisodeInformationHero({
  episodeId,
  enabled = true,
  spelledOutDuration = false,
  onOpenTitle,
}: EpisodeInformationHeroProps) {
  const { data, isLoading, error } = useEpisodeInformation(episodeId, enabled)

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Loading episode information…
      </p>
    )
  }
  if (error || !data) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn't load the episode information.
      </p>
    )
  }

  const side = data.source

  return (
    <InformationHero
      title={
        <EpisodeTitle
          name={side.episode.name}
          episodeNumber={side.episode.episode_number}
        />
      }
      imageAlt={side.episode.name ?? "Unnamed episode"}
      subtitle={heroSubtitle(side, onOpenTitle)}
      description={side.episode.description}
      imageUrl={side.episode.thumbnail_url ?? side.episode.image_url}
      facts={heroFacts(side, spelledOutDuration)}
      links={heroLinks(side)}
    />
  )
}
