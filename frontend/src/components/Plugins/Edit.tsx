// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { PluginsService, type PluginUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  nullifyBlanks,
  optionalString,
  requiredKey,
  visibilityEnum,
} from "@/lib/formSchemas"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"

import type { PluginTableData } from "./columns"

const formSchema = z.object({
  key: requiredKey,
  name: optionalString,
  version: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
  visibility: visibilityEnum,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditPluginProps {
  plugin: PluginTableData
}

const EditPlugin = ({ plugin }: EditPluginProps) => {
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
      visibility: plugin.visibility ?? "private",
    },
  })

  const mutation = useEditTableRow<PluginUpdate>({
    mutationFn: (data) =>
      PluginsService.updatePlugin({ pluginId: plugin.id, requestBody: data }),
    rowId: plugin.id,
    successMessage: "Plugin updated successfully",
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
          label="Edit Plugin"
          icon={<Pencil />}
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
      <FormField
        control={form.control}
        name="visibility"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Visibility</FormLabel>
            <Select value={field.value} onValueChange={field.onChange}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {VISIBILITY_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {visibilityLabel(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />
    </FormModal>
  )
}

export default EditPlugin
