// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"

import type { EpisodeOutput, SeasonWithEpisodeCountOutput } from "@/client"
import { SeasonsService, TitlesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { useOpenMedia } from "@/hooks/useOpenMedia"

// TODO: Validate
function seasonLabel(season: SeasonWithEpisodeCountOutput) {
  if (season.name) {
    return season.name
  }
  return `Season ${season.season_number ?? "?"}`
}

// TODO: Validate
function episodeLabel(episode: EpisodeOutput) {
  const number = episode.episode_number
  if (number == null) {
    return episode.name ?? episode.key
  }
  return `Episode ${number}${episode.name ? ` - ${episode.name}` : ""}`
}

// TODO: Validate
function SeasonEpisodeRows({ seasonId }: { seasonId: string }) {
  const openMedia = useOpenMedia()
  const { data, isLoading } = useQuery({
    queryKey: ["season-episodes", seasonId],
    queryFn: () => SeasonsService.getSeasonEpisodes({ seasonId }),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <p className="px-2 py-2 text-sm text-muted-foreground">
        Loading episodes…
      </p>
    )
  }
  if (!data?.length) {
    return (
      <p className="px-2 py-2 text-sm text-muted-foreground">
        No episodes stored for this season.
      </p>
    )
  }

  return (
    <div className="space-y-1">
      {data.map((episode) => (
        <button
          key={episode.id}
          type="button"
          className="flex w-full items-center gap-1 rounded-md p-2 text-left text-sm hover:bg-accent/30"
          onClick={() => openMedia({ kind: "episode", episode })}
        >
          {episodeLabel(episode)}
        </button>
      ))}
    </div>
  )
}

interface TitleSeasonsSectionProps {
  titleId: string
  /** Whether the seasons are wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
}

// TODO: Validate
/**
 * The seasons a title holds, each opening into the episodes stored under it.
 */
export function TitleSeasonsSection({
  titleId,
  enabled = true,
}: TitleSeasonsSectionProps) {
  const [openSeasonId, setOpenSeasonId] = useState<string | null>(null)
  const { data } = useQuery({
    queryKey: ["title-seasons", titleId],
    queryFn: () => TitlesService.getTitleSeasons({ titleId }),
    enabled,
    staleTime: 5 * 60 * 1000,
  })

  if (!data) {
    return null
  }

  return (
    <CollapsibleSection title="Seasons" defaultOpen>
      {data.length === 0 && (
        <p className="px-2 py-2 text-sm text-muted-foreground">
          No episodes found.
        </p>
      )}
      <div className="space-y-1">
        {data.map((season) => (
          <div key={season.id}>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-md p-2 text-left text-sm hover:bg-accent/30"
              onClick={() =>
                setOpenSeasonId(openSeasonId === season.id ? null : season.id)
              }
            >
              {openSeasonId === season.id ? (
                <ChevronDown className="h-4 w-4 shrink-0" />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0" />
              )}
              <span className="flex-1">{seasonLabel(season)}</span>
              <span className="text-xs text-muted-foreground">
                {season.episode_count} episodes
              </span>
            </button>
            {openSeasonId === season.id && (
              <div className="ml-6 border-l pl-2">
                <SeasonEpisodeRows seasonId={season.id} />
              </div>
            )}
          </div>
        ))}
      </div>
    </CollapsibleSection>
  )
}
