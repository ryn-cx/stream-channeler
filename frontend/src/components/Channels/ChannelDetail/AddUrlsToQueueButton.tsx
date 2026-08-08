// TODO: Validate
import { MonitorCog, Plus } from "lucide-react"
import { useState } from "react"
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
  variant?: "button" | "menu" | "icon"
  /** When provided, adds an owner-only "Combined Channels" tab to the modal. */
  combinedChannels?: {
    isLoggedIn?: boolean
  }
}

export function ManageShowsButton({
  channelId,
  variant = "button",
  combinedChannels,
}: ManageShowsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  // Editing shows lays a title's whole filter out inline, which needs the page
  // rather than the width the other tabs read comfortably at.
  const [isWide, setIsWide] = useState(false)
  useSearchablePlugins()

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <VariantTrigger
          variant={variant}
          icon={MonitorCog}
          iconVariantIcon={Plus}
          label="Shows"
          iconTitle="Manage shows"
        />
      </DialogTrigger>
      <DialogContent
        className={`${
          isWide ? "sm:max-w-[calc(100%-2rem)]" : "sm:max-w-5xl"
        } max-h-[85vh] flex flex-col`}
      >
        <DialogHeader className="px-8">
          <DialogTitle>Manage Shows</DialogTitle>
          <DialogDescription>
            Search, import, and manage shows in your channel.
          </DialogDescription>
        </DialogHeader>

        <ManageShowsTabs
          channelId={channelId}
          contentClassName="overflow-y-auto flex-1 min-h-0 px-8 py-4"
          tabsListClassName="mx-8 flex-wrap h-auto"
          combinedChannels={combinedChannels}
          onRequestClose={() => setIsOpen(false)}
          onActiveTabChange={(tab) => setIsWide(tab === "shows")}
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
