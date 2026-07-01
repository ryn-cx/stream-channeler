// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  type SnapshotAdminOutput,
  type SnapshotDetailOutput,
  SnapshotsService,
} from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import type { SnapshotTableData } from "@/components/Snapshots/SnapshotList/columns"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { DialogTrigger } from "@/components/ui/dialog"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { visibilityEnum } from "@/lib/formSchemas"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

const formSchema = z.object({
  name: z.string(),
  visibility: visibilityEnum,
  anonymous: z.boolean(),
  // Admin-only. `0` hides the snapshot from the public list; `1` or higher lists
  // it publicly, with higher scores shown first.
  score: z.string(),
})

type FormData = z.infer<typeof formSchema>

interface EditSnapshotProps {
  snapshot: SnapshotAdminOutput | SnapshotDetailOutput
  // When provided, the dialog is controlled by the parent (used by the admin
  // browse). Otherwise the component renders its own pencil trigger.
  open?: boolean
  onOpenChange?: (open: boolean) => void
  hideTrigger?: boolean
}

const EditSnapshot = ({
  snapshot,
  open,
  onOpenChange,
  hideTrigger = false,
}: EditSnapshotProps) => {
  const [internalOpen, setInternalOpen] = useState(false)
  const { user } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  // Only admins can see or change the score; regular users can never touch it.
  const isAdmin = user?.is_superuser ?? false

  const isControlled = open !== undefined
  const isOpen = isControlled ? open : internalOpen
  const setOpen = onOpenChange ?? setInternalOpen

  const defaultValues = (): FormData => ({
    name: snapshot.name ?? "",
    visibility: snapshot.visibility ?? "private",
    anonymous: snapshot.anonymous ?? false,
    score: String(snapshot.score ?? 0),
  })

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: defaultValues(),
  })

  const mutation = useMutation<
    SnapshotAdminOutput | SnapshotDetailOutput,
    Error,
    FormData,
    { previous: Array<SnapshotTableData> | undefined }
  >({
    mutationFn: (data: FormData) => {
      const base = {
        name: data.name.trim() || null,
        visibility: data.visibility,
        anonymous: data.anonymous,
      }
      // Admins go through the admin endpoint so they can edit any snapshot and
      // set the score; everyone else uses the owner endpoint, which has no score.
      return isAdmin
        ? SnapshotsService.adminUpdateSnapshot({
            snapshotId: snapshot.id,
            requestBody: {
              ...base,
              score: Math.max(0, Number.parseInt(data.score, 10) || 0),
            },
          })
        : SnapshotsService.updateSnapshot({
            snapshotId: snapshot.id,
            requestBody: base,
          })
    },
    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: ["snapshots"] })
      const previous = queryClient.getQueryData<Array<SnapshotTableData>>([
        "snapshots",
      ])
      queryClient.setQueryData<Array<SnapshotTableData>>(["snapshots"], (old) =>
        old?.map((existing) =>
          existing.id === snapshot.id
            ? {
                ...existing,
                name: data.name.trim() || null,
                visibility: data.visibility,
                pending: true,
              }
            : existing,
        ),
      )
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Snapshot updated")
      queryClient.invalidateQueries({ queryKey: ["snapshots"] })
      queryClient.invalidateQueries({ queryKey: ["snapshot", snapshot.id] })
    },
    onError: (error, _vars, context) => {
      queryClient.setQueryData(["snapshots"], context?.previous)
      handleError.call(showErrorToast, error as any)
    },
  })

  const handleOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (nextOpen) {
      form.reset(defaultValues())
    }
  }

  const onSubmit = (data: FormData) => {
    setOpen(false)
    mutation.mutate(data)
  }

  const creatorName =
    "username" in snapshot ? snapshot.username : user?.username

  const anonymous = form.watch("anonymous")

  return (
    <FormModal
      open={isOpen}
      onOpenChange={handleOpenChange}
      trigger={
        hideTrigger ? null : (
          <Tooltip>
            <TooltipTrigger asChild>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Pencil className="size-4" />
                </Button>
              </DialogTrigger>
            </TooltipTrigger>
            <TooltipContent>
              <p>Edit Snapshot</p>
            </TooltipContent>
          </Tooltip>
        )
      }
      title="Edit Snapshot"
      description="Rename the snapshot or change who can see it."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField
        control={form.control}
        label="Name"
        placeholder="(untitled)"
        type="text"
      />

      <FormField
        control={form.control}
        name="visibility"
        render={({ field }) => (
          <FormItem>
            <FormLabel>Visibility</FormLabel>
            <Select value={field.value} onValueChange={field.onChange}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                {VISIBILITY_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {visibilityLabel(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={form.control}
        name="anonymous"
        render={({ field }) => (
          <FormItem className="flex flex-row items-start gap-3 space-y-0">
            <FormControl>
              <Checkbox
                checked={field.value}
                onCheckedChange={(checked) => field.onChange(checked === true)}
              />
            </FormControl>
            <div className="space-y-1 leading-none">
              <FormLabel className="font-normal">Publish anonymously</FormLabel>
              <p className="text-sm text-muted-foreground">
                The creator of the snapshot will be listed as{" "}
                {anonymous ? "anonymous" : creatorName}.
              </p>
            </div>
          </FormItem>
        )}
      />

      {isAdmin && (
        <FormField
          control={form.control}
          name="score"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Score</FormLabel>
              <FormControl>
                <Input type="number" min={0} step={1} {...field} />
              </FormControl>
              <p className="text-sm text-muted-foreground">
                0 hides the snapshot from the public list. 1 or higher lists it
                publicly, with higher scores shown first.
              </p>
              <FormMessage />
            </FormItem>
          )}
        />
      )}
    </FormModal>
  )
}

export default EditSnapshot
