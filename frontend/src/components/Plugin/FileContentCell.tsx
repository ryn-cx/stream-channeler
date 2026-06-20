// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"

import { FilesService } from "@/client"
import { JsonViewer } from "@/components/Common/JsonViewer"
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

  const content = data?.content ?? null
  // Try to parse as JSON so it can be shown as a collapsible tree; fall back to
  // raw text for anything that isn't JSON (e.g. HTML/XML scrapes).
  const parsedJson = useMemo(() => {
    if (content === null) return undefined
    try {
      return { value: JSON.parse(content) as unknown }
    } catch {
      return undefined
    }
  }, [content])

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 px-2 text-xs">
          Show content
        </Button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[90vh] flex-col sm:max-w-5xl lg:max-w-6xl">
        <DialogHeader>
          <DialogTitle>File Content</DialogTitle>
        </DialogHeader>
        {isFetching ? (
          <span className="text-muted-foreground text-sm">Loading...</span>
        ) : parsedJson ? (
          <JsonViewer value={parsedJson.value} />
        ) : (
          <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap wrap-break-word rounded-md bg-muted p-4 text-sm">
            {content ?? "-"}
          </pre>
        )}
      </DialogContent>
    </Dialog>
  )
}
