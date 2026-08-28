// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type EpisodeCreate, EpisodesService } from "@/client"
import { AddButton } from "@/components/Common/AddButton"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { DialogTrigger } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import {
  optionalInt,
  optionalNonNegativeInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"
import { handleError } from "@/utils"

const formSchema = z.object({
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

interface AddEpisodeProps {
  seasonKey: string
}

// TODO: Validate
const AddEpisode = ({ seasonKey }: AddEpisodeProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["media-table", "Episodes"]

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
      episode_number: "",
      url: "",
      description: "",
      image_url: "",
      air_date: "",
      duration: "",
      sort_order: "",
      data_timestamp: "",
      update_at: "",
      key: crypto.randomUUID(),
    },
  })

  const mutation = useMutation({
    mutationKey: ["seasons", seasonKey, "episodes", "create"],
    mutationFn: (data: EpisodeCreate) =>
      EpisodesService.createEpisode({ seasonId: seasonKey, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Episode created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    form.reset()
    // A manually-added episode is linked to nothing but itself; the canonical
    // row it stands for is created for it as it is stored.
    mutation.mutate(data)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <DialogTrigger asChild>
          <AddButton>Add Episode</AddButton>
        </DialogTrigger>
      }
      title="Add Episode"
      description="Create a new episode for this season."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="Episode name"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Episode Number"
        placeholder="1"
        type="number"
      />
      <FormTextField control={form.control} label="Sort Order" type="number" />
      <FormTextField
        control={form.control}
        label="URL"
        placeholder="https://..."
        type="url"
      />
      <FormTextField
        control={form.control}
        label="Description"
        placeholder="Description"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Image URL"
        placeholder="https://..."
        type="url"
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
      <FormTextField
        control={form.control}
        label="Data Timestamp"
        type="datetime-local"
      />
      <FormTextField
        control={form.control}
        label="Update At"
        type="datetime-local"
      />
      <FormTextField control={form.control} label="Key" type="text" />
    </FormModal>
  )
}

export default AddEpisode
