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

interface EditSeasonProps {
  season: SeasonTableData
}

const EditSeason = ({ season }: EditSeasonProps) => {
  const { showKey } = useParams({ strict: false })
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryKey = ["shows", showKey, "seasons"]

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema) as any,
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: season.name ?? "",
      season_number: season.season_number ?? "",
      url: season.url ?? "",
      image_url: season.image_url ?? "",
      sort_order: season.sort_order ?? "",
      data_timestamp: season.data_timestamp?.slice(0, 16) ?? "",
      key: season.key ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      request(OpenAPI, {
        method: "PATCH",
        url: "/api/v1/seasons/{season_id}",
        path: { season_id: season.id },
        body: data,
        mediaType: "application/json",
      }),
    onMutate: async (newData, context) => {
      await context.client.cancelQueries({ queryKey })
      const previous = context.client.getQueryData<SeasonsListOutput>(queryKey)

      context.client.setQueryData<SeasonsListOutput>(queryKey, (old) => ({
        ...old!,
        data: old!.data.map((s) =>
          s.id === season.id ? ({ ...s, ...newData } as SeasonTableData) : s,
        ),
      }))

      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Season updated successfully")
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
      season_number: data.season_number || undefined,
      sort_order: data.sort_order || undefined,
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
          <p>Edit season</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Season</DialogTitle>
              <DialogDescription>
                Update the season details below.
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

export default EditSeason
