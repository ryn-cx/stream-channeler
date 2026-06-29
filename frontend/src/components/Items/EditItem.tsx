import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { ApiError } from "@/client"
import { type ItemPublic, ItemsService } from "@/client"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import type { ItemsPublicWithPending } from "@/components/Items/types"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Form } from "@/components/ui/form"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z.object({
  title: z.string().min(1, { message: "Title is required" }),
  description: z.string().optional(),
})

type FormData = z.infer<typeof formSchema>

interface EditItemProps {
  item: ItemPublic
}

const EditItem = ({ item }: EditItemProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      title: item.title,
      description: item.description ?? undefined,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      ItemsService.updateItem({ itemId: item.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (data) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["items"] })

      // Snapshot the previous value
      const previousItems = queryClient.getQueriesData<ItemsPublicWithPending>({
        queryKey: ["items"],
      })

      // Optimistically update to the new value
      queryClient.setQueriesData<ItemsPublicWithPending>(
        { queryKey: ["items"] },
        (old) =>
          old
            ? {
                ...old,
                data: old.data.map((existingItem) =>
                  existingItem.id === item.id
                    ? { ...existingItem, ...data, pending: true }
                    : existingItem,
                ),
              }
            : old,
      )

      // Return a result with the snapshotted value
      return { previousItems }
    },
    onSuccess: (data) => {
      showSuccessToast("Item updated successfully")
      queryClient.setQueriesData<ItemsPublicWithPending>(
        { queryKey: ["items"] },
        (old) =>
          old
            ? {
                ...old,
                data: old.data.map((existingItem) =>
                  existingItem.id === data.id ? data : existingItem,
                ),
              }
            : old,
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (err, _variables, context) => {
      for (const [queryKey, data] of context?.previousItems ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      handleError.call(showErrorToast, err as ApiError)
    },
    // Always refetch after error or success:
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["items"] }),
  })

  const onSubmit = (data: FormData) => {
    setIsOpen(false)
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <TooltipIconButton
        label="Edit Item"
        icon={<Pencil />}
        onClick={() => setIsOpen(true)}
      />
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Item</DialogTitle>
              <DialogDescription>
                Update the item details below.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormTextField
                control={form.control}
                name="title"
                label="Title"
                placeholder="Title"
                type="text"
                required
              />

              <FormTextField
                control={form.control}
                name="description"
                label="Description"
                placeholder="Description"
                type="text"
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

export default EditItem
