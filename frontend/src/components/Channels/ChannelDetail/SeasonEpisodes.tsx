// TODO: Validate
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronRight } from "lucide-react"
import { useState } from "react"
import type { WhitelistEpisodeOutput, WhitelistSourceOutput } from "@/client"
import { ChannelsService } from "@/client"
import EditEpisode, {
  EpisodeInformationContent,
} from "@/components/Episodes/Edit"
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
  const episodeNumber = episode.tmdb_episode_number
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
  tmdbTitleId: string
  seasonId: string
  /** Whether the season itself carries an entry, which the labels read against. */
  seasonEnabled: boolean
  sourcesByTitleId: Map<string, WhitelistSourceOutput>
  tmdbTitleIds: Set<string>
  isEpisodeMarked: (episode: WhitelistEpisodeOutput) => boolean
  episodeExpiry: (episode: WhitelistEpisodeOutput) => string
  onEpisodeClick: (episode: WhitelistEpisodeOutput) => void
  episodeActionLabel: (
    episodeEnabled: boolean,
    seasonEnabled: boolean,
  ) => string
  /** Whether the filters are only being read, which leaves the marks off. */
  readOnly?: boolean
}

// TODO: Validate
// TODO: Validate
export function SeasonEpisodes({
  channelId,
  tmdbTitleId,
  seasonId,
  seasonEnabled,
  sourcesByTitleId,
  tmdbTitleIds,
  isEpisodeMarked,
  episodeExpiry,
  onEpisodeClick,
  episodeActionLabel,
  readOnly = false,
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
      "channelTitleSeasonEpisodes",
      channelId,
      tmdbTitleId,
      seasonId,
      offset,
    ],
    queryFn: () =>
      ChannelsService.getChannelWhitelistEpisodes({
        channelId,
        tmdbTitleId,
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
  const catalogueTitleIds = (titleIds: string[]) =>
    titleIds.filter((titleId) => tmdbTitleIds.has(titleId))

  // TODO: Validate
  const watchableTitleIds = (titleIds: string[]) =>
    titleIds.filter((titleId) => !tmdbTitleIds.has(titleId))

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
        const episodeTmdbTitleIds = catalogueTitleIds(episode.title_ids)
        return (
          <div key={episode.tmdb_episode_id}>
            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
              <Button
                className="ml-8"
                variant="ghost"
                size="icon-sm"
                onClick={() =>
                  toggleEpisodeInformation(episode.tmdb_episode_id)
                }
              >
                {informationEpisodeId === episode.tmdb_episode_id ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </Button>
              <span className="flex items-center">
                {episodeTmdbTitleIds.length > 0 && (
                  <SourceFavicons
                    titleIds={episodeTmdbTitleIds}
                    sourcesByTitleId={sourcesByTitleId}
                  />
                )}
              </span>
              <button
                type="button"
                className="flex-1 text-left text-sm hover:underline"
                onClick={() =>
                  toggleEpisodeInformation(episode.tmdb_episode_id)
                }
              >
                {episodeLabel(episode)}
                {episodeEnabled && expiry && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    (until {new Date(expiry).toLocaleString()})
                  </span>
                )}
              </button>
              <SourceFavicons
                titleIds={watchableTitleIds(episode.title_ids)}
                sourcesByTitleId={sourcesByTitleId}
              />
              {!readOnly && (
                <Button
                  variant={
                    episodeEnabled !== seasonEnabled ? "default" : "outline"
                  }
                  size="sm"
                  onClick={() => onEpisodeClick(episode)}
                >
                  {episodeActionLabel(episodeEnabled, seasonEnabled)}
                </Button>
              )}
              <ExternalMediaLink
                url={episode.url}
                label="Open this episode on its site"
              />
              <AdminOnly>
                <EditEpisode episode={episode} />
              </AdminOnly>
              <MediaPageButton
                to="/episodes"
                search={{ season_id: seasonId }}
                label="Open this episode's season here"
              />
            </div>
            {informationEpisodeId === episode.tmdb_episode_id && (
              <div className="ml-16 space-y-1">
                {episode.links.map((link) => {
                  const linkSource = sourcesByTitleId.get(link.title_id)
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
                            referrerPolicy="no-referrer"
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
                          {linkSource?.source_key ?? "Unknown source"}
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
                          <EpisodeInformationContent episode={link} enabled />
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
