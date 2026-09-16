// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Hammer, Lock } from "lucide-react"
import { useEffect, useState } from "react"
import { ChannelsService } from "@/client"
import { SourceOptionLabel } from "@/components/Common/SourceOptionLabel"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { invalidateChannelTitles, TitleSearch } from "./Search"

// TODO: Validate
function BuildButton({
  channelId,
  tmdbTitleId,
}: {
  channelId: string
  tmdbTitleId?: string | null
}) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<string[]>([])

  const { data: plugins, isPending: pluginsPending } = useQuery({
    queryKey: ["channel-build-plugins", channelId, tmdbTitleId],
    queryFn: () =>
      ChannelsService.getChannelBuildPlugins({
        channelId,
        titleId: tmdbTitleId as string,
      }),
    enabled: open && Boolean(tmdbTitleId),
  })

  useEffect(() => {
    if (plugins) setSelected(plugins.map((plugin) => plugin.key))
  }, [plugins])

  const buildMutation = useMutation({
    mutationFn: (titleId: string) =>
      ChannelsService.buildChannelFromTitle({
        channelId,
        titleId,
        requestBody: selected,
      }),
    onSuccess: (message) => {
      showSuccessToast(message.message)
      invalidateChannelTitles(queryClient, channelId)
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
  })

  if (!tmdbTitleId) {
    return (
      <Button
        size="sm"
        variant="secondary"
        className="mt-2 w-full"
        disabled
        title="Nothing has imported this title yet, so there is nothing to build from"
      >
        <Lock className="h-3 w-3 mr-1" />
        Not Imported
      </Button>
    )
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          size="sm"
          className="mt-2 w-full"
          onClick={(event) => event.stopPropagation()}
        >
          <Hammer className="h-3 w-3 mr-1" />
          Build
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-64 space-y-3"
        onClick={(event) => event.stopPropagation()}
      >
        <p className="text-sm font-medium">Build from</p>
        {pluginsPending ? (
          <p className="text-sm text-muted-foreground">Loading websites...</p>
        ) : plugins && plugins.length > 0 ? (
          <div className="flex flex-col gap-2">
            {plugins.map((plugin) => (
              <div key={plugin.key} className="flex items-center gap-2">
                <Checkbox
                  id={`build-plugin-${plugin.key}`}
                  checked={selected.includes(plugin.key)}
                  onCheckedChange={(checked) =>
                    setSelected((current) =>
                      checked
                        ? [...current, plugin.key]
                        : current.filter((key) => key !== plugin.key),
                    )
                  }
                />
                <Label
                  htmlFor={`build-plugin-${plugin.key}`}
                  className="font-normal"
                >
                  <SourceOptionLabel
                    name={plugin.key}
                    faviconUrl={plugin.favicon_url}
                  />
                </Label>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            No website linked to this title can say what is similar to it.
          </p>
        )}
        <Button
          size="sm"
          className="w-full"
          disabled={buildMutation.isPending || selected.length === 0}
          onClick={() => buildMutation.mutate(tmdbTitleId)}
        >
          <Hammer className="h-3 w-3 mr-1" />
          {buildMutation.isPending ? "Building..." : "Build"}
        </Button>
      </PopoverContent>
    </Popover>
  )
}

// TODO: Validate
export function BuilderPanel({ channelId }: { channelId: string }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Pick a show and automatically build a channel inspired by that show.
      </p>
      <TitleSearch
        channelId={channelId}
        placeholder="Search for a title to build from..."
        action={(title) => (
          <BuildButton
            channelId={channelId}
            tmdbTitleId={title.tmdb_title_id}
          />
        )}
      />
    </div>
  )
}
