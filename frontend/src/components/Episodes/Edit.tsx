// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { EpisodesService, type EpisodeUpdate } from "@/client"
import {
  EpisodeInformationHero,
  episodeInformationQueryKey,
  useEpisodeInformation,
} from "@/components/ChannelCommon/EpisodeInformationHero"
import { EpisodeUserUrlSection } from "@/components/ChannelCommon/EpisodeUserUrlSection"
import { IssueReportsSection } from "@/components/ChannelCommon/IssueReportsSection"
import { AdminZone } from "@/components/Common/AdminZone"
import { FormTextField } from "@/components/Common/FormTextField"
import { ModalContent } from "@/components/Common/ModalContent"
import { ModalFooter } from "@/components/Common/ModalFooter"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import EditShow from "@/components/Shows/Edit"
import { TMDB_EPISODE_ORDER_PLUGIN } from "@/components/Shows/TmdbEpisodeOrderField"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Form } from "@/components/ui/form"
import { LoadingButton } from "@/components/ui/loading-button"
import useAuth from "@/hooks/useAuth"
import { useShow } from "@/hooks/useEntities"
import { extraText, parseExtraText } from "@/lib/extra"
import {
  nullifyBlanks,
  optionalInt,
  optionalNonNegativeInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"

import {
  CanonicalEpisodeControls,
  CanonicalEpisodeList,
} from "./CanonicalEpisodeField"
import type { EpisodeTableData } from "./columns"
import { NonCanonicalEpisodeLinks } from "./NonCanonicalEpisodeLinks"

/** What the form reads, so any row carrying these can be edited. */
export type EditableEpisodeFields = Pick<
  EpisodeTableData,
  | "id"
  | "canonical_episode_ids"
  | "key"
  | "name"
  | "url"
  | "description"
  | "image_url"
  | "air_date"
  | "episode_number"
  | "duration"
  | "sort_order"
  | "canonical_episode_validated_at"
  | "canonical_episode_note"
  | "data_timestamp"
  | "update_at"
  | "deleted_at"
  | "extra"
>

const formSchema = z.object({
  canonical_episode_validated_at: optionalString,
  canonical_episode_note: optionalString,
  deleted_at: optionalString,
  extra: optionalString,
  name: optionalString,
  episode_number: optionalInt,
  url: optionalString,
  description: optionalString,
  image_url: optionalString,
  air_date: optionalString,
  duration: optionalNonNegativeInt,
  sort_order: optionalInt,
  data_timestamp: optionalString,
  update_at: optionalString,
  key: requiredKey,
})

const VERIFIED_NOTE = "Manual: Verified"

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

// TODO: Validate
const EditShowOfEpisode = ({ showId }: { showId: string }) => {
  const { data: show } = useShow(showId)
  if (!show) return null
  return <EditShow show={show} size="icon-sm" />
}

interface EpisodeInformationContentProps {
  /**
   * The row being read. Only the id is asked for, since a reader who may not
   * edit is never served the row's own columns and there is nothing to fill a
   * form with.
   */
  episode: Pick<EditableEpisodeFields, "id"> & Partial<EditableEpisodeFields>
  /** Whether the episode is wanted yet, so a collapsed reading fetches nothing. */
  enabled: boolean
  /** Called once the row's own columns have been written. */
  onSaved?: () => void
  /** Whether there is a window around this for a Cancel to close. */
  withCancel?: boolean
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
  onSaved,
  withCancel = false,
}: EpisodeInformationContentProps) {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_superuser)
  const information = useEpisodeInformation(episode.id, enabled)
  const informationQueryKey = episodeInformationQueryKey(episode.id)
  const showId = information.data?.source.show.id
  // TMDB's own rows are the episodes every website's row is settled against, so
  // there is nothing above them to link them to.
  const isTmdbEpisode =
    information.data?.source.source.plugin_name === TMDB_EPISODE_ORDER_PLUGIN
  const [canonicalEpisodeIds, setCanonicalEpisodeIds] = useState(
    episode.canonical_episode_ids ?? [],
  )

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      canonical_episode_validated_at:
        episode.canonical_episode_validated_at?.slice(0, 16) ?? "",
      canonical_episode_note: episode.canonical_episode_note ?? "",
      deleted_at: episode.deleted_at?.slice(0, 16) ?? "",
      extra: extraText(episode.extra),
      name: episode.name ?? "",
      episode_number: episode.episode_number ?? "",
      url: episode.url ?? "",
      description: episode.description ?? "",
      image_url: episode.image_url ?? "",
      air_date: episode.air_date ?? "",
      duration: episode.duration ?? "",
      sort_order: episode.sort_order ?? "",
      data_timestamp: episode.data_timestamp?.slice(0, 16) ?? "",
      update_at: episode.update_at?.slice(0, 16) ?? "",
      key: episode.key ?? "",
    },
  })

  const mutation = useEditTableRow<EpisodeUpdate>({
    mutationFn: (data) =>
      EpisodesService.updateEpisode({
        episodeId: episode.id,
        requestBody: data,
      }),
    rowId: episode.id,
    successMessage: "Episode updated successfully",
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    onSaved?.()
    mutation.mutate({
      ...nullifyBlanks(data),
      extra: parseExtraText(data.extra ?? ""),
    })
  }

  return (
    <div className="flex flex-col gap-6">
      <EpisodeInformationHero
        episodeId={episode.id}
        enabled={enabled}
        spelledOutDuration
        titleAction={
          isAdmin && showId ? <EditShowOfEpisode showId={showId} /> : null
        }
      />

      {information.data ? (
        <EpisodeUserUrlSection
          episodeId={episode.id}
          userUrl={information.data.user_url}
          informationQueryKey={informationQueryKey}
        />
      ) : null}

      {/*
              A canonical episode is asked the question the other way around: it
              stands for nothing itself, and what is worth reading on it is the
              website rows that came to it.
            */}
      {isTmdbEpisode ? (
        <NonCanonicalEpisodeLinks episodeId={episode.id} enabled={enabled} />
      ) : (
        <CanonicalEpisodeList
          episodeId={episode.id}
          canonicalEpisodeIds={canonicalEpisodeIds}
          enabled={enabled}
          editable={isAdmin}
          onLinksChanged={(linked) =>
            setCanonicalEpisodeIds(linked.canonical_episode_ids ?? [])
          }
        />
      )}

      {isAdmin && !isTmdbEpisode ? (
        <AdminZone>
          <CanonicalEpisodeControls
            episodeId={episode.id}
            seasonNumber={null}
            episodeNumber={episode.episode_number ?? null}
            canonicalEpisodeValidatedAt={form.watch(
              "canonical_episode_validated_at",
            )}
            hasLinks={canonicalEpisodeIds.length > 0}
            enabled={enabled}
            onVerified={() => {
              form.setValue(
                "canonical_episode_validated_at",
                new Date().toISOString().slice(0, 16),
              )
              form.setValue("canonical_episode_note", VERIFIED_NOTE)
            }}
            onLinksChanged={(linked) => {
              setCanonicalEpisodeIds(linked.canonical_episode_ids ?? [])
              form.setValue(
                "canonical_episode_validated_at",
                linked.canonical_episode_validated_at?.slice(0, 16) ?? "",
              )
              form.setValue(
                "canonical_episode_note",
                linked.canonical_episode_note ?? "",
              )
            }}
          />
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

      {/*
              The row's own columns are put away behind a heading: they are the
              website's account of the episode, which is written by the import
              and only ever corrected by hand.
            */}
      {isAdmin ? (
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <Accordion
              type="single"
              collapsible
              className="rounded-xl border px-4"
            >
              <AccordionItem value="fields">
                <AccordionTrigger>Manually Edit Fields</AccordionTrigger>
                <AccordionContent>
                  <div className="grid gap-4 px-1 py-2 sm:grid-cols-2">
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="Name"
                        placeholder="Episode name"
                        type="text"
                      />
                    </div>
                    <FormTextField
                      control={form.control}
                      label="Episode Number"
                      placeholder="1"
                      type="number"
                    />
                    <FormTextField
                      control={form.control}
                      label="Sort Order"
                      type="number"
                    />
                    <FormTextField
                      control={form.control}
                      label="Air Date"
                      type="date"
                    />
                    <FormTextField
                      control={form.control}
                      name="duration"
                      label="Duration (seconds)"
                      placeholder="0"
                      type="number"
                    />
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="URL"
                        placeholder="https://..."
                        type="url"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="Image URL"
                        placeholder="https://..."
                        type="url"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="Description"
                        placeholder="Description"
                        type="text"
                      />
                    </div>
                    <FormTextField
                      control={form.control}
                      label="Data Timestamp"
                      type="datetime-local"
                    />
                    <FormTextField
                      control={form.control}
                      label="Update At"
                      type="datetime-local"
                      showNowButton
                    />
                    <FormTextField
                      control={form.control}
                      label="Key"
                      type="text"
                    />
                    <FormTextField
                      control={form.control}
                      label="Deleted At"
                      type="datetime-local"
                    />
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="Canonical Episode Note"
                        type="text"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="Canonical Episode Validated At"
                        type="datetime-local"
                        showNowButton
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <FormTextField
                        control={form.control}
                        label="Extra"
                        type="text"
                      />
                    </div>
                  </div>
                  {withCancel ? (
                    <ModalFooter isPending={mutation.isPending} />
                  ) : (
                    <div className="flex justify-end pt-2">
                      <LoadingButton type="submit" loading={mutation.isPending}>
                        Save
                      </LoadingButton>
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </form>
        </Form>
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
      <ModalContent
        size="3xl"
        className="max-h-[calc(100dvh-2rem)] overflow-y-hidden"
      >
        <DialogHeader>
          <DialogTitle>Episode Information</DialogTitle>
          <DialogDescription>
            What the website and TMDB each say about this episode, and which
            episodes the row stands for.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="max-h-none min-h-0 flex-1">
          <div className="py-4">
            <EpisodeInformationContent
              episode={episode}
              enabled={isOpen}
              onSaved={() => setIsOpen(false)}
              withCancel
            />
          </div>
        </DialogBody>
      </ModalContent>
    </Dialog>
  )
}

export default EditEpisode
