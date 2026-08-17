// TODO: Validate
import { type ComponentProps, useState } from "react"

import { WhitelistManager } from "@/components/Channels/ChannelDetail/WhitelistManager"
import { ShowCards, type ShowGroup } from "@/components/Channels/ShowCards"
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

type ShowCardsProps = Omit<ComponentProps<typeof ShowCards>, "onSelect"> & {
  /** The channel holding these shows, which is what their filters are read from. */
  channelId: string
}

// TODO: Validate
/**
 * Show cards that open the title, for somebody who does not own the channel.
 *
 * The whole of what the channel carries is read - the title, its sites, its
 * seasons and their episodes - since that is no more than watching the channel
 * already shows. Which of them the channel carries is the owner's to set, so
 * nothing that would set it is here.
 */
export function ShowCardsWithInformation({
  channelId,
  ...cardProps
}: ShowCardsProps) {
  const [selected, setSelected] = useState<ShowGroup | null>(null)

  return (
    <>
      <ShowCards {...cardProps} onSelect={setSelected} />
      <Dialog
        open={selected != null}
        onOpenChange={(open) => {
          if (!open) setSelected(null)
        }}
      >
        <DialogContent className="sm:max-w-[calc(100%-2rem)] max-h-[85vh] flex flex-col overflow-hidden">
          <DialogHeader>
            <DialogTitle>{selected?.name || "Unknown Show"}</DialogTitle>
          </DialogHeader>
          {selected && (
            <DialogBody>
              <WhitelistManager
                channelId={channelId}
                canonicalShowId={selected.canonicalShowId}
                showName={selected.name || "Unknown Show"}
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
