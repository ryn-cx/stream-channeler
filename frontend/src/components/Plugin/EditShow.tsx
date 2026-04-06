// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { useParams } from "@tanstack/react-router"
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
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

import type { ShowTableData } from "./showColumns"

type ShowsData = Array<ShowTableData>

const formSchema = z.object({
  key: z.string().max(255).optional().or(z.literal("")),
  name: z.string().max(255).optional().or(z.literal("")),
  media_type: z.string().max(255).optional().or(z.literal("")),
  description: z.string().optional().or(z.literal("")),
  url: z.string().max(2048).optional().or(z.literal("")),
  image_url: z.string().max(2048).optional().or(z.literal("")),
  data_timestamp: z.string().optional().or(z.literal("")),
})

type FormData = z.infer<typeof formSchema>

interface EditShowProps {
  show: ShowTableData
}

const EditShow = ({ show }: EditShowProps) => {
  const { sourceKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["sources", sourceKey, "shows"]

  const form = useForm<FormData>({
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
      data_timestamp: show.data_timestamp?.slice(0, 16) ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "PATCH",
        url: "/api/v1/shows/{show_id}",
        path: { show_id: show.id },
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newData, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<ShowsData>(queryKey)

      context.client.setQueryData<ShowsData>(queryKey, (old) =>
        old!.map((s) => (s.id === show.id ? { ...s, ...newData } : s)),
      )

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Show updated successfully")
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
      key: data.key || undefined,
      name: data.name || undefined,
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
          <p>Edit show</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Show</DialogTitle>
              <DialogDescription>
                Update the show details below.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Show name" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="media_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Media Type</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g. anime, series"
                        type="text"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Input placeholder="Description" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="url"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>URL</FormLabel>
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
                      <Input type="text" {...field} />
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

export default EditShow
