// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { PluginsService, type PluginUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
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
import useCustomToast from "@/hooks/useCustomToast"
import { optionalString, requiredKey, visibilityEnum } from "@/lib/formSchemas"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

import type { PluginTableData } from "./columns"

type PluginsData = Array<PluginTableData>

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
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins"]

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

  const mutation = useMutation({
    mutationFn: (data: PluginUpdate) =>
      PluginsService.updatePlugin({ pluginId: plugin.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey })
      // Snapshot the previous value
      const previous = context.client.getQueryData<PluginsData>(queryKey)

      // Optimistically update to the new value
      context.client.setQueryData<PluginsData>(queryKey, (old) =>
        old!.map((p) =>
          p.id === plugin.id
            ? ({ ...p, ...newData, pending: true } as PluginTableData)
            : p,
        ),
      )

      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Plugin updated successfully")
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
