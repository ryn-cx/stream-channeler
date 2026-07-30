// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { ApiError, UserCreate } from "@/client"
import { UsersService } from "@/client"
import { AddButton } from "@/components/Common/AddButton"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import { Checkbox } from "@/components/ui/checkbox"
import { DialogTrigger } from "@/components/ui/dialog"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const formSchema = z
  .object({
    email: z.email({ message: "Invalid email address" }),
    username: z.string().min(1, "Username is required"),
    password: z
      .string()
      .min(1, { message: "Password is required" })
      .min(8, { message: "Password must be at least 8 characters" }),
    confirm_password: z
      .string()
      .min(1, { message: "Please confirm your password" }),
    is_superuser: z.boolean(),
    is_active: z.boolean(),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "The passwords don't match",
    path: ["confirm_password"],
  })

type FormData = z.infer<typeof formSchema>

const AddUser = () => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      email: "",
      username: "",
      password: "",
      confirm_password: "",
      is_superuser: false,
      is_active: false,
    },
  })

  const mutation = useMutation({
    mutationKey: ["users", "create"],
    mutationFn: (data: UserCreate) =>
      UsersService.createUser({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User created successfully")
    },
    onError: (err) => {
      handleError.call(showErrorToast, err as ApiError)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const onSubmit = (data: FormData) => {
    const { confirm_password: _, ...userCreate } = data
    setIsOpen(false)
    form.reset()
    mutation.mutate(userCreate)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <DialogTrigger asChild>
          <AddButton>Add User</AddButton>
        </DialogTrigger>
      }
      title="Add User"
      description="Fill in the form below to add a new user to the system."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Email"
        placeholder="Email"
        type="email"
        required
      />

      <FormTextField
        control={form.control}
        label="Username"
        placeholder="Username"
        type="text"
      />

      <FormTextField
        control={form.control}
        name="password"
        label="Set Password"
        placeholder="Password"
        type="password"
        required
      />

      <FormTextField
        control={form.control}
        label="Confirm Password"
        placeholder="Password"
        type="password"
        required
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
    </FormModal>
  )
}

export default AddUser
