// TODO: Validate
import { Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { DialogTrigger } from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface DeleteIconTriggerProps {
  tooltip: string
}

export function DeleteIconTrigger({ tooltip }: DeleteIconTriggerProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <DialogTrigger asChild>
          <Button variant="ghost">
            <Trash2 className="text-destructive" />
          </Button>
        </DialogTrigger>
      </TooltipTrigger>
      <TooltipContent>
        <p>{tooltip}</p>
      </TooltipContent>
    </Tooltip>
  )
}
