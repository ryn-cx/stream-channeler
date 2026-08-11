// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil, Trash2 } from "lucide-react"
import { useState } from "react"

import { type ChannelQueueAdminOutput, ChannelsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { EditChannelQueueDialog } from "./EditChannelQueueDialog"

// TODO: Validate
export function ChannelQueueActions({
  queueEntry,
}: {
  queueEntry: ChannelQueueAdminOutput
}) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [isEditing, setIsEditing] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () =>
      ChannelsService.adminDeleteChannelQueue({ queueId: queueEntry.id }),
    onSuccess: () => {
      showSuccessToast("Queue entry removed successfully")
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-channel-queues"] }),
  })

  return (
    <div className="flex justify-end gap-2">
      <Button
        variant="outline"
        size="icon-sm"
        onClick={() => setIsEditing(true)}
      >
        <Pencil />
      </Button>
      <Button
        variant="outline"
        size="icon-sm"
        className="text-destructive hover:text-destructive"
        onClick={() => setIsDeleting(true)}
      >
        <Trash2 />
      </Button>

      {isEditing && (
        <EditChannelQueueDialog
          queueEntry={queueEntry}
          open={isEditing}
          onOpenChange={setIsEditing}
        />
      )}

      <ConfirmDialog
        open={isDeleting}
        onOpenChange={setIsDeleting}
        title="Delete Queue Entry"
        description={`Remove "${queueEntry.url}" from the import queue? This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={() => deleteMutation.mutate()}
      />
    </div>
  )
}
