// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import {
  EpisodesService,
  type WatchedEpisodesOutput,
  type WatchItem,
  type WatchPatchInput,
} from "@/client"
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
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z.object({
  watch_date: z.string(),
  verified: z.boolean(),
})

type FormData = z.infer<typeof formSchema>

interface EditWatchProps {
  watch: WatchItem
}

const EditWatch = ({ watch }: EditWatchProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      watch_date: new Date(watch.watch_date).toISOString().slice(0, 23),
      verified: watch.verified,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: WatchPatchInput) =>
      EpisodesService.patchWatchedEpisode({
        WatchId: watch.id,
        requestBody: data,
      }),
    // When mutate is called:
    onMutate: async (data, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["watches"] })

      // Snapshot the previous value
      const previousWatches =
        context.client.getQueryData<WatchedEpisodesOutput>(["watches"])

      // Optimistically update to the new value
      context.client.setQueryData<WatchedEpisodesOutput>(
        ["watches"],
        (old) => ({
          ...old!,
          watches: old!.watches.map((w) =>
            w.id === watch.id ? { ...w, ...data } : w,
          ),
        }),
      )

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: () => {
      showSuccessToast("Watch updated successfully")
      setIsOpen(false)
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _data, onMutateResult, context) => {
      context.client.setQueryData(["watches"], onMutateResult?.previousWatches)
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["watches"] }),
  })

  const onSubmit = (data: FormData) => {
    const payload: WatchPatchInput = {
      watch_date: data.watch_date,
      verified: data.verified,
    }
    mutation.mutate(payload)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <Tooltip>
        <TooltipTrigger asChild>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon">
              <Pencil className="size-4" />
            </Button>
          </DialogTrigger>
        </TooltipTrigger>
        <TooltipContent>
          <p>Edit watch</p>
        </TooltipContent>
      </Tooltip>
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Watch</DialogTitle>
              <DialogDescription>
                Update the watch entry details below.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="watch_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Watch Date</FormLabel>
                    <FormControl>
                      <Input type="datetime-local" step="0.001" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="verified"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Verified?</FormLabel>
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

export default EditWatch
