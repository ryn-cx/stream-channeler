// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SeasonsService, type SeasonUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import useCustomToast from "@/hooks/useCustomToast"
import { optionalInt, optionalString, requiredKey } from "@/lib/formSchemas"
import { handleError } from "@/utils"

import type { SeasonTableData } from "./seasonColumns"

type SeasonsData = Array<SeasonTableData>

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

interface EditSeasonProps {
  season: SeasonTableData
}

const EditSeason = ({ season }: EditSeasonProps) => {
  const { showKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["shows", showKey, "seasons"]

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: season.name ?? "",
      season_number: season.season_number ?? "",
      url: season.url ?? "",
      image_url: season.image_url ?? "",
      sort_order: season.sort_order ?? "",
      data_timestamp: season.data_timestamp?.slice(0, 16) ?? "",
      update_at: season.update_at?.slice(0, 16) ?? "",
      key: season.key ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: SeasonUpdate) =>
      SeasonsService.updateSeason({ seasonId: season.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<SeasonsData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<SeasonsData>(queryKey, (old) =>
        old!.map((s) =>
          s.id === season.id
            ? ({ ...s, ...newData, pending: true } as SeasonTableData)
            : s,
        ),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Season updated successfully")
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
          label="Edit Season"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit Season"
      description="Update the season details below."
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

export default EditSeason
