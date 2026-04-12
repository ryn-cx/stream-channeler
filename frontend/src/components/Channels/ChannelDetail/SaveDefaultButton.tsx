// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Save } from "lucide-react"
import { useState } from "react"

import { ChannelsService } from "@/client"
import { ConfirmDialog } from "@/components/Common/ConfirmDialog"
import { Button } from "@/components/ui/button"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
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

  if (variant === "menu") {
    return (
      <>
        <DropdownMenuItem
          onSelect={(e) => {
            e.preventDefault()
            setConfirmOpen(true)
          }}
          disabled={saveDefaultsMutation.isPending}
        >
          <Save className="mr-2 size-4" />
          Save as Default
        </DropdownMenuItem>
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

  return (
    <>
      <Button
        onClick={() => setConfirmOpen(true)}
        disabled={saveDefaultsMutation.isPending}
        className="mt-2 mb-4"
      >
        <Save className="mr-2" />
        {saveDefaultsMutation.isPending ? "Saving..." : "Save as Default"}
      </Button>
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
