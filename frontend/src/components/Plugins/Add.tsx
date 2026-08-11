// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type PluginCreate, PluginsService } from "@/client"
import { AddButton } from "@/components/Common/AddButton"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { Checkbox } from "@/components/ui/checkbox"
import { DialogTrigger } from "@/components/ui/dialog"
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

const formSchema = z.object({
  key: requiredKey,
  name: optionalString,
  version: optionalString,
  data_timestamp: optionalString,
  update_at: optionalString,
  visibility: visibilityEnum,
  anonymous: z.boolean(),
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

// TODO: Validate
const AddPlugin = () => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: crypto.randomUUID(),
      name: "",
      version: "",
      data_timestamp: "",
      update_at: "",
      visibility: "private",
      anonymous: false,
    },
  })

  const mutation = useMutation({
    mutationKey: ["plugins", "create"],
    mutationFn: (data: PluginCreate) =>
      PluginsService.createPlugin({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Plugin created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["plugins"] })
    },
  })

  // TODO: Validate
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
          <AddButton>Add Plugin</AddButton>
        </DialogTrigger>
      }
      title="Add Plugin"
      description="Create a new plugin by providing a name."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
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
      />
      <FormTextField control={form.control} label="Key" type="text" />
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
      <FormField
        control={form.control}
        name="anonymous"
        render={({ field }) => (
          <FormItem className="flex items-start gap-3">
            <FormControl>
              <Checkbox
                checked={field.value}
                onCheckedChange={(checked) => field.onChange(checked === true)}
              />
            </FormControl>
            <div className="space-y-1 leading-none">
              <FormLabel className="font-normal">Publish anonymously</FormLabel>
              <p className="text-sm text-muted-foreground">
                Hides you as the owner of this plugin and of everything it
                imports.
              </p>
            </div>
          </FormItem>
        )}
      />
    </FormModal>
  )
}

export default AddPlugin
