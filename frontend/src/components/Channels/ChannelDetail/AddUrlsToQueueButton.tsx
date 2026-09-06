// TODO: Validate
import { Maximize2, Minimize2, MonitorCog } from "lucide-react"
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
import { useSearchablePlugins } from "@/hooks/useEntities"
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
}

// TODO: Validate
export function ManageTitlesButton({
  channelId,
  channelName,
  variant = "button",
  showLabel,
  combinedChannels,
}: ManageTitlesButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isFullScreen, setIsFullScreen] = useState(false)
  // Warm the searchable-plugins cache only once the modal is open, so the
  // channel list doesn't fetch it for every card just by rendering.
  useSearchablePlugins(isOpen)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
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
      <ModalContent
        size={isFullScreen ? "full" : "3xl"}
        className={
          isFullScreen
            ? "max-h-none h-[calc(100dvh-2rem)] flex flex-col"
            : "max-h-[85vh] flex flex-col"
        }
      >
        <DialogHeader className="px-8">
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

        {/*
          Opposite the close, since the two do the same kind of thing to the
          window rather than to what is in it. Last of the children rather than
          first: an opening window puts the cursor on whatever it finds first,
          and a tooltip taken as read on the way in says nothing to anybody.
        */}
        <TooltipIconButton
          label={isFullScreen ? "Shrink to a window" : "Fill the screen"}
          icon={isFullScreen ? <Minimize2 /> : <Maximize2 />}
          size="icon-sm"
          className="absolute left-4 top-4 z-10"
          onClick={() => setIsFullScreen(!isFullScreen)}
        />
      </ModalContent>
    </Dialog>
  )
}
