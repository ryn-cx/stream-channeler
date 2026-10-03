// TODO: Validate
import { useMutation, useQueries, useQueryClient } from "@tanstack/react-query"
import { Unlink } from "lucide-react"
import { useState } from "react"

import { type TitlePublic, TitlesService, TmdbTitlesService } from "@/client"
import { CollapsibleSection } from "@/components/ChannelCommon/CollapsibleSection"
import { ReportIssueForm } from "@/components/ChannelCommon/ReportIssueForm"
import { ResultCard } from "@/components/Channels/ChannelDetail/Search"
import { AdminZone } from "@/components/Common/AdminZone"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { useOpenMedia } from "@/hooks/useOpenMedia"
import { handleError } from "@/utils"
import { ForceRelinkTitleButton } from "./ForceRelinkTitleButton"
import { ForceUpdateTitleButton } from "./ForceUpdateTitleButton"
import { LinkedTitleField } from "./LinkedTitleField"
import { LinkedTitleLinks } from "./LinkedTitleLinks"
import { MarkTitleAbsentButton } from "./MarkTitleAbsentButton"
import { TmdbTitleField } from "./TmdbTitleField"

// TODO: Validate
/**
 * The canonical titles this row stands for, read by anybody.
 *
 * Each is read as the card the searches offer it as, and opens into everything
 * that title is, which is the same reading the row itself is given.
 */
function TmdbTitleReadOnlyList({
  titleId,
  tmdbTitleIds,
  enabled,
  editable,
}: {
  titleId: string
  tmdbTitleIds: string[]
  enabled: boolean
  editable: boolean
}) {
  const openMedia = useOpenMedia()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const unlinkMutation = useMutation({
    mutationFn: (tmdbTitleId: string) =>
      TitlesService.adminUnlinkTitleFromTmdb({ titleId, tmdbTitleId }),
    onSuccess: () => {
      showSuccessToast("Title unlinked from tmdb title")
      queryClient.invalidateQueries({ queryKey: ["titles"] })
      queryClient.invalidateQueries({ queryKey: ["title-information"] })
      queryClient.invalidateQueries({ queryKey: ["tmdb-title"] })
    },
    onError: (error: unknown) =>
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      ),
  })
  const linkedQueries = useQueries({
    queries: tmdbTitleIds.map((tmdbTitleId) => ({
      queryKey: ["tmdb-title", tmdbTitleId],
      queryFn: () => TmdbTitlesService.getTmdbTitleById({ tmdbTitleId }),
      enabled,
    })),
  })
  const linked = linkedQueries
    .map((query) => query.data)
    .filter((title) => title !== undefined)

  if (tmdbTitleIds.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">Linked to no tmdb title.</p>
    )
  }

  return (
    <div className="flex flex-wrap gap-3">
      {tmdbTitleIds.map((tmdbTitleId) => {
        const title = linked.find((each) => each.id === tmdbTitleId)
        if (!title) {
          return (
            <p key={tmdbTitleId} className="text-sm text-muted-foreground">
              Reading the linked title…
            </p>
          )
        }
        return (
          <ResultCard
            key={tmdbTitleId}
            imageUrl={title.poster_thumbnail_url ?? title.poster_url}
            title={
              title.year
                ? `${title.name ?? "Unnamed"} (${title.year})`
                : (title.name ?? "Unnamed")
            }
            subtitle={title.media_type}
            onClick={() => openMedia({ kind: "title", titleId: tmdbTitleId })}
            footer={
              editable ? (
                <TooltipIconButton
                  label="Unlink Title"
                  icon={<Unlink />}
                  className="bg-blue-900 text-white hover:bg-blue-900/90 dark:bg-blue-500/60 dark:hover:bg-blue-500/50"
                  disabled={unlinkMutation.isPending}
                  onClick={() => unlinkMutation.mutate(tmdbTitleId)}
                />
              ) : null
            }
          />
        )
      })}
    </div>
  )
}

interface TitleTmdbSectionProps {
  title: TitlePublic
  /** Whether the links are wanted yet, so a collapsed panel fetches nothing. */
  enabled?: boolean
}

// TODO: Validate
/**
 * Which canonical titles a website's row stands for, read beside the row itself.
 *
 * Everybody is shown what the row stands for, since that is as much a part of it
 * as its name. An admin is given the settling of those links, marked out as
 * theirs rather than mixed in among what everybody sees.
 */
export function TitleTmdbSection({
  title,
  enabled = true,
}: TitleTmdbSectionProps) {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_superuser)
  const isTmdbTitle = title.plugin_name === "TMDB"
  const tmdbTitleIds = title.tmdb_title_ids ?? []
  const [suggesting, setSuggesting] = useState(false)
  const canSuggest = !isAdmin && !isTmdbTitle && tmdbTitleIds.length === 0

  return (
    <CollapsibleSection title="TMDB Titles" defaultOpen>
      {isTmdbTitle ? (
        <LinkedTitleLinks titleId={title.id} enabled={enabled} />
      ) : (
        <TmdbTitleReadOnlyList
          titleId={title.id}
          tmdbTitleIds={tmdbTitleIds}
          enabled={enabled}
          editable={isAdmin}
        />
      )}
      {canSuggest ? (
        <div className="mt-3 space-y-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSuggesting(!suggesting)}
          >
            Suggest a TMDB Match
          </Button>
          {suggesting ? (
            <ReportIssueForm
              sources={[{ titleId: title.id, label: title.name ?? title.key }]}
              fixedProblem="wrong-title"
              onSent={() => setSuggesting(false)}
            />
          ) : null}
        </div>
      ) : null}
      {isAdmin ? (
        <AdminZone className="mt-3">
          {isTmdbTitle ? (
            <LinkedTitleField titleId={title.id} />
          ) : (
            <>
              <TmdbTitleField
                titleId={title.id}
                tmdbTitleIds={tmdbTitleIds}
                enabled={enabled}
              />
              <MarkTitleAbsentButton
                titleId={title.id}
                titleName={title.name}
              />
              <p className="text-sm text-muted-foreground">
                {title.tmdb_absent_at
                  ? "This title is already settled as one TMDB has no record of."
                  : "Drops every canonical title this stands for and settles it as one TMDB has no record of, so no later import links it again."}
              </p>
            </>
          )}
          <div className="flex flex-wrap gap-2">
            <ForceUpdateTitleButton titleId={title.id} />
            {!isTmdbTitle && <ForceRelinkTitleButton titleId={title.id} />}
          </div>
        </AdminZone>
      ) : null}
    </CollapsibleSection>
  )
}
