// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ShowsService, type ShowUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

import type { ShowTableData } from "./showColumns"

type ShowsData = Array<ShowTableData>

const formSchema = z.object({
  key: requiredKey,
  name: optionalString,
  media_type: optionalString,
  description: optionalString,
  url: optionalString,
  image_url: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditShowProps {
  show: ShowTableData
}

const EditShow = ({ show }: EditShowProps) => {
  const { sourceKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["sources", sourceKey, "shows"]

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: show.key ?? "",
      name: show.name ?? "",
      media_type: show.media_type ?? "",
      description: show.description ?? "",
      url: show.url ?? "",
      image_url: show.image_url ?? "",
      data_timestamp: show.data_timestamp?.slice(0, 16) ?? "",
      update_at: show.update_at?.slice(0, 16) ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: ShowUpdate) =>
      ShowsService.updateShow({ showId: show.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<ShowsData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<ShowsData>(queryKey, (old) =>
        old!.map((s) =>
          s.id === show.id
            ? ({ ...s, ...newData, pending: true } as ShowTableData)
            : s,
        ),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Show updated successfully")
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
    mutation.mutate(data)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <TooltipIconButton
          label="Edit Show"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit Show"
      description="Update the show details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="Show name"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Media Type"
        placeholder="e.g. anime, series"
        type="text"
      />
      <FormTextField
        control={form.control}
        label="Description"
        placeholder="Description"
        type="text"
      />
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
        showNowButton
      />
      <FormTextField control={form.control} label="Key" type="text" />
    </FormModal>
  )
}

export default EditShow
