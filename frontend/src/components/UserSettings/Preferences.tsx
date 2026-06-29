import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { UsersService, type UserUpdateMe } from "@/client"
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
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

// This needs to stay in sync with the value in the backend.
const SERVER_SIDE_THRESHOLD_MAXIMUM = 100_000

const formSchema = z.object({
  server_side_threshold: z
    .number({ message: "Enter a number" })
    .int()
    .min(0, { message: "Must be 0 or greater" })
    .max(SERVER_SIDE_THRESHOLD_MAXIMUM, {
      message: `Must be ${SERVER_SIDE_THRESHOLD_MAXIMUM.toLocaleString()} or less`,
    }),
})

type FormData = z.infer<typeof formSchema>

const Preferences = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { user: currentUser } = useAuth()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      server_side_threshold: currentUser?.server_side_threshold ?? 10000,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: UserUpdateMe) =>
      UsersService.updateUserMe({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Preferences updated successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate({ server_side_threshold: data.server_side_threshold })
  }

  return (
    <div className="max-w-md">
      <h3 className="text-lg font-semibold py-4">Preferences</h3>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
        >
          <FormField
            control={form.control}
            name="server_side_threshold"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Server-side filtering threshold</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    min={0}
                    max={SERVER_SIDE_THRESHOLD_MAXIMUM}
                    step={1}
                    name={field.name}
                    ref={field.ref}
                    value={Number.isNaN(field.value) ? "" : field.value}
                    onBlur={field.onBlur}
                    onChange={(event) =>
                      field.onChange(event.target.valueAsNumber)
                    }
                  />
                </FormControl>
                <FormDescription>
                  Tables with at least this many entries are filtered and sorted
                  on the server. Smaller tables are loaded in full and filtered
                  in your browser.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <LoadingButton
            type="submit"
            loading={mutation.isPending}
            disabled={!form.formState.isDirty}
          >
            Save
          </LoadingButton>
        </form>
      </Form>
    </div>
  )
}

export default Preferences
