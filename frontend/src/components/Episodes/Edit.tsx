// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { EpisodesService, type EpisodeUpdate } from "@/client"
import { FormCheckboxField } from "@/components/Common/FormCheckboxField"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import { extraText, parseExtraText } from "@/lib/extra"
import {
  nullifyBlanks,
  optionalInt,
  optionalNonNegativeInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"

import type { EpisodeTableData } from "./columns"

/** What the form reads, so any row carrying these can be edited. */
export type EditableEpisodeFields = Pick<
  EpisodeTableData,
  | "id"
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
      <div className="grid gap-4 sm:grid-cols-2">
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
        <FormTextField control={form.control} label="Air Date" type="date" />
        <FormTextField
          control={form.control}
          name="duration"
          label="Duration (seconds)"
          placeholder="0"
          type="number"
        />
        <FormTextField
          control={form.control}
          label="TMDB ID"
          placeholder="12345"
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
        <div className="sm:col-span-2">
          <FormTextField control={form.control} label="Key" type="text" />
          <FormTextField
            control={form.control}
            label="Canonical Episode Note"
            type="text"
          />
          <FormCheckboxField
            control={form.control}
            label="Canonical Episode Locked"
          />
          <FormTextField
            control={form.control}
            label="Deleted At"
            type="datetime-local"
          />
          <FormTextField control={form.control} label="Extra" type="text" />
          <FormTextField
            control={form.control}
            label="Episode Number"
            type="number"
          />
          <FormTextField
            control={form.control}
            label="Sort Order"
            type="number"
          />
          <FormTextField
            control={form.control}
            label="Duration"
            type="number"
          />
          <FormTextField
            control={form.control}
            label="Canonical Episode Note"
            type="text"
          />
          <FormCheckboxField
            control={form.control}
            label="Canonical Episode Locked"
          />
          <FormTextField
            control={form.control}
            label="Deleted At"
            type="datetime-local"
          />
          <FormTextField control={form.control} label="Extra" type="text" />
        </div>
      </div>
    </FormModal>
  )
}

export default EditEpisode
