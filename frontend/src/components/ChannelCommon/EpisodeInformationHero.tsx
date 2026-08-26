// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import type { ReactNode } from "react"

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
export function durationText(value: number | null) {
  if (value == null) return null
  return `${Math.floor(value / 60)}m ${value % 60}s`
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
  const seasonNumber = side.season_number
  const episodeNumber = side.episode_number
  const placement = [
    seasonNumber != null ? `Season ${seasonNumber}` : side.season_name,
    episodeNumber != null ? `Episode ${episodeNumber}` : null,
  ].filter(Boolean)
  return [side.show_name, ...placement].filter(Boolean).join(" · ")
}

// TODO: Validate
function heroFacts(
  data: EpisodeInformationOutput,
  preferSource: boolean,
  spelledOutDuration: boolean,
) {
  const side = primarySide(data, preferSource)
  const facts = [
    spelledOutDuration
      ? durationText(side.duration)
      : formatDuration(side.duration),
    formatInformationDate(side.air_date),
    // What TMDB has to do with the episode is no part of one website's own
    // account of it, so it is left out where the website's row is what was
    // opened.
    preferSource ? null : data.tmdb ? "Linked to TMDB" : "Not linked to TMDB",
    data.source.label,
  ]
  return facts.filter((fact): fact is string => !!fact)
}

// TODO: Validate
function heroLinks(data: EpisodeInformationOutput, preferSource: boolean) {
  const links = []
  if (data.source.url) {
    links.push({ label: data.source.label, href: data.source.url })
  }
  if (!preferSource && data.tmdb?.url) {
    links.push({ label: data.tmdb.label, href: data.tmdb.url })
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
  /**
   * Whether the website's own row is what was opened, in which case its own
   * account is the whole of what is shown: TMDB's stands beside the episode
   * rather than beside one website's listing of it, and reading it here would
   * put words in the website's mouth.
   */
  preferSource?: boolean
  spelledOutDuration?: boolean
  titleAction?: ReactNode
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
  spelledOutDuration = false,
  titleAction,
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

  const side = primarySide(data, preferSource)

  return (
    <InformationHero
      title={side.name ?? "Unnamed episode"}
      subtitle={heroSubtitle(data, preferSource)}
      description={side.description}
      imageUrl={side.image_url}
      facts={heroFacts(data, preferSource, spelledOutDuration)}
      links={heroLinks(data, preferSource)}
      titleAction={titleAction}
    />
  )
}
