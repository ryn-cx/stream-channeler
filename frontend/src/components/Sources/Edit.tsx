// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type SourcePublic, SourcesService, type SourceUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import { extraText, parseExtraText } from "@/lib/extra"
import { nullifyBlanks, optionalString, requiredKey } from "@/lib/formSchemas"

const formSchema = z.object({
  deleted_at: optionalString,
  extra: optionalString,
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
  source: SourcePublic
  size?: React.ComponentProps<typeof TooltipIconButton>["size"]
}

// TODO: Validate
const EditSource = ({ source, size }: EditSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      deleted_at: source.deleted_at?.slice(0, 16) ?? "",
      extra: extraText(source.extra),
      key: source.key ?? "",
      name: source.name ?? "",
      favicon_url: source.favicon_url ?? "",
      image_url: source.image_url ?? "",
      data_timestamp: source.data_timestamp?.slice(0, 16) ?? "",
      update_at: source.update_at?.slice(0, 16) ?? "",
    },
  })

  const mutation = useEditTableRow<SourceUpdate>({
    mutationFn: (data) =>
      SourcesService.updateSource({ sourceId: source.id, requestBody: data }),
    rowId: source.id,
    successMessage: "Source updated successfully",
    extraInvalidateKeys: [["sources", source.id]],
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    mutation.mutate({
      ...nullifyBlanks(data),
      extra: parseExtraText(data.extra ?? ""),
    })
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <TooltipIconButton
          label="Edit Source"
          icon={<Pencil />}
          size={size}
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
      <FormTextField
        control={form.control}
        label="Deleted At"
        type="datetime-local"
      />
      <FormTextField control={form.control} label="Extra" type="text" />
      <FormTextField
        control={form.control}
        label="Deleted At"
        type="datetime-local"
      />
      <FormTextField control={form.control} label="Extra" type="text" />
    </FormModal>
  )
}

export default EditSource
