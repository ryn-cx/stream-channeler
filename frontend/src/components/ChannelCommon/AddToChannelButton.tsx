// TODO: Validate
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { Check, Plus } from "lucide-react"

import {
  type ChannelListOutput,
  ChannelsService,
  type ShowPublic,
} from "@/client"
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

// A TMDB result's URL is the title's own TMDB page, so it names the same title
// as a channel show's `TMDB tv 123` identifier even when the channel holds that
// title from some other service.
const TMDB_TITLE_URL_PATTERN = /themoviedb\.org\/(tv|movie)\/(\d+)/

// Which channel was picked last, so the next title starts on it. One channel is
// usually filled in a sitting, and the pick is a convenience rather than
// anything the server has to be told about.
const LAST_CHANNEL_KEY = "add-to-channel:last-channel-id"

// TODO: Validate
function channelCarriesShow(
  shows: ShowPublic[],
  showId: string,
  showUrl: string | null,
) {
  if (shows.some((show) => show.id === showId)) return true
  if (showUrl == null) return false
  if (shows.some((show) => show.url === showUrl)) return true
  const match = TMDB_TITLE_URL_PATTERN.exec(showUrl)
  if (match == null) return false
  const tmdbId = Number(match[2])
  return shows.some((show) => show.tmdb_id === tmdbId)
}

interface AddToChannelButtonProps {
  showId: string
  showUrl: string | null
}

// TODO: Validate
export function AddToChannelButton({
  showId,
  showUrl,
}: AddToChannelButtonProps) {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const loggedIn = isLoggedIn()
  const [selectedChannelId, setSelectedChannelId] = usePersistedState(
    LAST_CHANNEL_KEY,
    "",
  )

  const { data: channelsData, isLoading: isLoadingChannels } = useQuery({
    queryKey: ["channels"],
    queryFn: () => ChannelsService.getChannels({ scope: "owned" }),
    enabled: loggedIn,
    refetchOnWindowFocus: false,
  })
  const channels: ChannelListOutput[] = channelsData?.data ?? []

  const showQueries = useQueries({
    queries: channels.map((channel) => ({
      queryKey: ["channel-shows", channel.id],
      queryFn: () => ChannelsService.getChannelShows({ channelId: channel.id }),
      enabled: loggedIn,
      refetchOnWindowFocus: false,
    })),
  })

  const carriedByChannelId = new Map(
    channels.map((channel, index) => {
      const query = showQueries[index]
      return [
        channel.id,
        query?.data != null &&
          channelCarriesShow(query.data.shows ?? [], showId, showUrl),
      ]
    }),
  )

  const addMutation = useMutation({
    mutationFn: (channelId: string) =>
      ChannelsService.addChannelShow({ channelId, showId }),
    onSuccess: (result, channelId) => {
      showSuccessToast(result.message)
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
  const selectedCarries = carriedByChannelId.get(selectedChannelId) === true

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
                {carriedByChannelId.get(channel.id) && (
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
