// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"
import type { WhitelistEpisodeOutput, WhitelistSourceOutput } from "@/client"
import { ChannelsService } from "@/client"
import { EpisodeInformationPanel } from "@/components/ChannelCommon/EpisodeInformationDialog"
import EditEpisode from "@/components/Episodes/Edit"
import { Button } from "@/components/ui/button"
import {
  AdminOnly,
  ExternalMediaLink,
  MediaPageButton,
} from "./MediaPageButton"
import { SourceFavicons } from "./SourceFavicons"

// How many of a season's episodes the server serves at once, which is what the
// page numbering here counts in.
const PAGE_SIZE = 100

// A name that says nothing the episode's own number does not, whether the site
// wrote it as "Episode 3", "EP 3", or just "3".
const NUMBERED_EPISODE_NAME = /^(?:episode|ep\.?)?\s*0*(\d+)$/i

// TODO: Validate
export function episodeLabel(episode: WhitelistEpisodeOutput) {
  const episodeName = episode.name ?? ""
  const episodeNumber = episode.episode_number
  if (episodeNumber == null) {
    return episodeName
  }
  // A website that never named an episode calls it by its number, which the
  // label already says, so "Episode 3 - Episode 3" is read as "Episode 3".
  const nameIsNumber = NUMBERED_EPISODE_NAME.exec(episodeName)
  const named = episodeName && Number(nameIsNumber?.[1]) !== episodeNumber
  return `Episode ${episodeNumber}${named ? ` - ${episodeName}` : ""}`
}

interface SeasonEpisodesProps {
  channelId: string
  canonicalShowId: string
  seasonId: string
  /** Whether the season itself carries an entry, which the labels read against. */
  seasonEnabled: boolean
  sourcesByShowId: Map<string, WhitelistSourceOutput>
  tmdbShowIds: Set<string>
  isEpisodeMarked: (episode: WhitelistEpisodeOutput) => boolean
  episodeExpiry: (episode: WhitelistEpisodeOutput) => string
  onEpisodeClick: (episode: WhitelistEpisodeOutput) => void
  episodeActionLabel: (
    episodeEnabled: boolean,
    seasonEnabled: boolean,
  ) => string
}

// TODO: Validate
/**
 * The episodes of one season, read a page at a time as the season is expanded.
 *
 * A title's whole catalogue is far more than the filter page ever shows at
 * once, so a season's episodes are asked for only when somebody opens it.
 */
export function SeasonEpisodes({
  channelId,
  canonicalShowId,
  seasonId,
  seasonEnabled,
  sourcesByShowId,
  tmdbShowIds,
  isEpisodeMarked,
  episodeExpiry,
  onEpisodeClick,
  episodeActionLabel,
}: SeasonEpisodesProps) {
  const [offset, setOffset] = useState(0)
  // The record whose information panel is open, if any.
  const [informationEpisodeId, setInformationEpisodeId] = useState<
    string | null
  >(null)
  const [informationLinkEpisodeId, setInformationLinkEpisodeId] = useState<
    string | null
  >(null)

  const { data, isLoading } = useQuery({
    queryKey: [
      "channelShowSeasonEpisodes",
      channelId,
      canonicalShowId,
      seasonId,
      offset,
    ],
    queryFn: () =>
      ChannelsService.getChannelWhitelistEpisodes({
        channelId,
        canonicalShowId,
        seasonId,
        offset,
        limit: PAGE_SIZE,
      }),
    placeholderData: keepPreviousData,
  })

  // TODO: Validate
  const toggleEpisodeInformation = (episodeId: string) => {
    setInformationEpisodeId(
      informationEpisodeId === episodeId ? null : episodeId,
    )
  }

  // TODO: Validate
  const toggleLinkInformation = (linkEpisodeId: string) => {
    setInformationLinkEpisodeId(
      informationLinkEpisodeId === linkEpisodeId ? null : linkEpisodeId,
    )
  }

  // TODO: Validate
  const catalogueShowIds = (showIds: string[]) =>
    showIds.filter((showId) => tmdbShowIds.has(showId))

  // TODO: Validate
  const watchableShowIds = (showIds: string[]) =>
    showIds.filter((showId) => !tmdbShowIds.has(showId))

  if (isLoading && !data) {
    return (
      <div className="p-2">
        <p className="text-sm text-muted-foreground text-center py-2">
          Loading episodes…
        </p>
      </div>
    )
  }

  const episodes = data?.episodes ?? []
  const totalCount = data?.total_count ?? 0

  if (episodes.length === 0) {
    return (
      <div className="p-2">
        <p className="text-sm text-muted-foreground text-center py-2">
          No episodes found
        </p>
      </div>
    )
  }

  return (
    <div className="p-2 space-y-1">
      {episodes.map((episode) => {
        const episodeEnabled = isEpisodeMarked(episode)
        const expiry = episodeExpiry(episode)
        const episodeTmdbShowIds = catalogueShowIds(episode.show_ids)
        return (
          <div key={episode.id}>
            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
              <Button
                className="ml-8"
                variant="ghost"
                size="icon-sm"
                onClick={() => toggleEpisodeInformation(episode.id)}
              >
                {informationEpisodeId === episode.id ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </Button>
              <span className="flex items-center">
                {episodeTmdbShowIds.length > 0 && (
                  <SourceFavicons
                    showIds={episodeTmdbShowIds}
                    sourcesByShowId={sourcesByShowId}
                  />
                )}
              </span>
              <button
                type="button"
                className="flex-1 text-left text-sm hover:underline"
                onClick={() => toggleEpisodeInformation(episode.id)}
              >
                {episodeLabel(episode)}
                {episodeEnabled && expiry && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    (until {new Date(expiry).toLocaleString()})
                  </span>
                )}
              </button>
              <SourceFavicons
                showIds={watchableShowIds(episode.show_ids)}
                sourcesByShowId={sourcesByShowId}
              />
              <Button
                variant={
                  episodeEnabled !== seasonEnabled ? "default" : "outline"
                }
                size="sm"
                onClick={() => onEpisodeClick(episode)}
              >
                {episodeActionLabel(episodeEnabled, seasonEnabled)}
              </Button>
              <ExternalMediaLink
                url={episode.url}
                label="Open this episode on its site"
              />
              <AdminOnly>
                <EditEpisode episode={episode} />
              </AdminOnly>
              <MediaPageButton
                to="/season/$seasonKey"
                params={{ seasonKey: seasonId }}
                label="Open this episode's season here"
              />
            </div>
            {informationEpisodeId === episode.id && (
              <div className="ml-16 space-y-1">
                {episode.links.map((link) => {
                  const linkSource = sourcesByShowId.get(link.show_id)
                  return (
                    <div key={link.episode_id}>
                      <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => toggleLinkInformation(link.episode_id)}
                        >
                          {informationLinkEpisodeId === link.episode_id ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </Button>
                        {linkSource?.favicon_url && (
                          <img
                            src={linkSource.favicon_url}
                            alt=""
                            className="size-6 shrink-0"
                          />
                        )}
                        <button
                          type="button"
                          className="flex-1 text-left text-sm hover:underline"
                          onClick={() => toggleLinkInformation(link.episode_id)}
                        >
                          {linkSource?.source_name ?? "Unknown source"}
                        </button>
                        <ExternalMediaLink
                          url={link.url}
                          label="Open this episode on its site"
                        />
                        <AdminOnly>
                          <EditEpisode episode={link} />
                        </AdminOnly>
                      </div>
                      {informationLinkEpisodeId === link.episode_id && (
                        <div className="ml-8 rounded border bg-muted/30 p-4">
                          <EpisodeInformationPanel
                            episodeId={link.episode_id}
                            preferSource
                          />
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}

      {totalCount > PAGE_SIZE && (
        <div className="flex items-center justify-between gap-2 px-2 py-1">
          <span className="text-xs text-muted-foreground">
            Episodes {offset + 1}–{offset + episodes.length} of {totalCount}
          </span>
          <span className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + episodes.length >= totalCount}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </span>
        </div>
      )}
    </div>
  )
}
