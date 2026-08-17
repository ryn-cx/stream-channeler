// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { EpisodesService, type EpisodeUpdate } from "@/client"
import { EpisodeInformationHero } from "@/components/ChannelCommon/EpisodeInformationHero"
import { FormCheckboxField } from "@/components/Common/FormCheckboxField"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
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
  | "canonical_episode_locked"
  | "canonical_episode_note"
  | "data_timestamp"
  | "update_at"
  | "deleted_at"
  | "extra"
>

const formSchema = z.object({
  canonical_episode_locked: z.boolean(),
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

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditEpisodeProps {
  episode: EditableEpisodeFields
}

// TODO: Validate
const EditEpisode = ({ episode }: EditEpisodeProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      canonical_episode_locked: episode.canonical_episode_locked ?? false,
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
        <TooltipIconButton
          label="Edit Episode"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit Episode"
      description="Update the episode details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
      size="3xl"
    >
      <CanonicalEpisodeField
        episodeId={episode.id}
        canonicalEpisodeIds={episode.canonical_episode_ids ?? []}
        name={episode.name ?? null}
        seasonNumber={null}
        episodeNumber={episode.episode_number ?? null}
        enabled={isOpen}
      />

      {/*
        The website's own account of the episode rather than TMDB's, since this
        window edits the website's row and what it says is what is being read
        against the episodes above.
      */}
      <EpisodeInformationHero
        episodeId={episode.id}
        enabled={isOpen}
        preferSource
      />

      {/*
        Which episodes the row stands for is what this window is opened for,
        so the row's own columns are put away behind a heading: they are the
        website's account of the episode, which is written by the import and
        only ever corrected by hand.
      */}
      <Accordion type="single" collapsible>
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
                <FormCheckboxField
                  control={form.control}
                  label="Canonical Episode Locked"
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
