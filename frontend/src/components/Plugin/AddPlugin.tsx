// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { OpenAPI } from "@/client"
import { request } from "@/client/core/request"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { PluginTableData } from "./columns"

type PluginsData = Array<PluginTableData>

const formSchema = z.object({
  key: z.string().min(1),
  name: z.string().max(255).optional().or(z.literal("")),
  version: z.string().max(255).optional().or(z.literal("")),
  data_timestamp: z.string().optional().or(z.literal("")),
  public: z.boolean(),
})

type FormData = z.infer<typeof formSchema>

const makeDefaults = (): FormData => ({
  key: crypto.randomUUID(),
  name: "",
  version: "",
  data_timestamp: "",
  public: false,
})

const AddPlugin = () => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: makeDefaults(),
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "POST",
        url: "/api/v1/plugins",
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newPlugin, context) => {
      await context.client.cancelQueries({ queryKey: ["plugins"] })
      const previous = context.client.getQueryData<PluginsData>(["plugins"])

      context.client.setQueryData<PluginsData>(["plugins"], (old) => [
        ...(old ?? []),
        {
          key: newPlugin.key,
          name: newPlugin.name ?? null,
          version: newPlugin.version ?? null,
          id: crypto.randomUUID(),
          user_id: null,
          data_timestamp: null,
          deleted_at: null,
          public: newPlugin.public,
        },
      ])

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Plugin created successfully")
      form.reset(makeDefaults())
      setIsOpen(false)
    },
    onError: (error, _variables, onMutateResult, context) => {
      context.client.setQueryData(["plugins"], onMutateResult?.previous)
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["plugins"] }),
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
      <DialogTrigger asChild>
        <Button className="mt-2 mb-4">
          <Plus className="mr-2" />
          Add Plugin
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Plugin</DialogTitle>
          <DialogDescription>
            Create a new plugin by providing a name.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="grid gap-4 py-4">
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
                name="public"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Is public?</FormLabel>
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

export default AddPlugin
