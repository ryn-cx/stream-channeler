// TODO: Validate
import { MonitorCog } from "lucide-react"
import { useState } from "react"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { VariantTrigger } from "@/components/Common/VariantTrigger"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useSearchablePlugins } from "@/hooks/useEntities"
import { ManageShowsTabs } from "./ManageShowsTabs"

interface ManageShowsButtonProps {
  channelId: string
  channelName?: string | null
  variant?: "button" | "menu" | "icon"
  showLabel?: boolean
  /** When provided, adds an owner-only "Combined Channels" tab to the modal. */
  combinedChannels?: {
    isLoggedIn?: boolean
  }
}

// TODO: Validate
export function ManageShowsButton({
  channelId,
  channelName,
  variant = "button",
  showLabel,
  combinedChannels,
}: ManageShowsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  // Warm the searchable-plugins cache only once the modal is open, so the
  // channel list doesn't fetch it for every card just by rendering.
  useSearchablePlugins(isOpen)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {variant === "icon" ? (
          <TooltipIconButton
            label="Manage shows"
            icon={<MonitorCog className="size-4" />}
            showLabel={showLabel}
          />
        ) : (
          <VariantTrigger
            variant={variant}
            icon={MonitorCog}
            label="Manage shows"
            iconTitle="Manage shows"
          />
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-5xl max-h-[85vh] flex flex-col">
        <DialogHeader className="px-8">
          <DialogTitle>
            {channelName ? `Manage ${channelName} Shows` : "Manage Shows"}
          </DialogTitle>
          <DialogDescription>
            Search, import, and manage shows in your channel.
          </DialogDescription>
        </DialogHeader>

        <ManageShowsTabs
          channelId={channelId}
          contentClassName="no-scrollbar max-h-[50vh] overflow-y-auto px-8 py-4"
          tabsListClassName="mx-8 flex-wrap h-auto"
          combinedChannels={combinedChannels}
          onRequestClose={() => setIsOpen(false)}
        />

        <DialogFooter className="px-8">
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
