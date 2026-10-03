// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Trash2 } from "lucide-react"
import { useEffect, useState } from "react"

import { EpisodesService } from "@/client"
import { ExternalAnchor } from "@/components/ChannelCommon/InformationTable"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import useAuth from "@/hooks/useAuth"
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
  const [confirmingRemoval, setConfirmingRemoval] = useState(false)
  const queryClient = useQueryClient()
  const { user } = useAuth()
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

  // What is saved here is saved against the reader, so there is nothing to show
  // and nowhere to put it until there is a reader to save it against.
  if (!user) return null

  return (
    <div className="flex flex-col gap-2 rounded border p-3">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-medium">Custom Media</span>
        <p className="text-sm text-muted-foreground">
          A custom URL is private to you and allows you to add links to episodes
          that are not supported by Stream Channeler.
        </p>
      </div>

      {userUrl === null ? (
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
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm">
          <span className="min-w-0 flex-1 break-all">
            {isWebAddress(userUrl) ? (
              <ExternalAnchor href={userUrl} label={userUrl} />
            ) : (
              userUrl
            )}
          </span>
          <TooltipIconButton
            label="Remove this custom URL"
            icon={<Trash2 />}
            className="text-destructive hover:text-destructive"
            disabled={isPending}
            onClick={() => setConfirmingRemoval(true)}
          />
        </div>
      )}

      <ConfirmDialog
        open={confirmingRemoval}
        onOpenChange={setConfirmingRemoval}
        title="Remove Custom URL"
        description="This episode will go back to having no custom URL of yours. You can save another one afterwards."
        confirmLabel="Remove"
        onConfirm={() => clearMutation.mutate()}
      />
    </div>
  )
}
