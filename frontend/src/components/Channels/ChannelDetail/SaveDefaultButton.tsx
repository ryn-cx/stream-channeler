// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { Save } from "lucide-react"

import { ChannelsService } from "@/client"
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

  const saveDefaultsMutation = useMutation({
    mutationFn: () =>
      ChannelsService.updateUserChannelDefaultOrder({
        channelId,
        requestBody: searchParams,
      }),
    onSuccess: () => {
      showSuccessToast("Default order saved successfully")
    },
    onError: handleError.bind(showErrorToast),
  })

  const handleClick = () => {
    saveDefaultsMutation.mutate()
  }

  if (variant === "menu") {
    return (
      <DropdownMenuItem
        onSelect={(e) => {
          e.preventDefault()
          handleClick()
        }}
        disabled={saveDefaultsMutation.isPending}
      >
        <Save className="mr-2 size-4" />
        Save as Default
      </DropdownMenuItem>
    )
  }

  return (
    <Button
      onClick={handleClick}
      disabled={saveDefaultsMutation.isPending}
      className="mt-2 mb-4"
    >
      <Save className="mr-2" />
      {saveDefaultsMutation.isPending ? "Saving..." : "Save as Default"}
    </Button>
  )
}
