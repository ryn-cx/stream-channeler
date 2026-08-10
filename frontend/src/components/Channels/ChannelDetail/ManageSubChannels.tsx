// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, X } from "lucide-react"
import { useEffect, useState } from "react"

import {
  type ChannelListOutput,
  ChannelsService,
  type CombinedChannelOutput,
} from "@/client"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface AdditionalChannelsPanelProps {
  channelId: string
  isLoggedIn?: boolean
  /** Called after a successful save, e.g. to close the surrounding modal. */
  onSaved?: () => void
}

export function AdditionalChannelsPanel({
  channelId,
  isLoggedIn = false,
  onSaved,
}: AdditionalChannelsPanelProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const [channelPickerOpen, setChannelPickerOpen] = useState(false)
  const [manualChannelId, setManualChannelId] = useState<string>("")
  const [localChannels, setLocalChannels] = useState<CombinedChannelOutput[]>(
    [],
  )
  const [initialized, setInitialized] = useState(false)

  // The channel's currently saved combined channels.
  const { data: combinedData } = useQuery({
    queryKey: ["channel-combined-channels", channelId],
    queryFn: () => ChannelsService.getChannelCombinedChannels({ channelId }),
  })

  useEffect(() => {
    if (combinedData && !initialized) {
      setLocalChannels(combinedData)
      setInitialized(true)
    }
  }, [combinedData, initialized])

  // Channels owned by the user, used by the picker.
  const { data: channelsData, isLoading: isLoadingChannels } = useQuery({
    queryKey: ["channels"],
    queryFn: () => ChannelsService.getChannels({ scope: "owned" }),
    enabled: isLoggedIn,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  })
  const channels = channelsData?.data ?? []

  const localIds = new Set(localChannels.map((channel) => channel.id))
  const selectableChannels = channels.filter(
    (channel: ChannelListOutput) =>
      channel.id !== channelId && !localIds.has(channel.id),
  )

  const mutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateChannelCombinedChannels({
        channelId,
        requestBody: localChannels.map((channel) => ({ id: channel.id })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["channel-combined-channels", channelId],
      })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
      showSuccessToast("Combined channels updated successfully")
      onSaved?.()
    },
    onError: handleError.bind(showErrorToast),
  })

  const addChannel = (channel: CombinedChannelOutput) => {
    if (channel.id === channelId || localIds.has(channel.id)) return
    setLocalChannels([...localChannels, channel])
  }

  const handleAddFromInput = () => {
    if (!manualChannelId) return
    addChannel({ id: manualChannelId, name: null })
    setManualChannelId("")
  }

  const handleRemove = (idToRemove: string) => {
    setLocalChannels(
      localChannels.filter((channel) => channel.id !== idToRemove),
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold">Combined Channels</h3>
        <p className="text-xs text-muted-foreground">
          Combine other channels into this one. Their episodes are shown here
          whenever anyone views this channel.
        </p>
      </div>

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
              <Popover
                open={channelPickerOpen}
                onOpenChange={setChannelPickerOpen}
              >
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    className="flex-1 justify-start"
                  >
                    Select a channel
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className="w-[--radix-popover-trigger-width] p-0"
                  align="start"
                  onWheel={(event) => event.stopPropagation()}
                >
                  <Command>
                    <CommandInput placeholder="Filter channels..." />
                    <CommandList>
                      <CommandEmpty>No channels found.</CommandEmpty>
                      <CommandGroup>
                        {selectableChannels.map(
                          (channel: ChannelListOutput) => (
                            <CommandItem
                              key={channel.id}
                              value={channel.name ?? channel.id}
                              keywords={[channel.id]}
                              onSelect={() => {
                                addChannel({
                                  id: channel.id,
                                  name: channel.name ?? null,
                                })
                                setChannelPickerOpen(false)
                              }}
                            >
                              {channel.name}
                            </CommandItem>
                          ),
                        )}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            )}
          </div>
        )}

        <form
          onSubmit={(event) => {
            event.preventDefault()
            handleAddFromInput()
          }}
          className="flex items-center gap-4"
        >
          <Label>By Channel ID</Label>
          <Input
            placeholder="Enter channel ID"
            value={manualChannelId}
            onChange={(event) => setManualChannelId(event.target.value)}
            className="flex-1"
          />
          <Button type="submit" size="sm" disabled={!manualChannelId}>
            <Plus className="h-4 w-4" />
          </Button>
        </form>

        {localChannels.length > 0 && (
          <div className="space-y-2 mt-2">
            <Label className="text-xs text-muted-foreground">
              Combined channels:
            </Label>
            {localChannels.map((channel) => (
              <div
                key={channel.id}
                className="flex items-center justify-between gap-3 p-2 border rounded text-sm"
              >
                <span className="text-xs">{channel.name || channel.id}</span>
                <div className="flex items-center gap-3">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRemove(channel.id)}
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

      <div className="flex justify-end">
        <Button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Saving..." : "Save"}
        </Button>
      </div>
    </div>
  )
}
