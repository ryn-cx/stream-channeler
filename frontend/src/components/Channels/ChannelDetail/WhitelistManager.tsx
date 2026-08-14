// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, ChevronUp } from "lucide-react"
import { useEffect, useState } from "react"
import type {
  WhitelistEpisodeOutput,
  WhitelistSeasonOutput,
  WhitelistShowInput,
  WhitelistSourceOutput,
} from "@/client"
import { ChannelsService } from "@/client"
import { EpisodeInformationPanel } from "@/components/ChannelCommon/EpisodeInformationDialog"
import { ShowInformationPanel } from "@/components/ChannelCommon/ShowInformationDialog"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EpisodeExpiryDialog } from "./EpisodeExpiryDialog"
import { isExpired, isoToLocalInput, localInputToIso } from "./expiry"

// TODO: Validate
/** The favicons of the websites' links a season or episode was found on. */
function SourceFavicons({
  showIds,
  sourcesByShowId,
}: {
  showIds: string[]
  sourcesByShowId: Map<string, WhitelistSourceOutput>
}) {
  return (
    <span className="flex items-center gap-1 shrink-0">
      {showIds.map((showId) => {
        const source = sourcesByShowId.get(showId)
        if (!source?.favicon_url) return null
        return (
          <Tooltip key={showId}>
            <TooltipTrigger asChild>
              <img
                src={source.favicon_url}
                alt={`${source.source_name} favicon`}
                className="size-6 shrink-0"
              />
            </TooltipTrigger>
            <TooltipContent>
              {source.source_name ?? "Unknown source"}
            </TooltipContent>
          </Tooltip>
        )
      })}
    </span>
  )
}

// A name that says nothing the episode's own number does not, whether the site
// wrote it as "Episode 3", "EP 3", or just "3".
const NUMBERED_EPISODE_NAME = /^(?:episode|ep\.?)?\s*0*(\d+)$/i

// TODO: Validate
function seasonLabel(
  season: WhitelistSeasonOutput,
  anySeasonHasNumber: boolean,
) {
  if (!anySeasonHasNumber) {
    return season.name ?? ""
  }
  const seasonName = season.name ? ` - ${season.name}` : ""
  return `Season ${season.season_number ?? "?"}${seasonName}`
}

/**
 * The episodes of each season, keyed by the season they belong to.
 *
 * An episode is under the season its canonical episode is under, which the
 * server has already answered with: a site that files an episode somewhere the
 * title does not is read as the title has it, so nothing here has to work out
 * which season a row belongs to a second time.
 */
// TODO: Validate
function episodesBySeason(
  episodes: WhitelistEpisodeOutput[],
): Map<string, WhitelistEpisodeOutput[]> {
  const bySeason = new Map<string, WhitelistEpisodeOutput[]>()
  for (const episode of episodes) {
    const seasonEpisodes = bySeason.get(episode.season_id) ?? []
    seasonEpisodes.push(episode)
    bySeason.set(episode.season_id, seasonEpisodes)
  }
  // A season the sites number between them is read in the title's order, which
  // is the only order every episode of it is in.
  for (const seasonEpisodes of bySeason.values()) {
    if (
      seasonEpisodes.every((episode) => episode.tmdb_episode_number != null)
    ) {
      seasonEpisodes.sort(
        (first, second) =>
          (first.tmdb_episode_number ?? 0) - (second.tmdb_episode_number ?? 0),
      )
    }
  }
  return bySeason
}

interface WhitelistManagerProps {
  channelId: string
  showId: string
  showName: string
  onClose: () => void
}

// TODO: Validate
export function WhitelistManager({
  channelId,
  showId,
  showName,
  onClose,
}: WhitelistManagerProps) {
  const [isWhitelist, setIsWhitelist] = useState(false)
  // The `Show` ids of the websites' links that carry a filter entry.
  const [enabledSourceIds, setEnabledSourceIds] = useState<Set<string>>(
    new Set(),
  )
  const [enabledSeasonIds, setEnabledSeasonIds] = useState<Set<string>>(
    new Set(),
  )
  // A filter is about the episode rather than one season's listing of it, so the
  // episodes two seasons share are marked by identifier and move together.
  const [enabledEpisodeIdentifiers, setEnabledEpisodeIdentifiers] = useState<
    Set<string>
  >(new Set())
  // Maps an episode identifier to its expiry as a datetime-local input value.
  // Absent = no expiry.
  const [episodeExpiry, setEpisodeExpiry] = useState<Map<string, string>>(
    new Map(),
  )
  const [expandedSeasons, setExpandedSeasons] = useState<Set<string>>(new Set())
  const [sourcesExpanded, setSourcesExpanded] = useState(true)
  const [seasonsExpanded, setSeasonsExpanded] = useState(true)
  // Episode awaiting the expiry popup before being added to the filter.
  const [pendingEpisode, setPendingEpisode] =
    useState<WhitelistEpisodeOutput | null>(null)
  // The record whose information popup is open, if any.
  const [informationEpisodeId, setInformationEpisodeId] = useState<
    string | null
  >(null)
  const [informationShowId, setInformationShowId] = useState<string | null>(
    null,
  )
  // The website's link to an episode whose information is open, if any.
  const [informationLinkEpisodeId, setInformationLinkEpisodeId] = useState<
    string | null
  >(null)

  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const { data: whitelistData, isLoading } = useQuery({
    queryKey: ["channelShowWhitelist", channelId, showId],
    queryFn: () => ChannelsService.getChannelWhitelist({ channelId, showId }),
  })

  useEffect(() => {
    if (whitelistData) {
      setIsWhitelist(whitelistData.is_whitelist ?? false)
      setEnabledSourceIds(
        new Set(
          whitelistData.sources
            .filter((source) => source.filtered)
            .map((source) => source.show_id),
        ),
      )
      setEnabledSeasonIds(
        new Set(
          whitelistData.seasons
            .filter((season) => season.filtered)
            .map((season) => season.id),
        ),
      )
      setEnabledEpisodeIdentifiers(
        new Set(
          whitelistData.episodes
            .filter(
              (episode) => episode.filtered && !isExpired(episode.expires_at),
            )
            .map((episode) => episode.canonical_episode_id),
        ),
      )
      setEpisodeExpiry(
        new Map(
          whitelistData.episodes
            .filter(
              (episode) => episode.expires_at && !isExpired(episode.expires_at),
            )
            .map((episode) => [
              episode.canonical_episode_id,
              isoToLocalInput(episode.expires_at),
            ]),
        ),
      )
    }
  }, [whitelistData])

  const saveMutation = useMutation({
    mutationFn: (input: WhitelistShowInput) =>
      ChannelsService.updateChannelWhitelist({
        channelId,
        showId,
        requestBody: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channelShowWhitelist", channelId, showId],
      })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
      showSuccessToast("Whitelist settings saved successfully")
      onClose()
    },
    onError: handleError.bind(showErrorToast),
  })

  // TODO: Validate
  const toggleIsWhitelist = () => {
    setIsWhitelist(!isWhitelist)
  }

  // TODO: Validate
  const toggleSeasonExpanded = (seasonId: string) => {
    const newExpanded = new Set(expandedSeasons)
    if (newExpanded.has(seasonId)) {
      newExpanded.delete(seasonId)
    } else {
      newExpanded.add(seasonId)
    }
    setExpandedSeasons(newExpanded)
  }

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
  const toggleShowInformation = (sourceShowId: string) => {
    setInformationShowId(
      informationShowId === sourceShowId ? null : sourceShowId,
    )
  }

  // TODO: Validate
  const toggleSourceEnabled = (showId: string) => {
    const newEnabled = new Set(enabledSourceIds)
    if (newEnabled.has(showId)) {
      newEnabled.delete(showId)
    } else {
      newEnabled.add(showId)
    }
    setEnabledSourceIds(newEnabled)
  }

  // TODO: Validate
  const toggleSeasonEnabled = (seasonId: string, enabled: boolean) => {
    const newEnabled = new Set(enabledSeasonIds)
    if (enabled) {
      newEnabled.delete(seasonId)
    } else {
      newEnabled.add(seasonId)
    }
    setEnabledSeasonIds(newEnabled)
  }

  // TODO: Validate
  const toggleEpisodeEnabled = (episodeIdentifier: string) => {
    const newEnabled = new Set(enabledEpisodeIdentifiers)
    if (newEnabled.has(episodeIdentifier)) {
      newEnabled.delete(episodeIdentifier)
    } else {
      newEnabled.add(episodeIdentifier)
    }
    setEnabledEpisodeIdentifiers(newEnabled)
  }

  // TODO: Validate
  const setEpisodeExpiryValue = (episodeIdentifier: string, value: string) => {
    setEpisodeExpiry((previous) => {
      const next = new Map(previous)
      if (value) {
        next.set(episodeIdentifier, value)
      } else {
        next.delete(episodeIdentifier)
      }
      return next
    })
  }

  // Clicking an episode toggles it; removing is immediate, adding first asks for the
  // optional expiry via a popup.
  // TODO: Validate
  const handleEpisodeClick = (episode: WhitelistEpisodeOutput) => {
    if (enabledEpisodeIdentifiers.has(episode.canonical_episode_id)) {
      toggleEpisodeEnabled(episode.canonical_episode_id)
    } else {
      setPendingEpisode(episode)
    }
  }

  // TODO: Validate
  const confirmEpisodeExpiry = (expiresAtLocal: string) => {
    if (!pendingEpisode) return
    setEnabledEpisodeIdentifiers((previous) =>
      new Set(previous).add(pendingEpisode.canonical_episode_id),
    )
    setEpisodeExpiryValue(pendingEpisode.canonical_episode_id, expiresAtLocal)
    setPendingEpisode(null)
  }

  // TODO: Validate
  const handleSave = () => {
    if (!whitelistData) return

    const input: WhitelistShowInput = {
      is_whitelist: isWhitelist,
      sources: whitelistData.sources
        .filter((source) => !source.is_tmdb)
        .map((source) => ({
          id: source.show_id,
          marked: enabledSourceIds.has(source.show_id),
        })),
      seasons: whitelistData.seasons.map((season) => ({
        id: season.id,
        marked: enabledSeasonIds.has(season.id),
      })),
      episodes: whitelistData.episodes.map((episode) => ({
        id: episode.id,
        marked: enabledEpisodeIdentifiers.has(episode.canonical_episode_id),
        expires_at: enabledEpisodeIdentifiers.has(episode.canonical_episode_id)
          ? localInputToIso(
              episodeExpiry.get(episode.canonical_episode_id) ?? "",
            )
          : null,
      })),
    }
    saveMutation.mutate(input)
  }

  // TODO: Validate
  const getEpisodeLabel = (episode: WhitelistEpisodeOutput) => {
    const episodeName = episode.name ?? ""
    const episodeNumber = episode.tmdb_episode_number ?? episode.sort_order
    if (episodeNumber == null) {
      return episodeName
    }
    // A website that never named an episode calls it by its number, which the
    // label already says, so "Episode 3 - Episode 3" is read as "Episode 3".
    const nameIsNumber = NUMBERED_EPISODE_NAME.exec(episodeName)
    const named = episodeName && Number(nameIsNumber?.[1]) !== episodeNumber
    return `Episode ${episodeNumber}${named ? ` - ${episodeName}` : ""}`
  }

  // TODO: Validate
  const getSeasonActionLabel = (enabled: boolean) => {
    if (isWhitelist) {
      return enabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    return enabled ? "Remove from Blacklist" : "Add to Blacklist"
  }

  // A source entry reads the same way a season entry does: in whitelist mode it is
  // one of the sites the show is watched on, in blacklist mode one of the sites it
  // is skipped on.
  const getSourceActionLabel = getSeasonActionLabel

  // TODO: Validate
  const getEpisodeActionLabel = (
    episodeEnabled: boolean,
    seasonEnabled: boolean,
  ) => {
    // When the season itself is filtered, an episode-level entry inverts that filter
    // for the episode (a blacklisted season's marked episode is shown again; a
    // whitelisted season's marked episode is excluded), so the add/remove wording flips.
    if (isWhitelist) {
      if (seasonEnabled) {
        return episodeEnabled ? "Add to Whitelist" : "Remove from Whitelist"
      }
      return episodeEnabled ? "Remove from Whitelist" : "Add to Whitelist"
    }
    if (seasonEnabled) {
      return episodeEnabled ? "Add to Blacklist" : "Remove from Blacklist"
    }
    return episodeEnabled ? "Remove from Blacklist" : "Add to Blacklist"
  }

  if (!whitelistData) return
  const sourcesByShowId = new Map(
    whitelistData.sources.map((source) => [source.show_id, source]),
  )
  // TMDB catalogues the media rather than carrying it, so it never stands for a
  // site an episode can be watched on.
  const tmdbShowIds = new Set(
    whitelistData.sources
      .filter((source) => source.is_tmdb)
      .map((source) => source.show_id),
  )
  // TODO: Validate
  const watchableShowIds = (showIds: string[]) =>
    showIds.filter((showId) => !tmdbShowIds.has(showId))
  // TMDB leads a row the way it leads a season's, since what a row stands for is
  // the media rather than any one site's link to it, and the sites it can be
  // watched on follow the name rather than lead it.
  // TODO: Validate
  const catalogueShowIds = (showIds: string[]) =>
    showIds.filter((showId) => tmdbShowIds.has(showId))
  const watchableSources = whitelistData.sources.filter(
    (source) => !source.is_tmdb,
  )
  const seasonEpisodes = episodesBySeason(whitelistData.episodes)
  const anySeasonHasNumber = whitelistData.seasons.some(
    (season) => season.season_number != null,
  )
  // A season's sites are the ones carrying the episodes under it, since a season
  // can be a shell a site announced and never filled. Who catalogued the season
  // is read off the season itself rather than off its episodes, so a season TMDB
  // has a record of says so whether or not the episodes under it were ever
  // matched to TMDB's.
  // TODO: Validate
  const seasonShowIds = (season: WhitelistSeasonOutput) => [
    ...new Set([
      ...catalogueShowIds(season.show_ids),
      ...(seasonEpisodes.get(season.id) ?? []).flatMap(
        (episode) => episode.show_ids,
      ),
    ]),
  ]
  // The season an episode is under decides how its own entry reads.
  const seasonEnabledByEpisodeId = new Map(
    whitelistData.episodes.map(
      (episode) =>
        [episode.id, enabledSeasonIds.has(episode.season_id)] as const,
    ),
  )

  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">
              Manage Whitelist - {showName}
            </h2>
            <p className="text-sm text-muted-foreground">
              {isWhitelist
                ? "Only selected sites, seasons and episodes will appear. New episodes are not automatically added."
                : "All episodes are shown by default. New episodes are automatically added."}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <ChevronUp className="h-4 w-4 mr-1" /> Collapse
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-2 p-4 border rounded bg-muted/50 shrink-0">
                <div>
                  <h3 className="font-semibold">
                    Current Mode:{" "}
                    {isWhitelist ? "Whitelist Mode" : "Blacklist Mode"}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isWhitelist
                      ? "Only whitelisted episodes will be shown"
                      : "All episodes except blacklisted ones will be shown"}
                  </p>
                </div>
                <Button onClick={toggleIsWhitelist} variant="outline">
                  Switch to {isWhitelist ? "Blacklist" : "Whitelist"} Mode
                </Button>
              </div>

              <div className="border rounded shrink-0">
                <div className="flex items-center gap-2 p-3 bg-accent/50">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setSourcesExpanded(!sourcesExpanded)}
                  >
                    {sourcesExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="flex-1">
                    <h3 className="font-medium">Sources</h3>
                    <p className="text-sm text-muted-foreground">
                      {isWhitelist
                        ? "Only whitelisted sites are watched for this show. Whitelisting none watches them all."
                        : "All sites are watched except blacklisted ones"}
                    </p>
                  </div>
                </div>
                {sourcesExpanded && (
                  <div className="p-2 space-y-1 border-t">
                    {watchableSources.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No sources found for this show
                      </p>
                    ) : (
                      watchableSources.map((source) => {
                        const sourceEnabled = enabledSourceIds.has(
                          source.show_id,
                        )
                        return (
                          <div key={source.show_id}>
                            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() =>
                                  toggleShowInformation(source.show_id)
                                }
                              >
                                {informationShowId === source.show_id ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </Button>
                              {source.favicon_url && (
                                <img
                                  src={source.favicon_url}
                                  alt=""
                                  className="size-6 shrink-0"
                                />
                              )}
                              <button
                                type="button"
                                className="flex-1 text-left text-sm hover:underline"
                                onClick={() =>
                                  toggleShowInformation(source.show_id)
                                }
                              >
                                {source.source_name ?? "Unknown source"}
                              </button>
                              <Button
                                variant={sourceEnabled ? "default" : "outline"}
                                size="sm"
                                onClick={() =>
                                  toggleSourceEnabled(source.show_id)
                                }
                              >
                                {getSourceActionLabel(sourceEnabled)}
                              </Button>
                            </div>
                            {informationShowId === source.show_id && (
                              <div className="rounded border bg-muted/30 p-4">
                                <ShowInformationPanel showId={source.show_id} />
                              </div>
                            )}
                          </div>
                        )
                      })
                    )}
                  </div>
                )}
              </div>

              <div className="border rounded shrink-0">
                <div className="flex items-center gap-2 p-3 bg-accent/50">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setSeasonsExpanded(!seasonsExpanded)}
                  >
                    {seasonsExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </Button>
                  <div className="flex-1">
                    <h3 className="font-medium">Seasons</h3>
                    <p className="text-sm text-muted-foreground">
                      {isWhitelist
                        ? "Only whitelisted seasons and episodes will appear"
                        : "All seasons are shown except blacklisted ones"}
                    </p>
                  </div>
                </div>
                {seasonsExpanded && (
                  <div className="p-2 space-y-1 border-t">
                    {whitelistData.seasons.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No seasons found for this show
                      </p>
                    ) : (
                      whitelistData.seasons.map((season) => {
                        const episodes = seasonEpisodes.get(season.id) ?? []
                        const seasonEnabled = enabledSeasonIds.has(season.id)
                        const rowShowIds = seasonShowIds(season)
                        const tmdbRowShowIds = rowShowIds.filter((showId) =>
                          tmdbShowIds.has(showId),
                        )
                        // TMDB leads the row, and the sites stand in front of the
                        // name only when TMDB has no record of the season to lead it.
                        const leadingShowIds =
                          tmdbRowShowIds.length > 0
                            ? tmdbRowShowIds
                            : rowShowIds
                        const trailingShowIds =
                          tmdbRowShowIds.length > 0
                            ? rowShowIds.filter(
                                (showId) => !tmdbShowIds.has(showId),
                              )
                            : []
                        return (
                          <div key={season.id}>
                            <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => toggleSeasonExpanded(season.id)}
                              >
                                {expandedSeasons.has(season.id) ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                              </Button>
                              {leadingShowIds.length > 0 && (
                                <SourceFavicons
                                  showIds={leadingShowIds}
                                  sourcesByShowId={sourcesByShowId}
                                />
                              )}
                              <button
                                type="button"
                                className="flex-1 text-left text-sm hover:underline"
                                onClick={() => toggleSeasonExpanded(season.id)}
                              >
                                {seasonLabel(season, anySeasonHasNumber)}
                              </button>
                              {trailingShowIds.length > 0 && (
                                <SourceFavicons
                                  showIds={trailingShowIds}
                                  sourcesByShowId={sourcesByShowId}
                                />
                              )}
                              <Button
                                variant={seasonEnabled ? "default" : "outline"}
                                size="sm"
                                onClick={() =>
                                  toggleSeasonEnabled(season.id, seasonEnabled)
                                }
                              >
                                {getSeasonActionLabel(seasonEnabled)}
                              </Button>
                            </div>

                            {expandedSeasons.has(season.id) && (
                              <div className="p-2 space-y-1">
                                {episodes.length === 0 ? (
                                  <p className="text-sm text-muted-foreground text-center py-2">
                                    No episodes found
                                  </p>
                                ) : (
                                  episodes.map((episode) => {
                                    const episodeEnabled =
                                      enabledEpisodeIdentifiers.has(
                                        episode.canonical_episode_id,
                                      )
                                    const episodeTmdbShowIds = catalogueShowIds(
                                      episode.show_ids,
                                    )
                                    return (
                                      <div key={episode.id}>
                                        <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                                          <Button
                                            className="ml-8"
                                            variant="ghost"
                                            size="icon-sm"
                                            onClick={() =>
                                              toggleEpisodeInformation(
                                                episode.id,
                                              )
                                            }
                                          >
                                            {informationEpisodeId ===
                                            episode.id ? (
                                              <ChevronDown className="h-4 w-4" />
                                            ) : (
                                              <ChevronRight className="h-4 w-4" />
                                            )}
                                          </Button>
                                          <span className="flex items-center">
                                            {episodeTmdbShowIds.length > 0 && (
                                              <SourceFavicons
                                                showIds={episodeTmdbShowIds}
                                                sourcesByShowId={
                                                  sourcesByShowId
                                                }
                                              />
                                            )}
                                          </span>
                                          <button
                                            type="button"
                                            className="flex-1 text-left text-sm hover:underline"
                                            onClick={() =>
                                              toggleEpisodeInformation(
                                                episode.id,
                                              )
                                            }
                                          >
                                            {getEpisodeLabel(episode)}
                                            {episodeEnabled &&
                                              episodeExpiry.get(
                                                episode.canonical_episode_id,
                                              ) && (
                                                <span className="ml-2 text-xs text-muted-foreground">
                                                  (until{" "}
                                                  {new Date(
                                                    episodeExpiry.get(
                                                      episode.canonical_episode_id,
                                                    )!,
                                                  ).toLocaleString()}
                                                  )
                                                </span>
                                              )}
                                          </button>
                                          <SourceFavicons
                                            showIds={watchableShowIds(
                                              episode.show_ids,
                                            )}
                                            sourcesByShowId={sourcesByShowId}
                                          />
                                          <Button
                                            variant={
                                              episodeEnabled !== seasonEnabled
                                                ? "default"
                                                : "outline"
                                            }
                                            size="sm"
                                            onClick={() =>
                                              handleEpisodeClick(episode)
                                            }
                                          >
                                            {getEpisodeActionLabel(
                                              episodeEnabled,
                                              seasonEnabled,
                                            )}
                                          </Button>
                                        </div>
                                        {informationEpisodeId ===
                                          episode.id && (
                                          <div className="ml-16 space-y-1">
                                            {episode.links.map((link) => {
                                              const linkSource =
                                                sourcesByShowId.get(
                                                  link.show_id,
                                                )
                                              return (
                                                <div key={link.episode_id}>
                                                  <div className="flex items-center gap-2 p-2 hover:bg-accent/30 rounded">
                                                    <Button
                                                      variant="ghost"
                                                      size="icon-sm"
                                                      onClick={() =>
                                                        toggleLinkInformation(
                                                          link.episode_id,
                                                        )
                                                      }
                                                    >
                                                      {informationLinkEpisodeId ===
                                                      link.episode_id ? (
                                                        <ChevronDown className="h-4 w-4" />
                                                      ) : (
                                                        <ChevronRight className="h-4 w-4" />
                                                      )}
                                                    </Button>
                                                    {linkSource?.favicon_url && (
                                                      <img
                                                        src={
                                                          linkSource.favicon_url
                                                        }
                                                        alt=""
                                                        className="size-6 shrink-0"
                                                      />
                                                    )}
                                                    <button
                                                      type="button"
                                                      className="flex-1 text-left text-sm hover:underline"
                                                      onClick={() =>
                                                        toggleLinkInformation(
                                                          link.episode_id,
                                                        )
                                                      }
                                                    >
                                                      {linkSource?.source_name ??
                                                        "Unknown source"}
                                                    </button>
                                                  </div>
                                                  {informationLinkEpisodeId ===
                                                    link.episode_id && (
                                                    <div className="ml-8 rounded border bg-muted/30 p-4">
                                                      <EpisodeInformationPanel
                                                        episodeId={
                                                          link.episode_id
                                                        }
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
                                  })
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={onClose}
                disabled={saveMutation.isPending}
              >
                Cancel
              </Button>
              <LoadingButton
                onClick={handleSave}
                loading={saveMutation.isPending}
              >
                Save Changes
              </LoadingButton>
            </div>
          </>
        )}
      </div>

      {pendingEpisode && (
        <EpisodeExpiryDialog
          open={!!pendingEpisode}
          // The popup only opens when adding an episode-level entry, so the action
          // matches the not-yet-enabled label (which already accounts for the season).
          title={getEpisodeActionLabel(
            false,
            seasonEnabledByEpisodeId.get(pendingEpisode.id) ?? false,
          )}
          description={getEpisodeLabel(pendingEpisode)}
          dateLabel="Expires at (optional)"
          confirmLabel={getEpisodeActionLabel(
            false,
            seasonEnabledByEpisodeId.get(pendingEpisode.id) ?? false,
          )}
          initialExpiry={
            episodeExpiry.get(pendingEpisode.canonical_episode_id) ?? ""
          }
          onConfirm={confirmEpisodeExpiry}
          onOpenChange={(open) => {
            if (!open) setPendingEpisode(null)
          }}
        />
      )}
    </>
  )
}
