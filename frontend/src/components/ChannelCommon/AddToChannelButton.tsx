// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Plus } from "lucide-react"

import { ChannelsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const loggedIn = isLoggedIn()
  const [selectedChannelId, setSelectedChannelId] = usePersistedState(
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

  // A channel the title is already on is still selectable, so the pick that was
  // remembered is not silently dropped; it is the button that says there is
  // nothing left to do.
  const selectedCarries = channels.some(
    (channel) => channel.id === selectedChannelId && channel.carries_show,
  )

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select value={selectedChannelId} onValueChange={setSelectedChannelId}>
        <SelectTrigger className="w-56" size="sm">
          <SelectValue
            placeholder={
              isLoadingChannels ? "Loading channels..." : "Choose a channel"
            }
          />
        </SelectTrigger>
        <SelectContent>
          {channels.map((channel) => (
            <SelectItem key={channel.id} value={channel.id}>
              <span className="flex items-center gap-2">
                <span className="truncate">{channel.name ?? channel.id}</span>
                {channel.carries_show && (
                  <span className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                    <Check className="h-3 w-3" />
                    Already added
                  </span>
                )}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
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
