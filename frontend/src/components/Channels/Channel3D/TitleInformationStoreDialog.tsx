// TODO: Validate
import type { VideoStoreTitleSourceOutput } from "@/client"
import { TitleInformationPanel } from "@/components/ChannelCommon/TitleInformationDialog"
import { ModalContent } from "@/components/Common/ModalContent"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogBody,
  DialogDescription,
  DialogFooter,
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
/**
 * Everything the shelf knows about a title, read as the title itself is read
 * everywhere else.
 *
 * A title a website splits up, or one several websites list, is read once per
 * row rather than as one account standing for the rest.
 */
export function TitleInformationStoreDialog({
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
      <ModalContent size="full">
        <DialogHeader>
          <DialogTitle>Title Information</DialogTitle>
          <DialogDescription>
            What each website and TMDB say about this title.
          </DialogDescription>
        </DialogHeader>

        <DialogBody className="flex flex-col gap-8 overflow-x-auto">
          {sources.map((source) => (
            <div key={source.title_id} className="flex flex-col gap-2">
              {sources.length > 1 && (
                <h3 className="font-medium">{sourceLabel(source)}</h3>
              )}
              <TitleInformationPanel titleId={source.title_id} enabled={open} />
            </div>
          ))}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </ModalContent>
    </Dialog>
  )
}
