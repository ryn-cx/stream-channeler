// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ShowsService, type ShowUpdate } from "@/client"
import { FormEmojiField } from "@/components/Common/FormEmojiField"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import { nullifyBlanks, optionalString, requiredKey } from "@/lib/formSchemas"

import type { ShowTableData } from "./columns"

const formSchema = z.object({
  key: requiredKey,
  name: optionalString,
  media_type: optionalString,
  description: optionalString,
  url: optionalString,
  image_url: optionalString,
  icon: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditShowProps {
  show: ShowTableData
}

const EditShow = ({ show }: EditShowProps) => {
  const [isOpen, setIsOpen] = useState(false)

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
      icon: show.icon ?? "",
      data_timestamp: show.data_timestamp?.slice(0, 16) ?? "",
      update_at: show.update_at?.slice(0, 16) ?? "",
    },
  })

  const mutation = useEditTableRow<ShowUpdate>({
    mutationFn: (data) =>
      ShowsService.updateShow({ showId: show.id, requestBody: data }),
    rowId: show.id,
    successMessage: "Show updated successfully",
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
      <FormEmojiField control={form.control} name="icon" label="Icon" />
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
