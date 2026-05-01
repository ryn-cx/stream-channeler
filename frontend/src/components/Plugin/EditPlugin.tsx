// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

import type { PluginTableData } from "./columns"

type PluginsData = Array<PluginTableData>

const formSchema = z.object({
  key: z.string().min(1, "Key is required").max(255),
  name: z.string().max(255).optional().or(z.literal("")),
  version: z.string().max(255).optional().or(z.literal("")),
  data_timestamp: z.string().optional().or(z.literal("")),
  visibility: z.enum(["public", "unlisted", "private"]),
})

type FormData = z.infer<typeof formSchema>

interface EditPluginProps {
  plugin: PluginTableData
}

const EditPlugin = ({ plugin }: EditPluginProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["plugins"]

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: plugin.key ?? "",
      name: plugin.name ?? "",
      version: plugin.version ?? "",
      data_timestamp: plugin.data_timestamp?.slice(0, 16) ?? "",
      visibility: plugin.visibility ?? "private",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "PATCH",
        url: "/api/v1/plugins/{plugin_id}",
        path: { plugin_id: plugin.id },
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newData, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<PluginsData>(queryKey)

      context.client.setQueryData<PluginsData>(queryKey, (old) =>
        old!.map((p) => (p.id === plugin.id ? { ...p, ...newData } : p)),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Plugin updated successfully")
      setIsOpen(false)
    },
    onError: (error, _newData, onMutateResult, context) => {
      context.client.setQueryData(queryKey, onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey }),
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      ...data,
      name: data.name || undefined,
      version: data.version || undefined,
      data_timestamp: data.data_timestamp || undefined,
    })
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost">
              <Pencil />
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>
          <p>Edit plugin</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Plugin</DialogTitle>
              <DialogDescription>
                Update the plugin details below.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Key</FormLabel>
                    <FormControl>
                      <Input type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Plugin name" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="version"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Version</FormLabel>
                    <FormControl>
                      <Input placeholder="Version" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="data_timestamp"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data Timestamp</FormLabel>
                    <FormControl>
                      <Input type="datetime-local" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
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
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default EditPlugin
