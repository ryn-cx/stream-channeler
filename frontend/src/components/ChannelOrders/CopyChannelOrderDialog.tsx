// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ChannelOrdersService } from "@/client"
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
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface CopyChannelOrderDialogProps {
  order: { id: string; name?: string | null }
  open: boolean
  onOpenChange: (open: boolean) => void
}

// TODO: Validate
export function CopyChannelOrderDialog({
  order,
  open,
  onOpenChange,
}: CopyChannelOrderDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [name, setName] = useState(
    order.name ? `Copy of ${order.name}` : "Copied order",
  )

  const mutation = useMutation({
    mutationFn: () =>
      ChannelOrdersService.copyChannelOrder({
        channelOrderId: order.id,
        requestBody: { name: name.trim() === "" ? null : name.trim() },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channel-orders"] })
      showSuccessToast("Order copied to your account")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Copy Channel Order</DialogTitle>
          <DialogDescription>
            Save a private copy of this order to your account. The copy is a
            snapshot and won't change if the original is edited.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="py-2">
          <div className="space-y-1.5">
            <Label htmlFor="copy-order-name">Name</Label>
            <Input
              id="copy-order-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
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
            Save Copy
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
