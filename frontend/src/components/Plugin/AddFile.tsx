// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type FileCreate, PluginsService } from "@/client"
import { AddButton } from "@/components/Common/AddButton"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextArea } from "@/components/Common/FormTextArea"
import { FormTextField } from "@/components/Common/FormTextField"
import { DialogTrigger } from "@/components/ui/dialog"
import useCustomToast from "@/hooks/useCustomToast"
import { optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

const formSchema = z.object({
  key: requiredKey,
  data_timestamp: z.string().min(1, "Data timestamp is required"),
  content: optionalString,
  update_at: optionalString,
  extra: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

function currentLocalDateTime() {
  const now = new Date()
  const pad = (value: number) => String(value).padStart(2, "0")
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(
    now.getDate(),
  )}T${pad(now.getHours())}:${pad(now.getMinutes())}`
}

interface AddFileProps {
  pluginId: string
}

const AddFile = ({ pluginId }: AddFileProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: crypto.randomUUID(),
      data_timestamp: currentLocalDateTime(),
      content: "",
      update_at: "",
      extra: "",
    },
  })

  const mutation = useMutation({
    mutationKey: ["plugins", pluginId, "files", "create"],
    mutationFn: (data: FileCreate) =>
      PluginsService.createFile({ pluginId, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("File created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["plugins", pluginId, "files"],
      })
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
          <AddButton>Add File</AddButton>
        </DialogTrigger>
      }
      title="Add File"
      description="Create a new file for this plugin."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField control={form.control} label="Key" type="text" />
      <FormTextField
        control={form.control}
        label="Data Timestamp"
        type="datetime-local"
        required
      />
      <FormTextField
        control={form.control}
        label="Update At"
        type="datetime-local"
      />
      <FormTextArea
        control={form.control}
        label="Content"
        placeholder="File content..."
        rows={8}
      />
      <FormTextField control={form.control} label="Extra" type="text" />
    </FormModal>
  )
}

export default AddFile
