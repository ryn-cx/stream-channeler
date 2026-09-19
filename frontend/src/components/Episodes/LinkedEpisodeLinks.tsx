// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "@tanstack/react-router"
import { ChevronDown, ChevronRight, Pencil, Unlink } from "lucide-react"
import { useState } from "react"

import type { EpisodeListOutput } from "@/client"
import { EpisodesService } from "@/client"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import EditEpisode from "./Edit"
import { EpisodeDatabaseDetails } from "./EpisodeDatabaseDetails"

// TODO: Validate
function SourceFavicon({ episode }: { episode: EpisodeListOutput }) {
  const name = episode.source_key ?? episode.plugin_name ?? episode.key
  const icon = episode.source_favicon_url ? (
    <img
      referrerPolicy="no-referrer"
      src={episode.source_favicon_url}
      alt={`${name} favicon`}
      className="size-8 shrink-0 rounded"
    />
  ) : (
    <span className="text-sm font-medium uppercase">{name.slice(0, 2)}</span>
  )

  if (!episode.url) {
    return (
      <span className="-my-2 flex w-12 shrink-0 items-center justify-center self-stretch text-muted-foreground">
        {icon}
      </span>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <a
          href={episode.url}
          target="_blank"
          rel="noopener noreferrer"
          className="-my-2 flex w-12 shrink-0 items-center justify-center self-stretch rounded-md transition-colors hover:bg-accent"
        >
          {icon}
          <span className="sr-only">{`Open on ${name}`}</span>
        </a>
      </TooltipTrigger>
      <TooltipContent>{`Open on ${name}`}</TooltipContent>
    </Tooltip>
  )
}

// TODO: Validate
function MediaPageLinks({ episode }: { episode: EpisodeListOutput }) {
  return (
    <div className="flex shrink-0 flex-wrap gap-1 self-center">
      <Button variant="destructive" size="sm" asChild>
        <Link to="/episodes" search={{ season_id: episode.season_id }}>
          Episode
        </Link>
      </Button>
      <Button variant="destructive" size="sm" asChild>
        <Link to="/seasons" search={{ title_id: episode.title_id }}>
          Season
        </Link>
      </Button>
      <Button variant="destructive" size="sm" asChild>
        <Link to="/titles" search={{ source_id: episode.source_id }}>
          Title
        </Link>
      </Button>
      <Button variant="destructive" size="sm" asChild>
        <Link to="/sources" search={{ plugin_id: episode.plugin_id }}>
          Source
        </Link>
      </Button>
    </div>
  )
}

// TODO: Validate
function seasonText(episode: EpisodeListOutput) {
  const numbered =
    episode.season_number == null ? null : `Season ${episode.season_number}`
  if (!episode.season_name) return numbered
  if (!numbered) return episode.season_name
  return `${episode.season_name} (${numbered})`
}

interface LinkedEpisodeRowProps {
  episode: EpisodeListOutput
  isAdmin: boolean
  unlinking: boolean
  onUnlink: () => void
}

// TODO: Validate
function LinkedEpisodeRow({
  episode,
  isAdmin,
  unlinking,
  onUnlink,
}: LinkedEpisodeRowProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="border-b text-sm last:border-b-0">
      <div className="flex items-stretch gap-3 px-3 py-2">
        <button
          type="button"
          aria-expanded={isExpanded}
          aria-label="Show the database columns"
          className="-my-2 flex shrink-0 items-center self-stretch text-muted-foreground hover:text-foreground"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
        </button>
        <SourceFavicon episode={episode} />
        <button
          type="button"
          aria-expanded={isExpanded}
          className="flex flex-1 items-center gap-2 self-center text-left hover:underline"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <span className="flex-1 whitespace-normal wrap-break-word">
            {episode.episode_number == null
              ? (episode.name ?? "Unnamed")
              : `${episode.episode_number}. ${episode.name ?? "Unnamed"}`}
            {seasonText(episode) ? (
              <span className="block text-xs text-muted-foreground">
                {seasonText(episode)}
              </span>
            ) : null}
            {episode.title_name ? (
              <span className="block text-xs text-muted-foreground">
                {episode.title_name}
              </span>
            ) : null}
          </span>
        </button>
        {isAdmin ? <MediaPageLinks episode={episode} /> : null}
        <TooltipIconButton
          label="Episode Information"
          icon={<Pencil />}
          className="self-center"
          onClick={() => setIsEditing(true)}
        />
        <EditEpisode
          episode={episode}
          open={isEditing}
          onOpenChange={setIsEditing}
        />
        {isAdmin ? (
          <TooltipIconButton
            label="Unlink Episode"
            icon={<Unlink />}
            variant="destructive"
            className="self-center bg-destructive dark:bg-destructive/60"
            disabled={unlinking}
            onClick={onUnlink}
          />
        ) : null}
      </div>
      {isExpanded ? (
        <div className="border-t px-3 py-3">
          <EpisodeDatabaseDetails episodeId={episode.id} enabled />
        </div>
      ) : null}
    </div>
  )
}

interface LinkedEpisodeLinksProps {
  episodeId: string
  enabled: boolean
}

// TODO: Validate
/**
 * Every website's row standing for this episode.
 *
 * The question a tmdb episode is opened with is the other way around from
 * the one a website's row is opened with: a row is settled by choosing which
 * episode it is of, and an episode is read by seeing which rows came to it.
 */
export function LinkedEpisodeLinks({
  episodeId,
  enabled,
}: LinkedEpisodeLinksProps) {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_superuser)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const { data: episodes, isLoading } = useQuery({
    queryKey: ["episodes", episodeId, "linked"],
    queryFn: () => EpisodesService.getLinkedEpisodes({ episodeId }),
    enabled,
  })

  const unlinkMutation = useMutation({
    mutationFn: (droppedId: string) =>
      EpisodesService.adminUnlinkEpisodeFromTmdbEpisode({
        episodeId: droppedId,
        tmdbEpisodeId: episodeId,
      }),
    onSuccess: () => {
      showSuccessToast("Episode unlinked from this episode")
      queryClient.invalidateQueries({ queryKey: ["episodes"] })
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
      queryClient.invalidateQueries({
        queryKey: ["admin-duplicated-tmdb-episodes"],
      })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })

  if (isLoading) {
    return (
      <p className="text-sm text-muted-foreground">
        Reading the linked episodes…
      </p>
    )
  }

  return (
    <div className="space-y-2">
      <Label>Linked Episodes</Label>
      {!episodes || episodes.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No episode is linked to this one.
        </p>
      ) : (
        <div className="rounded-lg border">
          {episodes.map((linked) => (
            <LinkedEpisodeRow
              key={linked.id}
              episode={linked}
              isAdmin={isAdmin}
              unlinking={unlinkMutation.isPending}
              onUnlink={() => unlinkMutation.mutate(linked.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
