// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { ChannelOrdersService, type Visibility } from "@/client"
import { EmojiPicker } from "@/components/Common/EmojiPicker"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import { serializeOrderConfig } from "@/lib/channelOrder"
import {
  VISIBILITY_OPTIONS,
  visibilityDescription,
  visibilityLabel,
} from "@/lib/visibility"
import { handleError } from "@/utils"

interface CreateChannelOrderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// TODO: Validate
export function CreateChannelOrderDialog({
  open,
  onOpenChange,
}: CreateChannelOrderDialogProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [icon, setIcon] = useState<string | null>(null)
  const [visibility, setVisibility] = useState<Visibility>("private")
  const [anonymous, setAnonymous] = useState(false)

  const mutation = useMutation({
    mutationFn: () =>
      ChannelOrdersService.createChannelOrder({
        requestBody: {
          name: name.trim() === "" ? null : name.trim(),
          description: description.trim() === "" ? null : description.trim(),
          visibility,
          anonymous,
          icon,
          // A new order starts empty; its sorting is configured by applying and
          // saving it from a channel's sorting options.
          config: serializeOrderConfig({ sortBy: [] }),
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channel-orders"] })
      showSuccessToast("Order created")
      onOpenChange(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Order</DialogTitle>
          <DialogDescription>
            Create an empty order, then set its sorting from a channel's sorting
            options.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="flex flex-col gap-4 py-2">
          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="create-order-name">Name</Label>
              <Input
                id="create-order-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="My order"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="create-order-icon">Icon</Label>
              <EmojiPicker
                id="create-order-icon"
                value={icon}
                onChange={setIcon}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="create-order-description">Description</Label>
            <Textarea
              id="create-order-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Optional"
              className="max-h-40 overflow-y-auto"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="create-order-visibility">Visibility</Label>
            <Select
              value={visibility}
              onValueChange={(value) => setVisibility(value as Visibility)}
            >
              <SelectTrigger id="create-order-visibility">
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
              id="create-order-anonymous"
              checked={anonymous}
              onCheckedChange={(checked) => setAnonymous(checked === true)}
            />
            <Label htmlFor="create-order-anonymous" className="font-normal">
              Publish anonymously
            </Label>
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
            Create Order
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
