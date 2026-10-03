// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import {
  EpisodeInformationHero,
  episodeInformationQueryKey,
  useEpisodeInformation,
} from "@/components/ChannelCommon/EpisodeInformationHero"
import { EpisodeUserUrlSection } from "@/components/ChannelCommon/EpisodeUserUrlSection"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"
import { AdminZone } from "@/components/Common/AdminZone"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { EpisodeWatchHistory } from "@/components/Watches/EpisodeWatchHistory"
import useAuth from "@/hooks/useAuth"
import { useOpenMedia } from "@/hooks/useOpenMedia"
import type { EpisodeTableData } from "./columns"
import { EpisodeDatabaseDetails } from "./EpisodeDatabaseDetails"
import { LinkedEpisodeLinks } from "./LinkedEpisodeLinks"
import { TmdbEpisodeControls, TmdbEpisodeList } from "./TmdbEpisodeField"

export type EditableEpisodeFields = Pick<
  EpisodeTableData,
  | "id"
  | "tmdb_episode_ids"
  | "episode_number"
  | "tmdb_episode_validated_at"
  | "tmdb_episode_note"
>

const VERIFIED_NOTE = "Manual: Verified"

interface EpisodeInformationContentProps {
  episode: Pick<EditableEpisodeFields, "id"> & Partial<EditableEpisodeFields>
  /** Whether the episode is wanted yet, so a collapsed reading fetches nothing. */
  enabled: boolean
}

// TODO: Validate
/**
 * Everything one episode is, read in whatever is already open.
 *
 * Read by anybody: what the episode is, where each side puts it, which episodes
 * it stands for, and what has been reported about it. An admin is given the
 * settling of those links and the row's own columns below them, marked out as
 * theirs rather than mixed in among what everybody sees.
 */
export function EpisodeInformationContent({
  episode,
  enabled,
}: EpisodeInformationContentProps) {
  const { user } = useAuth()
  const openMedia = useOpenMedia()
  const isAdmin = Boolean(user?.is_superuser)
  const information = useEpisodeInformation(episode.id, enabled)
  const informationQueryKey = episodeInformationQueryKey(episode.id)
  // TMDB's own rows are the episodes every website's row is settled against, so
  // there is nothing above them to link them to.
  const isTmdbEpisode = information.data?.source.source.plugin_name === "TMDB"
  const [tmdbEpisodeIds, setTmdbEpisodeIds] = useState(
    episode.tmdb_episode_ids ?? [],
  )

  const [tmdbEpisodeValidatedAt, setTmdbEpisodeValidatedAt] = useState(
    episode.tmdb_episode_validated_at?.slice(0, 16) ?? "",
  )
  const [tmdbEpisodeNote, setTmdbEpisodeNote] = useState(
    episode.tmdb_episode_note ?? "",
  )
  const [unignored, setUnignored] = useState(false)
  const ignored =
    !unignored && Boolean(information.data?.source.episode.ignored_at)

  return (
    <div className="flex flex-col gap-6">
      <EpisodeInformationHero
        episodeId={episode.id}
        enabled={enabled}
        spelledOutDuration
        onOpenTitle={(titleId) => openMedia({ kind: "title", titleId })}
      />

      <EpisodeWatchHistory episodeId={episode.id} enabled={enabled} />

      {information.data ? (
        <EpisodeUserUrlSection
          episodeId={episode.id}
          userUrl={information.data.user_url}
          informationQueryKey={informationQueryKey}
        />
      ) : null}

      {isTmdbEpisode ? (
        <LinkedEpisodeLinks episodeId={episode.id} enabled={enabled} />
      ) : (
        <TmdbEpisodeList
          episodeId={episode.id}
          tmdbEpisodeIds={tmdbEpisodeIds}
          enabled={enabled}
          editable={isAdmin}
          ignored={ignored}
          onLinksChanged={(linked) =>
            setTmdbEpisodeIds(linked.tmdb_episode_ids ?? [])
          }
        />
      )}

      {isAdmin && !isTmdbEpisode ? (
        <AdminZone>
          <TmdbEpisodeControls
            episodeId={episode.id}
            seasonNumber={null}
            episodeNumber={episode.episode_number ?? null}
            tmdbEpisodeValidatedAt={tmdbEpisodeValidatedAt}
            tmdbEpisodeNote={tmdbEpisodeNote}
            hasLinks={tmdbEpisodeIds.length > 0}
            enabled={enabled}
            ignored={ignored}
            onUnignored={() => setUnignored(true)}
            onVerified={() => {
              setTmdbEpisodeValidatedAt(new Date().toISOString().slice(0, 16))
              setTmdbEpisodeNote(VERIFIED_NOTE)
            }}
            onLinksChanged={(linked) => {
              setTmdbEpisodeIds(linked.tmdb_episode_ids ?? [])
              setTmdbEpisodeValidatedAt(
                linked.tmdb_episode_validated_at?.slice(0, 16) ?? "",
              )
              setTmdbEpisodeNote(linked.tmdb_episode_note ?? "")
            }}
          />
        </AdminZone>
      ) : null}

      <CollapsibleSection title="Database">
        <EpisodeDatabaseDetails episodeId={episode.id} enabled={enabled} />
      </CollapsibleSection>

      {information.data ? (
        <CollapsibleSection
          title={`Reported Issues (${information.data.issue_reports.length})`}
          defaultOpen={information.data.issue_reports.length > 0}
        >
          <IssueReportsSection
            target="episode"
            mediaId={episode.id}
            reports={information.data.issue_reports}
            informationQueryKey={informationQueryKey}
            showHeading={false}
          />
        </CollapsibleSection>
      ) : null}
    </div>
  )
}

interface EditEpisodeProps {
  episode: Pick<EditableEpisodeFields, "id"> & Partial<EditableEpisodeFields>
}

// TODO: Validate
const EditEpisode = ({ episode }: EditEpisodeProps) => {
  const openMedia = useOpenMedia()
  return (
    <TooltipIconButton
      label="Episode Information"
      icon={<Pencil />}
      onClick={() => openMedia({ kind: "episode", episode })}
    />
  )
}

export default EditEpisode
