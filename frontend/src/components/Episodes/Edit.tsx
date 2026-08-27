// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { EpisodesService, type EpisodeUpdate } from "@/client"
import {
  EpisodeInformationHero,
  useEpisodeInformation,
} from "@/components/ChannelCommon/EpisodeInformationHero"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import EditShow from "@/components/Shows/Edit"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { useShow } from "@/hooks/useEntities"
import { extraText, parseExtraText } from "@/lib/extra"
import {
  nullifyBlanks,
  optionalInt,
  optionalNonNegativeInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"

import { CanonicalEpisodeField } from "./CanonicalEpisodeField"
import type { EpisodeTableData } from "./columns"

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

interface EditEpisodeProps {
  episode: EditableEpisodeFields
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// TODO: Validate
const EditEpisode = ({ episode, open, onOpenChange }: EditEpisodeProps) => {
  const [isOpenHere, setIsOpenHere] = useState(false)
  const isOpen = open ?? isOpenHere
  const setIsOpen = onOpenChange ?? setIsOpenHere
  const information = useEpisodeInformation(episode.id, isOpen)
  const showId = information.data?.source.show.id
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
    setIsOpen(false)
    mutation.mutate({
      ...nullifyBlanks(data),
      extra: parseExtraText(data.extra ?? ""),
    })
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        open === undefined ? (
          <TooltipIconButton
            label="Edit Episode"
            icon={<Pencil />}
            onClick={() => setIsOpen(true)}
          />
        ) : null
      }
      title="Edit Episode"
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
      size="3xl"
    >
      {/*
        The website's own account of the episode rather than TMDB's, since this
        window edits the website's row and what it says is what is being read
        against the episodes above.
      */}
      <EpisodeInformationHero
        episodeId={episode.id}
        enabled={isOpen}
        preferSource
        spelledOutDuration
        titleAction={showId ? <EditShowOfEpisode showId={showId} /> : null}
      />

      <CanonicalEpisodeField
        episodeId={episode.id}
        canonicalEpisodeIds={canonicalEpisodeIds}
        seasonNumber={null}
        episodeNumber={episode.episode_number ?? null}
        canonicalEpisodeValidatedAt={form.watch(
          "canonical_episode_validated_at",
        )}
        enabled={isOpen}
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

      {/*
        Which episodes the row stands for is what this window is opened for,
        so the row's own columns are put away behind a heading: they are the
        website's account of the episode, which is written by the import and
        only ever corrected by hand.
      */}
      <Accordion type="single" collapsible className="rounded-xl border px-4">
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
              <FormTextField control={form.control} label="Key" type="text" />
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
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </FormModal>
  )
}

export default EditEpisode
