// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SourcesService, type SourceUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { nullifyBlanks, optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

import type { SourceTableData } from "./columns"

type SourcesData = Array<SourceTableData>

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

interface EditSourceProps {
  source: SourceTableData
}

const EditSource = ({ source }: EditSourceProps) => {
  const { pluginId } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins", pluginId, "sources"]

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: source.key ?? "",
      name: source.name ?? "",
      favicon_url: source.favicon_url ?? "",
      image_url: source.image_url ?? "",
      data_timestamp: source.data_timestamp?.slice(0, 16) ?? "",
      update_at: source.update_at?.slice(0, 16) ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: SourceUpdate) =>
      SourcesService.updateSource({ sourceId: source.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<SourcesData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<SourcesData>(queryKey, (old) =>
        old!.map((s) =>
          s.id === source.id
            ? ({ ...s, ...newData, pending: true } as SourceTableData)
            : s,
        ),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Source updated successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _newData, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

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
          label="Edit Source"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit Source"
      description="Update the source details below."
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
        showNowButton
      />
      <FormTextField control={form.control} label="Key" type="text" />
    </FormModal>
  )
}

export default EditSource
