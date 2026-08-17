// TODO: Validate
import { useQuery } from "@tanstack/react-query"

import type { EpisodeInformationOutput, EpisodeInformationSide } from "@/client"
import { EpisodesService } from "@/client"
import { InformationHero } from "@/components/ChannelCommon/InformationHero"
import { formatInformationDate } from "@/components/ChannelCommon/InformationTable"

// TODO: Validate
export function formatDuration(value: number | null) {
  if (value == null) return null
  const minutes = Math.floor(value / 60)
  const seconds = value % 60
  return `${value}s (${minutes}m ${seconds}s)`
}

// TODO: Validate
/**
 * The side the episode is shown as, which is TMDB's account of it wherever TMDB
 * has one, and the website's own where the website's row is what was opened.
 */
export function primarySide(
  data: EpisodeInformationOutput,
  preferSource: boolean,
): EpisodeInformationSide {
  if (preferSource) return data.source
  return data.tmdb ?? data.source
}

// TODO: Validate
function heroSubtitle(data: EpisodeInformationOutput, preferSource: boolean) {
  const side = primarySide(data, preferSource)
  const seasonNumber = side.season_number ?? data.source.season_number
  const episodeNumber = side.episode_number ?? data.source.episode_number
  const placement = [
    seasonNumber != null ? `Season ${seasonNumber}` : side.season_name,
    episodeNumber != null ? `Episode ${episodeNumber}` : null,
  ].filter(Boolean)
  return [side.show_name, ...placement].filter(Boolean).join(" · ")
}

// TODO: Validate
function heroFacts(data: EpisodeInformationOutput, preferSource: boolean) {
  const side = primarySide(data, preferSource)
  const facts = [
    formatDuration(side.duration ?? data.source.duration),
    formatInformationDate(side.air_date ?? data.source.air_date),
    data.tmdb ? "Linked to TMDB" : "Not linked to TMDB",
    data.source.label,
  ]
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function heroLinks(data: EpisodeInformationOutput) {
  const links = []
  if (data.source.url) {
    links.push({ label: data.source.label, href: data.source.url })
  }
  if (data.tmdb?.url) {
    links.push({ label: data.tmdb.label, href: data.tmdb.url })
  }
  return links
}

/** Where the episode's information is held, which every reader of it shares. */
export const episodeInformationQueryKey = (episodeId: string) => [
  "episode-information",
  episodeId,
]

interface EpisodeInformationHeroProps {
  episodeId: string
  /** Whether the information is wanted yet, so a closed window fetches nothing. */
  enabled?: boolean
  /**
   * Whether the website's own row is what was opened, in which case that is what
   * is shown rather than TMDB's account of the episode it was matched to.
   */
  preferSource?: boolean
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
  preferSource = false,
}: EpisodeInformationHeroProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: episodeInformationQueryKey(episodeId),
    queryFn: () => EpisodesService.getEpisodeInformation({ episodeId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })

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

  const side = primarySide(data, preferSource)

  return (
    <InformationHero
      title={side.name ?? data.source.name ?? "Unnamed episode"}
      subtitle={heroSubtitle(data, preferSource)}
      description={side.description ?? data.source.description}
      imageUrl={side.image_url ?? data.source.image_url}
      facts={heroFacts(data, preferSource)}
      links={heroLinks(data)}
    />
  )
}
