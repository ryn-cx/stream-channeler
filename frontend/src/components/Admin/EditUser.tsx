import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { ApiError } from "@/client"
import { type UserPublic, UsersService } from "@/client"
import type { UsersPublicWithPending } from "@/components/Admin/types"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
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
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z
  .object({
    email: z.email({ message: "Invalid email address" }),
    full_name: z.string().optional(),
    password: z
      .string()
      .min(8, { message: "Password must be at least 8 characters" })
      .optional()
      .or(z.literal("")),
    confirm_password: z.string().optional(),
    is_superuser: z.boolean().optional(),
    is_active: z.boolean().optional(),
  })
  .refine((data) => !data.password || data.password === data.confirm_password, {
    message: "The passwords don't match",
    path: ["confirm_password"],
  })

type FormData = z.infer<typeof formSchema>

interface EditUserProps {
  user: UserPublic
}

const EditUser = ({ user }: EditUserProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: user.email,
      full_name: user.full_name ?? undefined,
      is_superuser: user.is_superuser,
      is_active: user.is_active,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: Omit<FormData, "confirm_password">) =>
      UsersService.updateUser({ userId: user.id, requestBody: data }),
    // When mutate is called:
    onMutate: async (data) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["users"] })

      // Snapshot the previous value
      const previousUsers = queryClient.getQueriesData<UsersPublicWithPending>({
        queryKey: ["users"],
      })

      // Optimistically update to the new value
      queryClient.setQueriesData<UsersPublicWithPending>(
        { queryKey: ["users"] },
        (old) =>
          old
            ? {
                ...old,
                data: old.data.map((existingUser) =>
                  existingUser.id === user.id
                    ? { ...existingUser, ...data, pending: true }
                    : existingUser,
                ),
              }
            : old,
      )

      // Return a result with the snapshotted value
      return { previousUsers }
    },
    onSuccess: (data) => {
      showSuccessToast("User updated successfully")
      queryClient.setQueriesData<UsersPublicWithPending>(
        { queryKey: ["users"] },
        (old) =>
          old
            ? {
                ...old,
                data: old.data.map((existingUser) =>
                  existingUser.id === data.id ? data : existingUser,
                ),
              }
            : old,
      )
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (err, _variables, context) => {
      for (const [queryKey, data] of context?.previousUsers ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      handleError.call(showErrorToast, err as ApiError)
    },
    // Always refetch after error or success:
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  })

  const onSubmit = (data: FormData) => {
    // exclude confirm_password from submission data and remove password if empty
    const { confirm_password: _, ...userUpdate } = data
    if (!userUpdate.password) delete userUpdate.password
    setIsOpen(false)
    mutation.mutate(userUpdate)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <TooltipIconButton
        label="Edit User"
        icon={<Pencil />}
        onClick={() => setIsOpen(true)}
      />
      <DialogContent className="sm:max-w-md">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit User</DialogTitle>
              <DialogDescription>
                Update the user details below.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormTextField
                control={form.control}
                name="email"
                label="Email"
                placeholder="Email"
                type="email"
                required
              />

              <FormTextField
                control={form.control}
                name="full_name"
                label="Full Name"
                placeholder="Full name"
                type="text"
              />

              <FormTextField
                control={form.control}
                name="password"
                label="Set Password"
                placeholder="Password"
                type="password"
              />

              <FormTextField
                control={form.control}
                name="confirm_password"
                label="Confirm Password"
                placeholder="Password"
                type="password"
              />

              <FormField
                control={form.control}
                name="is_superuser"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Is superuser?</FormLabel>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="is_active"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                    <FormLabel className="font-normal">Is active?</FormLabel>
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

export default EditUser
