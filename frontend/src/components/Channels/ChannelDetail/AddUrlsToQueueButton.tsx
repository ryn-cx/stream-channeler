// TODO: Validate
import { MonitorCog } from "lucide-react"
import { useState } from "react"
import { ModalContent } from "@/components/Common/ModalContent"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { ManageTitlesTabs } from "./ManageTitlesTabs"

interface ManageTitlesButtonProps {
  channelId: string
  channelName?: string | null
  variant?: "button" | "menu" | "icon"
  showLabel?: boolean
  /** When provided, adds an owner-only "Combined Channels" tab to the modal. */
  combinedChannels?: {
    isLoggedIn?: boolean
  }
  open?: boolean
  onOpenChange?: (open: boolean) => void
  hideTrigger?: boolean
}

// TODO: Validate
export function ManageTitlesButton({
  channelId,
  channelName,
  variant = "button",
  showLabel,
  combinedChannels,
  open,
  onOpenChange,
  hideTrigger,
}: ManageTitlesButtonProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const isOpen = open ?? internalOpen
  const setIsOpen = onOpenChange ?? setInternalOpen
  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {!hideTrigger && (
        <DialogTrigger asChild>
          {variant === "icon" ? (
            <TooltipIconButton
              label="Manage titles"
              icon={<MonitorCog className="size-4" />}
              showLabel={showLabel}
            />
          ) : (
            <VariantTrigger
              variant={variant}
              icon={MonitorCog}
              label="Manage titles"
              iconTitle="Manage titles"
            />
          )}
        </DialogTrigger>
      )}
      <ModalContent size="3xl">
        <DialogHeader>
          <DialogTitle>
            {channelName ? `Manage ${channelName} Titles` : "Manage Titles"}
          </DialogTitle>
          <DialogDescription>
            Search, import, and manage titles in your channel.
          </DialogDescription>
        </DialogHeader>

        <ManageTitlesTabs
          channelId={channelId}
          contentClassName="no-scrollbar flex-1 min-h-0 overflow-y-auto px-8 py-4"
          tabsListClassName="mx-4 h-auto"
          combinedChannels={combinedChannels}
          onRequestClose={() => setIsOpen(false)}
        />

        <DialogFooter className="px-8">
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
