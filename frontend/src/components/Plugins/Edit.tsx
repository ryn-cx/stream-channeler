// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type PluginOutput, PluginsService, type PluginUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import { nullifyBlanks, optionalString, requiredKey } from "@/lib/formSchemas"

const formSchema = z.object({
  key: requiredKey,
  name: optionalString,
  version: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditPluginProps {
  plugin: PluginOutput
  size?: React.ComponentProps<typeof TooltipIconButton>["size"]
}

// TODO: Validate
const EditPlugin = ({ plugin, size }: EditPluginProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: plugin.key ?? "",
      name: plugin.name ?? "",
      version: plugin.version ?? "",
      data_timestamp: plugin.data_timestamp?.slice(0, 16) ?? "",
      update_at: plugin.update_at?.slice(0, 16) ?? "",
    },
  })

  const mutation = useEditTableRow<PluginUpdate>({
    mutationFn: (data) =>
      PluginsService.updatePlugin({ pluginId: plugin.id, requestBody: data }),
    rowId: plugin.id,
    successMessage: "Plugin updated successfully",
    extraInvalidateKeys: [["plugins", plugin.id]],
  })

  // TODO: Validate
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
          label="Edit Plugin"
          icon={<Pencil />}
          size={size}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit Plugin"
      description="Update the plugin details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField control={form.control} label="Key" type="text" />
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
        showNowButton
      />
    </FormModal>
  )
}

export default EditPlugin
