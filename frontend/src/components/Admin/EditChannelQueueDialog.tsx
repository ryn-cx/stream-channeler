// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  type ChannelQueueAdminOutput,
  ChannelsService,
  type URLStatus,
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
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

const STATUS_OPTIONS: URLStatus[] = [
  "Pending",
  "Failed",
  "Imported",
  "Importing",
]

interface EditChannelQueueDialogProps {
  queueEntry: ChannelQueueAdminOutput
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditChannelQueueDialog({
  queueEntry,
  open,
  onOpenChange,
}: EditChannelQueueDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const [status, setStatus] = useState<URLStatus>(queueEntry.status)
  const [note, setNote] = useState(queueEntry.note ?? "")

  const mutation = useMutation({
    mutationFn: () =>
      ChannelsService.adminUpdateChannelQueue({
        queueId: queueEntry.id,
        requestBody: {
          status,
          note: note.trim() === "" ? null : note.trim(),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-channel-queues"] })
      showSuccessToast("Queue entry updated successfully")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Queue Entry</DialogTitle>
          <DialogDescription className="break-all">
            {queueEntry.url}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="edit-queue-status">Status</Label>
            <Select
              value={status}
              onValueChange={(value) => setStatus(value as URLStatus)}
            >
              <SelectTrigger id="edit-queue-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Set to Pending to re-queue the URL for import.
            </p>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-queue-note">Note</Label>
            <Textarea
              id="edit-queue-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Optional"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <LoadingButton
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
          >
            Save Changes
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
