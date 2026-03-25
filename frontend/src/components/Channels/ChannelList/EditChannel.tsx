// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type ChannelOutput,
  type ChannelPatchInput,
  type ChannelsListOutput,
  ChannelsService,
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
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z.object({
  name: z.string().min(1, { message: "Name is required" }),
  channel_number: z.number().int().nullable().optional(),
  default_order: z.string().optional(),
  public: z.boolean(),
})

type FormData = z.infer<typeof formSchema>

interface EditChannelProps {
  channel: ChannelOutput
  externalOpen?: boolean
  onExternalClose?: () => void
}

const EditChannel = ({
  channel,
  externalOpen,
  onExternalClose,
}: EditChannelProps) => {
  const [internalOpen, setInternalOpen] = useState(false)
  const isOpen = externalOpen ?? internalOpen
  const setIsOpen = (open: boolean) => {
    if (externalOpen !== undefined) {
      if (!open) onExternalClose?.()
    } else {
      setInternalOpen(open)
    }
  }
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: channel.name ?? "",
      channel_number: channel.channel_number ?? null,
      public: channel.public ?? false,
      // TODO: This will be made to always be a string in the future so the extra check
      // can be removed eventually.
      default_order: channel.default_order ?? "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: ChannelPatchInput) =>
      ChannelsService.updateUserChannel({
        channelId: channel.id,
        requestBody: data,
      }),
    // When mutate is called:
    onMutate: async (newData, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({ queryKey: ["channels"] })

      // Snapshot the previous value
      const previousChannels = context.client.getQueryData<ChannelsListOutput>([
        "channels",
      ])

      // Optimistically update to the new value
      context.client.setQueryData<ChannelsListOutput>(["channels"], (old) => {
        if (!old) return old
        return {
          ...old,
          data: old.data.map((c) =>
            c.id === channel.id ? { ...c, ...newData } : c,
          ),
        }
      })

      // Return a result with the snapshotted value
      return { previousChannels }
    },
    onSuccess: () => {
      showSuccessToast("Channel updated successfully")
      setIsOpen(false)
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _newData, onMutateResult, context) => {
      context.client.setQueryData(
        ["channels"],
        onMutateResult?.previousChannels,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({ queryKey: ["channels"] }),
  })

  const onSubmit = (data: FormData) => {
    const payload: ChannelPatchInput = {
      name: data.name,
      channel_number: data.channel_number ?? null,
      public: data.public,
      default_order: data.default_order || null,
    }
    mutation.mutate(payload)
  }

  return (
    <>
      {externalOpen === undefined && (
        <Button
          variant="ghost"
          size="icon"
          title="Edit channel"
          onClick={() => setIsOpen(true)}
        >
          <Pencil className="size-4" />
        </Button>
      )}
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent className="sm:max-w-md">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)}>
                <DialogHeader>
                  <DialogTitle>Edit Channel</DialogTitle>
                  <DialogDescription>
                    Update the channel details below.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Name <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Channel name"
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
                    name="channel_number"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Channel Number</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            placeholder="Optional"
                            {...field}
                            value={field.value ?? ""}
                            onChange={(e) =>
                              field.onChange(
                                e.target.value === ""
                                  ? null
                                  : Number.parseInt(e.target.value, 10),
                              )
                            }
                          />
                        </FormControl>
                        <FormDescription>
                          Used for sorting channels in the browse view
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="default_order"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Default Order</FormLabel>
                        <FormDescription>
                          It's easier to set this from the channel page
                        </FormDescription>
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
                        <FormLabel className="font-normal">
                          Is public?
                        </FormLabel>
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
      )}
    </>
  )
}

export default EditChannel
