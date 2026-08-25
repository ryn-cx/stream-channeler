// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import { EpisodesService } from "@/client"
import { ExternalAnchor } from "@/components/ChannelCommon/InformationTable"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

// TODO: Validate
function isWebAddress(value: string): boolean {
  return /^https?:\/\//i.test(value.trim())
}

interface EpisodeUserUrlSectionProps {
  episodeId: string
  userUrl: string | null
  informationQueryKey: unknown[]
}

// TODO: Validate
export function EpisodeUserUrlSection({
  episodeId,
  userUrl,
  informationQueryKey,
}: EpisodeUserUrlSectionProps) {
  const [draft, setDraft] = useState(userUrl ?? "")
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  useEffect(() => {
    setDraft(userUrl ?? "")
  }, [userUrl])

  const saveMutation = useMutation({
    mutationFn: () =>
      EpisodesService.setEpisodeUserUrl({
        episodeId,
        requestBody: { url: draft },
      }),
    onSuccess: () => {
      showSuccessToast("Episode link saved")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
    },
    onError: (error: unknown) => {
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    },
  })

  const clearMutation = useMutation({
    mutationFn: () => EpisodesService.deleteEpisodeUserUrl({ episodeId }),
    onSuccess: () => {
      showSuccessToast("Episode link removed")
      setDraft("")
      queryClient.invalidateQueries({ queryKey: informationQueryKey })
    },
    onError: (error: unknown) => {
      handleError.call(
        showErrorToast,
        error as Parameters<typeof handleError>[0],
      )
    },
  })

  const isPending = saveMutation.isPending || clearMutation.isPending

  return (
    <div className="flex flex-col gap-2 rounded border p-3">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-medium">Custom Media</span>
        <p className="text-sm text-muted-foreground">
          Offered under the Custom Media source, so it is ranked and filtered
          alongside every other source. Anything can be saved here, whether or
          not it is a web address.
        </p>
      </div>

      <div className="text-sm">
        {userUrl === null ? (
          <span className="text-muted-foreground">Nothing saved yet.</span>
        ) : isWebAddress(userUrl) ? (
          <ExternalAnchor href={userUrl} label={userUrl} />
        ) : (
          <span className="break-all">{userUrl}</span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Where you watch this episode"
          className="min-w-60 flex-1"
        />
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={isPending || !draft.trim()}
        >
          Save
        </Button>
        <Button
          variant="outline"
          onClick={() => clearMutation.mutate()}
          disabled={isPending || !userUrl}
        >
          Clear
        </Button>
      </div>
    </div>
  )
}
