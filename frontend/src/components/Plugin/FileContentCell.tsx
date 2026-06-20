// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"

import { FilesService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface FileContentCellProps {
  fileId: string
}

export function FileContentCell({ fileId }: FileContentCellProps) {
  const [isOpen, setIsOpen] = useState(false)
  const { data, isFetching } = useQuery({
    queryKey: ["files", fileId],
    queryFn: () => FilesService.getFile({ fileId }),
    enabled: isOpen,
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs">
          Show content
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>File Content</DialogTitle>
        </DialogHeader>
        {isFetching ? (
          <span className="text-muted-foreground text-sm">Loading...</span>
        ) : (
          <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap wrap-break-word rounded-md bg-muted p-4 text-sm">
            {data?.content ?? "-"}
          </pre>
        )}
      </DialogContent>
    </Dialog>
  )
}
