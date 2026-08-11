// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type SourceCreate, SourcesService } from "@/client"
import { AddButton } from "@/components/Common/AddButton"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { DialogTrigger } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

const formSchema = z.object({
  key: requiredKey,
  name: optionalString,
  favicon_url: optionalString,
  image_url: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface AddSourceProps {
  pluginId: string
}

// TODO: Validate
const AddSource = ({ pluginId }: AddSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: crypto.randomUUID(),
      name: "",
      favicon_url: "",
      image_url: "",
      data_timestamp: "",
      update_at: "",
    },
  })

  const mutation = useMutation({
    mutationKey: ["plugins", pluginId, "sources", "create"],
    mutationFn: (data: SourceCreate) =>
      SourcesService.createSource({ pluginId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Source created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["plugins", pluginId, "sources"],
      })
    },
  })

  // TODO: Validate
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
          <AddButton>Add Source</AddButton>
        </DialogTrigger>
      }
      title="Add Source"
      description="Create a new source for this plugin."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="Source name"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Favicon URL"
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

export default AddSource
