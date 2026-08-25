// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type PluginCreate, PluginsService } from "@/client"
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
  version: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

// TODO: Validate
const AddPlugin = () => {
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
      version: "",
      data_timestamp: "",
      update_at: "",
    },
  })

  const mutation = useMutation({
    mutationKey: ["plugins", "create"],
    mutationFn: (data: PluginCreate) =>
      PluginsService.createPlugin({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Plugin created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["plugins"] })
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
          <AddButton>Add Plugin</AddButton>
        </DialogTrigger>
      }
      title="Add Plugin"
      description="Create a new plugin by providing a name."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="Plugin name"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Version"
        placeholder="Version"
        type="text"
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

export default AddPlugin
