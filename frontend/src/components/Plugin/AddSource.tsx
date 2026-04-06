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

import type { SourceTableData } from "./sourceColumns"

type SourcesData = Array<SourceTableData>

const formSchema = z.object({
  key: z.string().max(255).optional().or(z.literal("")),
  name: z.string().max(255).optional().or(z.literal("")),
  favicon_url: z.string().max(2048).optional().or(z.literal("")),
  image_url: z.string().max(2048).optional().or(z.literal("")),
  data_timestamp: z.string().optional().or(z.literal("")),
})

type FormData = z.infer<typeof formSchema>

interface AddSourceProps {
  pluginId: string
}

const AddSource = ({ pluginId }: AddSourceProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: "",
      name: "",
      favicon_url: "",
      image_url: "",
      data_timestamp: "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "POST",
        url: `/api/v1/plugins/${pluginId}/sources`,
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newSource, context) => {
      const queryKey = ["plugins", pluginId, "sources"]
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SourcesData>(queryKey)

      context.client.setQueryData<SourcesData>(queryKey, (old) => [
        ...(old ?? []),
        {
          key: crypto.randomUUID(),
          name: newSource.name ?? null,
          id: crypto.randomUUID(),
          plugin_id: pluginId,
          favicon_url: null,
          image_url: null,
          data_timestamp: null,
        },
      ])

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Source created successfully")
      form.reset()
      setIsOpen(false)
    },
    onError: (error, _variables, onMutateResult, context) => {
      context.client.setQueryData(
        ["plugins", pluginId, "sources"],
        onMutateResult?.previous,
      )
      handleError.call(showErrorToast, error as any)
    },
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["plugins", pluginId, "sources"],
      }),
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({
      ...data,
      key: data.key || undefined,
      name: data.name || undefined,
      data_timestamp: data.data_timestamp || undefined,
    })
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="mt-2 mb-4">
          <Plus className="mr-2" />
          Add Source
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Source</DialogTitle>
          <DialogDescription>
            Create a new source for this plugin.
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
                      <Input placeholder="Source name" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="favicon_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Favicon URL</FormLabel>
                    <FormControl>
                      <Input placeholder="https://..." type="url" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="image_url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Image URL</FormLabel>
                    <FormControl>
                      <Input placeholder="https://..." type="url" {...field} />
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
                      <Input
                        placeholder="Auto-generated if empty"
                        type="text"
                        {...field}
                      />
                    </FormControl>
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

export default AddSource
