// TODO: Validate
import { type ComponentProps, useState } from "react"

import { WhitelistManager } from "@/components/Channels/ChannelDetail/WhitelistManager"
import { TitleCards, type TitleGroup } from "@/components/Channels/TitleCards"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

type TitleCardsProps = Omit<ComponentProps<typeof TitleCards>, "onSelect"> & {
  /** The channel holding these titles, which is what their filters are read from. */
  channelId: string
}

// TODO: Validate
/**
 * Title cards that open the title, for somebody who does not own the channel.
 *
 * The whole of what the channel carries is read - the title, its sites, its
 * seasons and their episodes - since that is no more than watching the channel
 * already titles. Which of them the channel carries is the owner's to set, so
 * nothing that would set it is here.
 */
export function TitleCardsWithInformation({
  channelId,
  ...cardProps
}: TitleCardsProps) {
  const [selected, setSelected] = useState<TitleGroup | null>(null)

  return (
    <>
      <TitleCards {...cardProps} onSelect={setSelected} />
      <Dialog
        open={selected != null}
        onOpenChange={(open) => {
          if (!open) setSelected(null)
        }}
      >
        <DialogContent className="sm:max-w-[calc(100%-2rem)] max-h-[85vh] flex flex-col overflow-hidden">
          <DialogHeader>
            <DialogTitle>{selected?.name || "Unknown Title"}</DialogTitle>
          </DialogHeader>
          {selected && (
            <DialogBody>
              <WhitelistManager
                channelId={channelId}
                tmdbTitleId={selected.tmdbTitleId}
                titleName={selected.name || "Unknown Title"}
                onClose={() => setSelected(null)}
                readOnly
              />
            </DialogBody>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
