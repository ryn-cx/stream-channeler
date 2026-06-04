// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type PlaylistOutput, PlaylistsService } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextField } from "@/components/Common/FormTextField"
import type { PlaylistTableData } from "@/components/Playlists/PlaylistList/columns"
import { Button } from "@/components/ui/button"
import { DialogTrigger } from "@/components/ui/dialog"
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
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
import useCustomToast from "@/hooks/useCustomToast"
import { visibilityEnum } from "@/lib/formSchemas"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

const formSchema = z.object({
  name: z.string(),
  visibility: visibilityEnum,
})

type FormData = z.infer<typeof formSchema>

interface EditPlaylistProps {
  playlist: PlaylistOutput
}

const EditPlaylist = ({ playlist }: EditPlaylistProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: playlist.name ?? "",
      visibility: playlist.visibility ?? "private",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      PlaylistsService.updatePlaylist({
        playlistId: playlist.id,
        requestBody: {
          name: data.name.trim() || null,
          visibility: data.visibility,
        },
      }),
    // When mutate is called:
    onMutate: async (data) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["playlists"] })
      // Snapshot the previous value
      const previous = queryClient.getQueryData<Array<PlaylistTableData>>([
        "playlists",
      ])
      // Optimistically update to the new value
      queryClient.setQueryData<Array<PlaylistTableData>>(["playlists"], (old) =>
        old?.map((p) =>
          p.id === playlist.id
            ? {
                ...p,
                name: data.name.trim() || null,
                visibility: data.visibility,
                pending: true,
              }
            : p,
        ),
      )
      // Return a result with the snapshotted value
      return { previous }
    },
    onSuccess: () => {
      showSuccessToast("Playlist updated")
      queryClient.invalidateQueries({ queryKey: ["playlists"] })
      queryClient.invalidateQueries({ queryKey: ["playlist", playlist.id] })
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _vars, context) => {
      queryClient.setQueryData(["playlists"], context?.previous)
      handleError.call(showErrorToast, error as any)
    },
  })

  const onOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      form.reset({
        name: playlist.name ?? "",
        visibility: playlist.visibility ?? "private",
      })
    }
  }

  const onSubmit = (data: FormData) => {
    setIsOpen(false)
    mutation.mutate(data)
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={onOpenChange}
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
            <p>Edit Playlist</p>
          </TooltipContent>
        </Tooltip>
      }
      title="Edit Playlist"
      description="Rename the playlist or change who can see it."
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
    </FormModal>
  )
}

export default EditPlaylist
