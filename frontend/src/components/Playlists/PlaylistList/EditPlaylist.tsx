// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"

import {
  type PlaylistOutput,
  PlaylistsService,
  type Visibility,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"
import { handleError } from "@/utils"

interface EditPlaylistProps {
  playlist: PlaylistOutput
}

const EditPlaylist = ({ playlist }: EditPlaylistProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState(playlist.name ?? "")
  const [visibility, setVisibility] = useState<Visibility>(
    playlist.visibility ?? "private",
  )
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: () =>
      PlaylistsService.updatePlaylist({
        playlistId: playlist.id,
        requestBody: {
          name: name.trim() || null,
          visibility,
        },
      }),
    onSuccess: () => {
      showSuccessToast("Playlist updated")
      queryClient.invalidateQueries({ queryKey: ["playlists"] })
      queryClient.invalidateQueries({ queryKey: ["playlist", playlist.id] })
      setIsOpen(false)
    },
    onError: (error) => {
      handleError.call(showErrorToast, error as any)
    },
  })

  const onOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      setName(playlist.name ?? "")
      setVisibility(playlist.visibility ?? "private")
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <Button
        variant="ghost"
        size="icon"
        title="Edit playlist"
        onClick={() => setIsOpen(true)}
      >
        <Pencil className="size-4" />
      </Button>
      <DialogContent className="sm:max-w-md">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate()
          }}
        >
          <DialogHeader>
            <DialogTitle>Edit Playlist</DialogTitle>
            <DialogDescription>
              Rename the playlist or change who can see it.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1">
              <Label htmlFor={`playlist-name-${playlist.id}`}>Name</Label>
              <Input
                id={`playlist-name-${playlist.id}`}
                autoFocus
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="(untitled)"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={`playlist-visibility-${playlist.id}`}>
                Visibility
              </Label>
              <Select
                value={visibility}
                onValueChange={(value) => setVisibility(value as Visibility)}
              >
                <SelectTrigger id={`playlist-visibility-${playlist.id}`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {VISIBILITY_OPTIONS.map((option) => (
                    <SelectItem key={option} value={option}>
                      {visibilityLabel(option)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsOpen(false)}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
            <LoadingButton type="submit" loading={mutation.isPending}>
              Save
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default EditPlaylist
