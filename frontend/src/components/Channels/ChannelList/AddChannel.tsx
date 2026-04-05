// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type ChannelPostInput,
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
  DialogTrigger,
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
  channel_number: z.number().nullable().optional(),
  default_order: z.string().optional(),
  public: z.boolean(),
})

type FormData = z.infer<typeof formSchema>

const AddChannel = () => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
      channel_number: null,
      default_order: "",
      public: false,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: ChannelPostInput) =>
      ChannelsService.createUserChannel({ requestBody: data }),
    // When mutate is called:
    onMutate: async (newChannel, context) => {
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
          data: [
            ...old.data,
            {
              ...newChannel,
              id: "Loading...",
              user_id: "Loading...",
            },
          ],
        }
      })

      // Return a result with the snapshotted value
      return { previousChannels }
    },
    onSuccess: () => {
      showSuccessToast("Channel created successfully")
      form.reset()
      // setIsOpen(false);
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _newChannel, onMutateResult, context) => {
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
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button className="mt-2 mb-4">
          <Plus className="mr-2" />
          New Channel
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Channel</DialogTitle>
          <DialogDescription>
            Fill in the details to add a new channel.
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
                    <FormLabel>
                      Name <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Channel name"
                        type="text"
                        {...field}
                        required
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

export default AddChannel
