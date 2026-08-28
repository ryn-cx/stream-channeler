// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, ChevronsUpDown, Plus } from "lucide-react"
import { useState } from "react"

import { ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { isLoggedIn } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { usePersistedState } from "@/hooks/usePersistedState"
import { handleError } from "@/utils"

// Which channel was picked last, so the next title starts on it. One channel is
// usually filled in a sitting, and the pick is a convenience rather than
// anything the server has to be told about.
const LAST_CHANNEL_KEY = "add-to-channel:last-channel-id"

interface AddToChannelButtonProps {
  showId: string
}

// TODO: Validate
export function AddToChannelButton({ showId }: AddToChannelButtonProps) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const loggedIn = isLoggedIn()
  const [selectedChannelId, setSelectedChannelId] = usePersistedState<string>(
    LAST_CHANNEL_KEY,
    "",
  )

  const { data: channels = [], isLoading: isLoadingChannels } = useQuery({
    queryKey: ["channels-for-show", showId],
    queryFn: () => ChannelsService.getChannelsForShow({ showId }),
    enabled: loggedIn,
    refetchOnWindowFocus: false,
  })

  const addMutation = useMutation({
    mutationFn: (channelId: string) =>
      ChannelsService.addChannelShow({ channelId, showId }),
    onSuccess: (result, channelId) => {
      showSuccessToast(result.message)
      queryClient.invalidateQueries({ queryKey: ["channels-for-show"] })
      queryClient.invalidateQueries({ queryKey: ["channel-shows", channelId] })
      queryClient.invalidateQueries({ queryKey: ["episodes", channelId] })
    },
    onError: handleError.bind(showErrorToast),
  })

  if (!loggedIn) {
    return null
  }

  const selected = channels.find((channel) => channel.id === selectedChannelId)
  // A channel the title is already on is still selectable, so the pick that was
  // remembered is not silently dropped; it is the button that says there is
  // nothing left to do.
  const selectedCarries = selected?.carries_show === true
  // TODO: Validate
  const channelLabel = (channel: { name?: string | null; id: string }) =>
    channel.name ?? channel.id

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            role="combobox"
            aria-expanded={open}
            className="w-56 justify-between font-normal"
          >
            <span className="truncate">
              {selected
                ? channelLabel(selected)
                : isLoadingChannels
                  ? "Loading channels..."
                  : "Choose a channel"}
            </span>
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-56 p-0"
          align="start"
          onWheel={(event) => event.stopPropagation()}
        >
          {/* Typing filters by name, which is how a channel is looked for when
              there are more of them than a list is read down. */}
          <Command>
            <CommandInput placeholder="Filter channels..." />
            <CommandList>
              <CommandEmpty>No channels found.</CommandEmpty>
              <CommandGroup>
                {channels.map((channel) => (
                  <CommandItem
                    key={channel.id}
                    value={channelLabel(channel)}
                    keywords={[channel.id]}
                    onSelect={() => {
                      setSelectedChannelId(channel.id)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={`h-4 w-4 shrink-0${
                        channel.id === selectedChannelId
                          ? ""
                          : " text-transparent"
                      }`}
                    />
                    <span className="flex-1 truncate">
                      {channelLabel(channel)}
                    </span>
                    {channel.carries_show && (
                      <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                        Already added
                      </span>
                    )}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      <Button
        size="sm"
        disabled={
          !selectedChannelId || selectedCarries || addMutation.isPending
        }
        onClick={() => addMutation.mutate(selectedChannelId)}
      >
        {selectedCarries ? (
          <>
            <Check className="h-4 w-4 mr-1" />
            Already on this channel
          </>
        ) : (
          <>
            <Plus className="h-4 w-4 mr-1" />
            {addMutation.isPending ? "Adding..." : "Add to Channel"}
          </>
        )}
      </Button>
    </div>
  )
}
