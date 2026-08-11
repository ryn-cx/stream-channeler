// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { EpisodesService, type EpisodeUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TmdbIdentifierField } from "@/components/Common/TmdbIdentifierField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import { Checkbox } from "@/components/ui/checkbox"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  nullifyBlanks,
  optionalInt,
  optionalNonNegativeInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"

import type { EpisodeTableData } from "./columns"

const formSchema = z.object({
  name: optionalString,
  episode_number: optionalInt,
  url: optionalString,
  description: optionalString,
  image_url: optionalString,
  release_date: optionalString,
  air_date: optionalString,
  duration: optionalNonNegativeInt,
  sort_order: optionalInt,
  data_timestamp: optionalString,
  update_at: optionalString,
  key: requiredKey,
  episode_identifier: z.string().min(1, "Episode identifier is required"),
  episode_identifier_locked: z.boolean(),
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditEpisodeProps {
  episode: EpisodeTableData
}

// TODO: Validate
const EditEpisode = ({ episode }: EditEpisodeProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: episode.name ?? "",
      episode_number: episode.episode_number ?? "",
      url: episode.url ?? "",
      description: episode.description ?? "",
      image_url: episode.image_url ?? "",
      release_date: episode.release_date ?? "",
      air_date: episode.air_date ?? "",
      duration: episode.duration ?? "",
      sort_order: episode.sort_order ?? "",
      data_timestamp: episode.data_timestamp?.slice(0, 16) ?? "",
      update_at: episode.update_at?.slice(0, 16) ?? "",
      key: episode.key ?? "",
      episode_identifier: episode.episode_identifier,
      episode_identifier_locked: episode.episode_identifier_locked ?? false,
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
    mutation.mutate(nullifyBlanks(data))
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
        <FormTextField
          control={form.control}
          label="Release Date"
          type="date"
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
        </div>
        <TmdbIdentifierField
          identifier={form.watch("episode_identifier")}
          onChange={(identifier) => {
            form.setValue("episode_identifier", identifier, {
              shouldValidate: true,
              shouldDirty: true,
            })
            form.setValue("episode_identifier_locked", true)
          }}
        />
        <FormField
          control={form.control}
          name="episode_identifier"
          render={({ field, fieldState }) => (
            <FormItem>
              <FormLabel>
                Episode Identifier<span className="text-destructive"> *</span>
              </FormLabel>
              <FormControl>
                <Input
                  aria-invalid={fieldState.invalid}
                  required
                  type="text"
                  {...field}
                  onChange={(event) => {
                    field.onChange(event)
                    form.setValue("episode_identifier_locked", true)
                  }}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="sm:col-span-2">
          <FormField
            control={form.control}
            name="episode_identifier_locked"
            render={({ field }) => (
              <FormItem className="flex items-center gap-3 space-y-0">
                <FormControl>
                  <Checkbox
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                </FormControl>
                <FormLabel className="font-normal">
                  Lock episode identifier?
                </FormLabel>
              </FormItem>
            )}
          />
        </div>
      </div>
    </FormModal>
  )
}

export default EditEpisode
