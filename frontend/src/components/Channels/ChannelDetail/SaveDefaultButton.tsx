// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Save } from "lucide-react"
import { useState } from "react"

import { ChannelsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface SaveDefaultButtonProps {
  channelId: string
  searchParams: Record<string, unknown>
  variant?: "button" | "menu"
}

export function SaveDefaultButton({
  channelId,
  searchParams,
  variant = "button",
}: SaveDefaultButtonProps) {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const saveDefaultsMutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateChannelDefaultOrder({
        channelId,
        requestBody: searchParams,
      }),
    onSuccess: () => {
      showSuccessToast("Default order saved successfully")
    },
    onError: handleError.bind(showErrorToast),
  })

  const buttonLabel = saveDefaultsMutation.isPending
    ? "Saving..."
    : "Save as Default"

  return (
    <>
      <VariantTrigger
        variant={variant}
        icon={Save}
        label={buttonLabel}
        menuLabel="Save as Default"
        disabled={saveDefaultsMutation.isPending}
        onClick={() => setConfirmOpen(true)}
        onSelect={(event) => {
          event.preventDefault()
          setConfirmOpen(true)
        }}
      />
      {confirmOpen && (
        <ConfirmDialog
          open={confirmOpen}
          onOpenChange={setConfirmOpen}
          title="Save as Default"
          description="This will overwrite the current default order for this channel. Are you sure?"
          confirmLabel="Save"
          variant="default"
          onConfirm={() => saveDefaultsMutation.mutate()}
        />
      )}
    </>
  )
}
