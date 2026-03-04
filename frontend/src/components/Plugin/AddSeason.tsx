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

import type { SeasonTableData } from "./seasonColumns"

interface SeasonsListOutput {
  data: SeasonTableData[]
  count: number
}

const formSchema = z.object({
  name: z.string().max(255).optional().or(z.literal("")),
  season_number: z.union([z.literal(""), z.coerce.number().int()]).optional(),
  url: z.string().max(2048).optional().or(z.literal("")),
  image_url: z.string().max(2048).optional().or(z.literal("")),
  sort_order: z.union([z.literal(""), z.coerce.number().int()]).optional(),
  data_timestamp: z.string().optional().or(z.literal("")),
  key: z.string().max(255).optional().or(z.literal("")),
})

type FormData = z.infer<typeof formSchema>

interface AddSeasonProps {
  showKey: string
}

const AddSeason = ({ showKey }: AddSeasonProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["shows", showKey, "seasons"]

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema) as any,
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
      season_number: "",
      url: "",
      image_url: "",
      sort_order: "",
      data_timestamp: "",
      key: "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "POST",
        url: `/api/v1/shows/${showKey}/seasons`,
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newSeason, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SeasonsListOutput>(queryKey)

      context.client.setQueryData<SeasonsListOutput>(queryKey, (old) => ({
        ...old!,
        data: [
          ...old!.data,
          {
            key: crypto.randomUUID(),
            name: newSeason.name ?? null,
            id: crypto.randomUUID(),
            show_id: showKey,
            season_number: null,
            url: null,
            image_url: null,
            sort_order: null,
            data_timestamp: null,
          },
        ],
        count: old!.count + 1,
      }))

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Season created successfully")
      form.reset()
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
      key: data.key || undefined,
      name: data.name || undefined,
      season_number: data.season_number || undefined,
      sort_order: data.sort_order || undefined,
      data_timestamp: data.data_timestamp || undefined,
    })
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="my-4">
          <Plus className="mr-2" />
          Add Season
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Season</DialogTitle>
          <DialogDescription>
            Create a new season for this show.
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
                      <Input placeholder="Season name" type="text" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="season_number"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Season Number</FormLabel>
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

export default AddSeason
