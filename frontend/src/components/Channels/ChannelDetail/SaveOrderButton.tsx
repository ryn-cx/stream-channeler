// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Save } from "lucide-react"

import { ChannelsService } from "@/client"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import useCustomToast from "@/hooks/useCustomToast"

interface SaveOrderButtonProps {
  channelId: string
  episodes: { id: string }[]
  variant?: "button" | "menu" | "icon"
}

export function SaveOrderButton({
  channelId,
  episodes,
  variant = "button",
}: SaveOrderButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateChannelOrder({
        channelId,
        requestBody: { episode_ids: episodes.map((episode) => episode.id) },
      }),
    onSuccess: () => {
      showSuccessToast("Order saved")
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      showErrorToast(`Could not save order: ${message}`)
    },
  })

  const save = () => mutation.mutate()

  return (
    <VariantTrigger
      variant={variant}
      icon={Save}
      label="Save Order"
      iconTitle="Save Order"
      onClick={save}
      onSelect={save}
      disabled={mutation.isPending || episodes.length === 0}
    />
  )
}
