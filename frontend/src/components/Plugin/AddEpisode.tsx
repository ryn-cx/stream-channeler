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

import type { EpisodeTableData } from "./episodeColumns"

type EpisodesData = Array<EpisodeTableData>

const formSchema = z.object({
  name: z.string().max(255).optional().or(z.literal("")),
  episode_number: z.union([z.literal(""), z.coerce.number().int()]).optional(),
  url: z.string().max(2048).optional().or(z.literal("")),
  description: z.string().optional().or(z.literal("")),
  image_url: z.string().max(2048).optional().or(z.literal("")),
  release_date: z.string().optional().or(z.literal("")),
  air_date: z.string().optional().or(z.literal("")),
  duration: z.union([z.literal(""), z.coerce.number().int().min(0)]).optional(),
  sort_order: z.union([z.literal(""), z.coerce.number().int()]).optional(),
  data_timestamp: z.string().optional().or(z.literal("")),
  update_at: z.string().optional().or(z.literal("")),
  key: z.string().min(1).max(255),
})

type FormData = z.infer<typeof formSchema>

const makeDefaults = (): FormData => ({
  name: "",
  episode_number: "",
  url: "",
  description: "",
  image_url: "",
  release_date: "",
  air_date: "",
  duration: "",
  sort_order: "",
  data_timestamp: "",
  update_at: "",
  key: crypto.randomUUID(),
})

interface AddEpisodeProps {
  seasonKey: string
}

const AddEpisode = ({ seasonKey }: AddEpisodeProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["seasons", seasonKey, "episodes"]

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema) as any,
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: makeDefaults(),
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "POST",
        url: `/api/v1/seasons/${seasonKey}/episodes`,
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newEpisode, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<EpisodesData>(queryKey)

      context.client.setQueryData<EpisodesData>(queryKey, (old) => [
        ...(old ?? []),
        {
          key: newEpisode.key,
          name: newEpisode.name ?? null,
          id: crypto.randomUUID(),
          season_id: seasonKey,
          episode_number: null,
          url: null,
          description: null,
          image_url: null,
          release_date: null,
          air_date: null,
          duration: null,
          sort_order: null,
          data_timestamp: null,
          update_at: newEpisode.update_at ?? null,
        },
      ])

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Episode created successfully")
      form.reset(makeDefaults())
      setIsOpen(false)
    },
    onError: (error, _variables, onMutateResult, context) => {
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
      episode_number: data.episode_number || undefined,
      duration: data.duration || undefined,
      sort_order: data.sort_order || undefined,
      release_date: data.release_date || undefined,
      air_date: data.air_date || undefined,
      data_timestamp: data.data_timestamp || undefined,
      update_at: data.update_at || undefined,
    })
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="mt-2 mb-4">
          <Plus className="mr-2" />
          Add Episode
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Episode</DialogTitle>
          <DialogDescription>
            Create a new episode for this season.
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
                      <Input
                        placeholder="Episode name"
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
                name="episode_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Episode Number</FormLabel>
                    <FormControl>
                      <Input placeholder="1" type="number" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="sort_order"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Sort Order</FormLabel>
                    <FormControl>
                      <Input type="number" {...field} />
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
                name="release_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Release Date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="air_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Air Date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="duration"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Duration (seconds)</FormLabel>
                    <FormControl>
                      <Input placeholder="0" type="number" {...field} />
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
                name="update_at"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Update At</FormLabel>
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

export default AddEpisode
