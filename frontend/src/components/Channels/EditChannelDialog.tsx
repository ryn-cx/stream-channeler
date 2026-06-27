// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import {
  type ChannelAdminOutput,
  type ChannelOutput,
  ChannelsService,
  type Visibility,
} from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import { Textarea } from "@/components/ui/textarea"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import {
  VISIBILITY_OPTIONS,
  visibilityDescription,
  visibilityLabel,
} from "@/lib/visibility"
import { handleError } from "@/utils"

interface EditChannelDialogProps {
  channel: ChannelOutput | ChannelAdminOutput
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EditChannelDialog({
  channel,
  open,
  onOpenChange,
}: EditChannelDialogProps) {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  // Only admins can see or change the score; regular users can never touch it.
  const isAdmin = user?.is_superuser ?? false

  const [name, setName] = useState(channel.name ?? "")
  const [channelNumber, setChannelNumber] = useState(
    channel.channel_number == null ? "" : String(channel.channel_number),
  )
  const [visibility, setVisibility] = useState<Visibility>(channel.visibility)
  const [description, setDescription] = useState(channel.description ?? "")
  const [anonymous, setAnonymous] = useState(channel.anonymous ?? false)
  // Score is admin-only. `0` hides the channel from the public list; `1` or higher
  // lists it publicly, with higher scores shown first.
  const [score, setScore] = useState(String(channel.score ?? 0))
  // The admin endpoint returns the owner's username on the channel; for an owner
  // editing their own channel it falls back to the logged-in user.
  const creatorName = "username" in channel ? channel.username : user?.username

  const mutation = useMutation({
    mutationFn: () => {
      const base = {
        name: name.trim() === "" ? null : name.trim(),
        channel_number:
          channelNumber === "" ? null : Number.parseFloat(channelNumber),
        visibility,
        description: description.trim() === "" ? null : description.trim(),
        anonymous,
      }
      // Admins go through the admin endpoint so they can edit any channel and set
      // the score; everyone else uses the owner endpoint, which has no score.
      return isAdmin
        ? ChannelsService.adminUpdateChannel({
            channelId: channel.id,
            requestBody: {
              ...base,
              score: Math.max(0, Number.parseInt(score, 10) || 0),
            },
          })
        : ChannelsService.updateChannel({
            channelId: channel.id,
            requestBody: base,
          })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      queryClient.invalidateQueries({ queryKey: ["admin-channels"] })
      showSuccessToast("Channel updated successfully")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Channel</DialogTitle>
          <DialogDescription>
            Update this channel's details. Manage its shows and sort order from
            the channel itself.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="edit-channel-name">Name</Label>
            <Input
              id="edit-channel-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-channel-number">Channel Number</Label>
            <Input
              id="edit-channel-number"
              type="number"
              value={channelNumber}
              onChange={(event) => setChannelNumber(event.target.value)}
              placeholder="Optional"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-channel-description">Description</Label>
            <Textarea
              id="edit-channel-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="edit-channel-visibility">Visibility</Label>
            <Select
              value={visibility}
              onValueChange={(value) => setVisibility(value as Visibility)}
            >
              <SelectTrigger id="edit-channel-visibility">
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
            <p className="text-sm text-muted-foreground">
              {visibilityDescription(visibility)}
            </p>
          </div>
          <div className="flex items-start gap-3">
            <Checkbox
              id="edit-channel-anonymous"
              checked={anonymous}
              onCheckedChange={(checked) => setAnonymous(checked === true)}
            />
            <div className="space-y-1 leading-none">
              <Label htmlFor="edit-channel-anonymous" className="font-normal">
                Publish anonymously
              </Label>
              <p className="text-sm text-muted-foreground">
                The creator of the channel will be listed as{" "}
                {anonymous ? "anonymous" : creatorName}.
              </p>
            </div>
          </div>
          {isAdmin && (
            <div className="space-y-1.5">
              <Label htmlFor="edit-channel-score">Score</Label>
              <Input
                id="edit-channel-score"
                type="number"
                min={0}
                step={1}
                value={score}
                onChange={(event) => setScore(event.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                0 hides the channel from the public list. 1 or higher lists it
                publicly, with higher scores shown first.
              </p>
            </div>
          )}
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
