// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { ListPlus } from "lucide-react"
import { useState } from "react"

import { type EpisodeWithExtrasOutput, PlaylistsService } from "@/client"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"

interface SaveAsPlaylistButtonProps {
  episodes: EpisodeWithExtrasOutput[]
  variant?: "button" | "menu" | "icon"
}

export function SaveAsPlaylistButton({
  episodes,
  variant = "button",
}: SaveAsPlaylistButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState("")
  const [isPublic, setIsPublic] = useState(false)

  const mutation = useMutation({
    mutationFn: () =>
      PlaylistsService.createPlaylist({
        requestBody: {
          name: name.trim() || null,
          public: isPublic,
          episode_ids: episodes.map((episode) => episode.id),
        },
      }),
    onSuccess: (playlist) => {
      showSuccessToast("Playlist saved")
      queryClient.invalidateQueries({ queryKey: ["playlists"] })
      setIsOpen(false)
      setName("")
      setIsPublic(false)
      navigate({
        to: "/playlists/$playlistId",
        params: { playlistId: playlist.id },
      })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not save playlist: ${message}`)
    },
  })

  const onOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (!open) {
      setName("")
      setIsPublic(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <VariantTrigger
          variant={variant}
          icon={ListPlus}
          label="Save as Playlist"
          iconTitle="Save as Playlist"
        />
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Save as Playlist</DialogTitle>
          <DialogDescription>
            Snapshot the current episode order ({episodes.length} episode
            {episodes.length === 1 ? "" : "s"}) as a new playlist.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate()
          }}
        >
          <div className="space-y-1">
            <Label htmlFor="playlist-name">Name</Label>
            <Input
              id="playlist-name"
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Optional name for the playlist"
            />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="playlist-public"
              checked={isPublic}
              onCheckedChange={(checked) => setIsPublic(checked === true)}
            />
            <Label htmlFor="playlist-public" className="cursor-pointer">
              Make this playlist public
            </Label>
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
            <Button
              type="submit"
              disabled={mutation.isPending || episodes.length === 0}
            >
              {mutation.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
