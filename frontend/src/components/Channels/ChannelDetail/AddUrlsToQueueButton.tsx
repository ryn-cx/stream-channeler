// TODO: Validate
import { MonitorCog, Plus } from "lucide-react"
import { useState } from "react"
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
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import { ManageShowsTabs } from "./ManageShowsTabs"

interface ManageShowsButtonProps {
  channelId: string
  variant?: "button" | "menu" | "icon"
}

export function ManageShowsButton({
  channelId,
  variant = "button",
}: ManageShowsButtonProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {variant === "menu" ? (
          <DropdownMenuItem
            onSelect={(e) => {
              e.preventDefault()
            }}
          >
            <MonitorCog className="mr-2 size-4" />
            Shows
          </DropdownMenuItem>
        ) : variant === "icon" ? (
          <Button variant="ghost" size="icon" title="Manage shows">
            <Plus className="size-4" />
          </Button>
        ) : (
          <Button className="mt-2 mb-4">
            <MonitorCog className="mr-2" />
            Shows
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-5xl max-h-[85vh] flex flex-col">
        <DialogHeader className="px-8">
          <DialogTitle>Manage Shows</DialogTitle>
          <DialogDescription>
            Search, import, and manage shows in your channel.
          </DialogDescription>
        </DialogHeader>

        <ManageShowsTabs
          channelId={channelId}
          contentClassName="overflow-y-auto flex-1 min-h-0 px-8 py-4"
          tabsListClassName="mx-8"
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
