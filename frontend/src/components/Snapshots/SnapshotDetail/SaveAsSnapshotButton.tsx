// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { ListPlus } from "lucide-react"
import { useState } from "react"

import {
  type EpisodeWithDetails,
  SnapshotsService,
  type Visibility,
} from "@/client"
import { ModalContent } from "@/components/Common/ModalContent"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import useCustomToast from "@/hooks/useCustomToast"
import { VISIBILITY_OPTIONS, visibilityLabel } from "@/lib/visibility"

interface SaveAsSnapshotButtonProps {
  episodes: EpisodeWithDetails[]
  variant?: "button" | "menu" | "icon"
}

export function SaveAsSnapshotButton({
  episodes,
  variant = "button",
}: SaveAsSnapshotButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState("")
  const [visibility, setVisibility] = useState<Visibility>("private")

  const mutation = useMutation({
    mutationFn: () =>
      SnapshotsService.createSnapshot({
        requestBody: {
          name: name.trim() || null,
          visibility,
          episode_ids: episodes.map((episode) => episode.id),
        },
      }),
    onSuccess: (snapshot) => {
      showSuccessToast("Snapshot saved")
      queryClient.invalidateQueries({ queryKey: ["snapshots"] })
      setIsOpen(false)
      setName("")
      setVisibility("private")
      navigate({
        to: "/snapshots/$snapshotId",
        params: { snapshotId: snapshot.id },
      })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not save snapshot: ${message}`)
    },
  })

  const onOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (!open) {
      setName("")
      setVisibility("private")
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <VariantTrigger
          variant={variant}
          icon={ListPlus}
          label="Save as Snapshot"
          iconTitle="Save as Snapshot"
        />
      </DialogTrigger>
      <ModalContent>
        <DialogHeader>
          <DialogTitle>Save as Snapshot</DialogTitle>
          <DialogDescription>
            Snapshot the current episode order ({episodes.length} episode
            {episodes.length === 1 ? "" : "s"}) as a new snapshot.
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
            <Label htmlFor="snapshot-name">Name</Label>
            <Input
              id="snapshot-name"
              autoFocus
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Optional name for the snapshot"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="snapshot-visibility">Visibility</Label>
            <Select
              value={visibility}
              onValueChange={(value) => setVisibility(value as Visibility)}
            >
              <SelectTrigger id="snapshot-visibility">
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
      </ModalContent>
    </Dialog>
  )
}
