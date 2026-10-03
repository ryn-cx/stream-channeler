// TODO: Validate
import type { VideoStoreTitleSourceOutput } from "@/client"
import { ReportIssueForm } from "@/components/ChannelCommon/ReportIssueForm"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

// TODO: Validate
function sourceLabel(source: VideoStoreTitleSourceOutput): string {
  return source.name
    ? `${source.source_key} · ${source.name}`
    : source.source_key
}

// TODO: Validate
export function ReportIssueDialog({
  open,
  onOpenChange,
  sources,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  sources: VideoStoreTitleSourceOutput[]
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Report an issue</DialogTitle>
          <DialogDescription>
            Tell us which website is wrong and what is wrong with it.
          </DialogDescription>
        </DialogHeader>

        <DialogBody>
          <ReportIssueForm
            sources={sources.map((source) => ({
              titleId: source.title_id,
              label: sourceLabel(source),
            }))}
            actions={
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
            }
            onSent={() => onOpenChange(false)}
          />
        </DialogBody>
      </DialogContent>
    </Dialog>
  )
}
