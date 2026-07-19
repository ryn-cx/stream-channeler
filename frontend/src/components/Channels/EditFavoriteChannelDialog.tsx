// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { type ChannelListOutput, ChannelsService } from "@/client"
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

interface EditFavoriteChannelDialogProps {
  channel: ChannelListOutput
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Lets a viewer set their own name/number for a channel they favorited, without
// changing the shared channel that its owner controls. Empty fields fall back to
// the channel's own values wherever the customization is displayed.
export function EditFavoriteChannelDialog({
  channel,
  open,
  onOpenChange,
}: EditFavoriteChannelDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const [name, setName] = useState(channel.custom_name ?? "")
  const [channelNumber, setChannelNumber] = useState(
    channel.custom_channel_number == null
      ? ""
      : String(channel.custom_channel_number),
  )

  const mutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateFavoriteChannel({
        channelId: channel.id,
        requestBody: {
          name: name.trim() === "" ? null : name.trim(),
          channel_number:
            channelNumber === "" ? null : Number.parseFloat(channelNumber),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels", "favorites"] })
      showSuccessToast("Channel personalized")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Personalize Channel</DialogTitle>
          <DialogDescription>
            Set your own name and number for this favorite. Only you see these;
            the channel's own details are left unchanged.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="flex flex-col gap-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="favorite-channel-name">Name</Label>
            <Input
              id="favorite-channel-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={channel.name ?? "Optional"}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="favorite-channel-number">Channel Number</Label>
            <Input
              id="favorite-channel-number"
              type="number"
              value={channelNumber}
              onChange={(event) => setChannelNumber(event.target.value)}
              placeholder={
                channel.channel_number == null
                  ? "Optional"
                  : String(channel.channel_number)
              }
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
