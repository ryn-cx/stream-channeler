// TODO: Validate
import { Pencil } from "lucide-react"
import { useState } from "react"

import {
  EpisodeInformationHero,
  episodeInformationQueryKey,
  useEpisodeInformation,
} from "@/components/ChannelCommon/EpisodeInformationHero"
import { EpisodeUserUrlSection } from "@/components/ChannelCommon/EpisodeUserUrlSection"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"
import { AdminZone } from "@/components/Common/AdminZone"
import { ModalContent } from "@/components/Common/ModalContent"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import EditTitle from "@/components/Titles/Edit"
import { TMDB_EPISODE_ORDER_PLUGIN } from "@/components/Titles/TmdbEpisodeOrderField"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import useAuth from "@/hooks/useAuth"
import { useTitle } from "@/hooks/useEntities"
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

// TODO: Validate
const EditTitleOfEpisode = ({ titleId }: { titleId: string }) => {
  const { data: title } = useTitle(titleId)
  if (!title) return null
  return <EditTitle title={title} size="icon-sm" />
}

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
  const isAdmin = Boolean(user?.is_superuser)
  const information = useEpisodeInformation(episode.id, enabled)
  const informationQueryKey = episodeInformationQueryKey(episode.id)
  const titleId = information.data?.source.title.id
  // TMDB's own rows are the episodes every website's row is settled against, so
  // there is nothing above them to link them to.
  const isTmdbEpisode =
    information.data?.source.source.plugin_name === TMDB_EPISODE_ORDER_PLUGIN
  const [tmdbEpisodeIds, setTmdbEpisodeIds] = useState(
    episode.tmdb_episode_ids ?? [],
  )

  const [tmdbEpisodeValidatedAt, setTmdbEpisodeValidatedAt] = useState(
    episode.tmdb_episode_validated_at?.slice(0, 16) ?? "",
  )
  const [tmdbEpisodeNote, setTmdbEpisodeNote] = useState(
    episode.tmdb_episode_note ?? "",
  )

  return (
    <div className="flex flex-col gap-6">
      <EpisodeInformationHero
        episodeId={episode.id}
        enabled={enabled}
        preferSource
        spelledOutDuration
        titleAction={
          isAdmin && titleId ? <EditTitleOfEpisode titleId={titleId} /> : null
        }
      />

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
          onLinksChanged={(linked) =>
            setTmdbEpisodeIds(linked.tmdb_episode_ids ?? [])
          }
        />
      )}

      {isAdmin ? (
        <AdminZone>
          {!isTmdbEpisode ? (
            <TmdbEpisodeControls
              episodeId={episode.id}
              seasonNumber={null}
              episodeNumber={episode.episode_number ?? null}
              tmdbEpisodeValidatedAt={tmdbEpisodeValidatedAt}
              tmdbEpisodeNote={tmdbEpisodeNote}
              hasLinks={tmdbEpisodeIds.length > 0}
              enabled={enabled}
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
          ) : null}
          <EpisodeDatabaseDetails episodeId={episode.id} enabled={enabled} />
        </AdminZone>
      ) : null}

      {information.data ? (
        <IssueReportsSection
          target="episode"
          mediaId={episode.id}
          reports={information.data.issue_reports}
          informationQueryKey={informationQueryKey}
        />
      ) : null}
    </div>
  )
}

interface EditEpisodeProps {
  episode: Pick<EditableEpisodeFields, "id"> & Partial<EditableEpisodeFields>
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// TODO: Validate
/** The same reading of an episode, in a window of its own. */
const EditEpisode = ({ episode, open, onOpenChange }: EditEpisodeProps) => {
  const [isOpenHere, setIsOpenHere] = useState(false)
  const isOpen = open ?? isOpenHere
  const setIsOpen = onOpenChange ?? setIsOpenHere

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {open === undefined ? (
        <TooltipIconButton
          label="Episode Information"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      ) : null}
      <ModalContent size="3xl" className="overflow-y-hidden">
        <DialogHeader>
          <DialogTitle>Episode Information</DialogTitle>
          <DialogDescription>
            What the website and TMDB each say about this episode, and which
            episodes the row stands for.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="max-h-none min-h-0 flex-1">
          <div className="py-4">
            <EpisodeInformationContent episode={episode} enabled={isOpen} />
          </div>
        </DialogBody>
      </ModalContent>
    </Dialog>
  )
}

export default EditEpisode
