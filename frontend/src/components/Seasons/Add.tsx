// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type SeasonCreate, SeasonsService } from "@/client"
import { AddButton } from "@/components/Common/AddButton"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { DialogTrigger } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { optionalInt, optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

const formSchema = z.object({
  name: optionalString,
  season_number: optionalInt,
  url: optionalString,
  image_url: optionalString,
  sort_order: optionalInt,
  data_timestamp: optionalString,
  update_at: optionalString,
  key: requiredKey,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface AddSeasonProps {
  showKey: string
}

const AddSeason = ({ showKey }: AddSeasonProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["shows", showKey, "seasons"]

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
      season_number: "",
      url: "",
      image_url: "",
      sort_order: "",
      data_timestamp: "",
      update_at: "",
      key: crypto.randomUUID(),
    },
  })

  const mutation = useMutation({
    mutationKey: ["shows", showKey, "seasons", "create"],
    mutationFn: (data: SeasonCreate) =>
      SeasonsService.createSeason({ showId: showKey, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Season created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey })
    },
  })

  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    form.reset()
    mutation.mutate(data)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <DialogTrigger asChild>
          <AddButton>Add Season</AddButton>
        </DialogTrigger>
      }
      title="Add Season"
      description="Create a new season for this show."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="Season name"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Season Number"
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
        label="Image URL"
        placeholder="https://..."
        type="url"
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

export default AddSeason
