// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SeasonsService, type SeasonUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import {
  nullifyBlanks,
  optionalInt,
  optionalString,
  requiredKey,
} from "@/lib/formSchemas"

import type { SeasonTableData } from "./columns"

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
  const [isOpen, setIsOpen] = useState(false)

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

  const mutation = useEditTableRow<SeasonUpdate>({
    mutationFn: (data) =>
      SeasonsService.updateSeason({ seasonId: season.id, requestBody: data }),
    rowId: season.id,
    successMessage: "Season updated successfully",
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
        showNowButton
      />
      <FormTextField control={form.control} label="Key" type="text" />
    </FormModal>
  )
}

export default EditSeason
