// TODO: Validate
import { useEffect, useState } from "react"

import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface EpisodeExpiryDialogProps {
  open: boolean
  title: string
  description: string
  dateLabel: string
  confirmLabel: string
  /** Pre-filled expiry as a datetime-local input value. */
  initialExpiry: string
  /** Called with the chosen datetime-local value ("" = never expires). */
  onConfirm: (expiresAtLocal: string) => void
  onOpenChange: (open: boolean) => void
}

// The same "ask for an optional expiry date" popup used when blacklisting an episode
// from an episode card, reused for the manage-whitelist menu.
export function EpisodeExpiryDialog({
  open,
  title,
  description,
  dateLabel,
  confirmLabel,
  initialExpiry,
  onConfirm,
  onOpenChange,
}: EpisodeExpiryDialogProps) {
  const [expiresAtLocal, setExpiresAtLocal] = useState(initialExpiry)

  // Reset the field whenever the dialog opens for a (new) episode.
  useEffect(() => {
    if (open) setExpiresAtLocal(initialExpiry)
  }, [open, initialExpiry])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <ModalContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <DialogBody className="flex flex-col gap-2 py-2">
          <Label htmlFor="episode-expiry">{dateLabel}</Label>
          <Input
            id="episode-expiry"
            type="datetime-local"
            value={expiresAtLocal}
            onChange={(event) => setExpiresAtLocal(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Leave empty to never expire.
          </p>
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              onConfirm(expiresAtLocal)
              onOpenChange(false)
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
