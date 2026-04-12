// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { ChevronDown, ChevronUp, Plus, TvMinimal, X } from "lucide-react"
import { useState } from "react"

import { getChannelEpisodes } from "@/api/channels"
import { type ChannelOutput, ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
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
import { handleError } from "@/utils"

interface ManageChannelsProps {
  channelId: string
  filterParams: { additionalChannels?: string[] }
  routeFullPath: string
  currentChannelIds?: string[]
  isLoggedIn?: boolean
  variant?: "button" | "menu"
}

export function ManageAdditionalChannels({
  filterParams,
  routeFullPath,
  currentChannelIds = [],
  isLoggedIn = false,
  channelId,
  variant = "button",
}: ManageChannelsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [manualChannelId, setManualChannelId] = useState<string>("")
  const [localAdditionalChannelIds, setLocalAdditionalChannelIds] = useState<
    string[]
  >([])

  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  // Channels that are owned by the user
  const { data: channelsData, isLoading: isLoadingChannels } = useQuery({
    queryKey: ["channels"],
    queryFn: () => ChannelsService.getChannels(),
    enabled: isOpen && isLoggedIn,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  })
  const channels = channelsData ?? []

  const channelNames = channels.reduce(
    (acc: Record<string, string>, channel: ChannelOutput) => {
      acc[channel.id] = channel.name ?? ""
      return acc
    },
    {} as Record<string, string>,
  )

  // Channels that the user owns that are not already in the chosen additional channels
  const selectableChannels = channels.filter(
    (channel: ChannelOutput) =>
      !currentChannelIds.includes(channel.id) &&
      !localAdditionalChannelIds.includes(channel.id),
  )

  const additionalChannelIds = currentChannelIds.slice(1)

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      setLocalAdditionalChannelIds([...additionalChannelIds])
    }
  }

  const mutation = useMutation({
    mutationFn: (newSearch: Record<string, any>) =>
      getChannelEpisodes({
        channelId,
        ...newSearch,
      }),
    onSuccess: (newData, newSearch) => {
      queryClient.setQueryData(["episodes", channelId], newData)
      setIsOpen(false)
      navigate({ to: routeFullPath, search: newSearch as any, replace: true })
      showSuccessToast("Channels updated successfully")
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleAddChannelFromSelect = (channelIdToAdd: string) => {
    if (!channelIdToAdd || localAdditionalChannelIds.includes(channelIdToAdd))
      return

    setLocalAdditionalChannelIds([...localAdditionalChannelIds, channelIdToAdd])
  }

  const handleAddChannelFromInput = () => {
    if (!manualChannelId || localAdditionalChannelIds.includes(manualChannelId))
      return

    setLocalAdditionalChannelIds([
      ...localAdditionalChannelIds,
      manualChannelId,
    ])
    setManualChannelId("")
  }

  const handleRemoveChannel = (channelIdToRemove: string) => {
    setLocalAdditionalChannelIds(
      localAdditionalChannelIds.filter((id) => id !== channelIdToRemove),
    )
  }

  const moveChannel = (index: number, direction: "up" | "down") => {
    const newIds = [...localAdditionalChannelIds]
    const targetIndex = direction === "up" ? index - 1 : index + 1

    ;[newIds[index], newIds[targetIndex]] = [newIds[targetIndex], newIds[index]]

    setLocalAdditionalChannelIds(newIds)
  }

  const handleSave = () => {
    const newSearch: Record<string, any> = {
      ...filterParams,
      additionalChannels:
        localAdditionalChannelIds.length > 0
          ? localAdditionalChannelIds
          : undefined,
    }

    mutation.mutate(newSearch)
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        {variant === "menu" ? (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault()
            }}
          >
            <TvMinimal className="mr-2 size-4" />
            Additional Channels
          </DropdownMenuItem>
        ) : (
          <Button className="mt-2 mb-4">
            <TvMinimal className="mr-2" />
            Manage Additional Channels
          </Button>
        )}
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Manage Additional Channels</DialogTitle>
          <DialogDescription>
            Add or remove additional channels to combine with this channel
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <h3>Add Channels</h3>
          <div className="space-y-2">
            {isLoggedIn && (
              <div className="flex items-center gap-4">
                <Label>From Your Channels</Label>
                {isLoadingChannels ? (
                  <p className="text-sm text-muted-foreground flex-1">
                    Loading channels...
                  </p>
                ) : selectableChannels.length === 0 ? (
                  <p className="text-sm text-muted-foreground flex-1">
                    No additional channels available
                  </p>
                ) : (
                  <Select
                    value=""
                    onValueChange={(value) => {
                      if (!localAdditionalChannelIds.includes(value)) {
                        handleAddChannelFromSelect(value)
                      }
                    }}
                  >
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select a channel" />
                    </SelectTrigger>
                    <SelectContent>
                      {selectableChannels.map((channel: ChannelOutput) => (
                        <SelectItem key={channel.id} value={channel.id}>
                          {channel.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleAddChannelFromInput()
              }}
              className="flex items-center gap-4"
            >
              <Label>By Channel ID</Label>
              <Input
                placeholder="Enter channel ID"
                value={manualChannelId}
                onChange={(e) => setManualChannelId(e.target.value)}
                className="flex-1"
              />
              <Button type="submit" size="sm" disabled={!manualChannelId}>
                <Plus className="h-4 w-4" />
              </Button>
            </form>

            {/* This was mostly copied from the EpisodeFilters component for simplicity */}
            {localAdditionalChannelIds.length > 0 && (
              <div className="space-y-2 mt-2">
                <Label className="text-xs text-muted-foreground">
                  Added Channels:
                </Label>
                {localAdditionalChannelIds.map((channelId, index) => (
                  <div
                    key={channelId}
                    className="flex items-center justify-between p-2 border rounded text-sm"
                  >
                    <span
                      className={`text-xs ${!channelNames[channelId] ? "text-destructive" : ""}`}
                    >
                      {channelNames[channelId] || "Invalid Channel"}
                    </span>
                    <div className="flex items-center gap-1">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => moveChannel(index, "up")}
                        disabled={index === 0}
                        className="h-6 w-6 p-0"
                      >
                        <ChevronUp className="h-3 w-3" />
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => moveChannel(index, "down")}
                        disabled={
                          index === localAdditionalChannelIds.length - 1
                        }
                        className="h-6 w-6 p-0"
                      >
                        <ChevronDown className="h-3 w-3" />
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemoveChannel(channelId)}
                        className="h-6 w-6 p-0 text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
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
              type="button"
              onClick={handleSave}
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}
