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
  DialogBody,
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
  const [importAt, setImportAt] = useState(
    queueEntry.import_at?.slice(0, 16) ?? "",
  )

  const mutation = useMutation({
    mutationFn: () =>
      ChannelsService.adminUpdateChannelQueue({
        queueId: queueEntry.id,
        requestBody: {
          status,
          note: note.trim() === "" ? null : note.trim(),
          import_at: importAt === "" ? null : importAt,
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

        <DialogBody className="flex flex-col gap-4 py-2">
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
            <Label htmlFor="edit-queue-import-at">Import At</Label>
            <Input
              id="edit-queue-import-at"
              type="datetime-local"
              value={importAt}
              onChange={(event) => setImportAt(event.target.value)}
            />
            <p className="text-sm text-muted-foreground">
              The URL is not imported before this time. Clear it to import on
              the next run.
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
        </DialogBody>

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
