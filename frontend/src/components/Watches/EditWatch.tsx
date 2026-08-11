// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import {
  type WatchesListOutput,
  WatchesService,
  type WatchItem,
  type WatchOutput,
  type WatchUpdate,
} from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DialogTrigger } from "@/components/ui/dialog"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
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

// TODO: Validate
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
    mutationFn: (data: WatchUpdate) =>
      WatchesService.updateWatch({
        watchId: watch.id,
        requestBody: data,
      }),
    // When mutate is called:
    onMutate: async (data, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["watches"] })

      // Snapshot the previous value
      const previousWatches = context.client.getQueryData<WatchesListOutput>([
        "watches",
      ])

      // Optimistically update the watch.
      context.client.setQueryData<WatchesListOutput>(["watches"], (old) => {
        if (!old) return old
        return {
          ...old,
          watches: old.watches.map((w) =>
            w.id === watch.id
              ? ({ ...w, ...data, pending: true } as WatchItem)
              : w,
          ),
        }
      })

      // Return a result with the snapshotted value
      return { previousWatches }
    },
    onSuccess: (result: WatchOutput[]) => {
      const message =
        result.length > 1
          ? `${result.length} watches updated successfully`
          : "Watch updated successfully"
      showSuccessToast(message)
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

  // TODO: Validate
  const onSubmit = (data: FormData) => {
    setIsOpen(false)
    const payload: WatchUpdate = {
      watch_date: data.watch_date,
      verified: data.verified,
    }
    mutation.mutate(payload)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
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
      }
      title="Edit Watch"
      description="Update the watch entry details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Watch Date"
        type="datetime-local"
        step="0.001"
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
    </FormModal>
  )
}

export default EditWatch
