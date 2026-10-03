// TODO: Validate
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2, X } from "lucide-react"
import { useState } from "react"
import { ChannelsService } from "@/client"
import type { StoreTitle } from "./caseTexture"

// TODO: Validate
const addTitles = async (channelId: string, titles: StoreTitle[]) => {
  for (const title of titles) {
    await ChannelsService.addChannelTitle({ channelId, titleId: title.id })
  }
}

// TODO: Validate
export function CounterChannels({
  action,
  titles,
  onClose,
}: {
  action: "create" | "add"
  titles: StoreTitle[]
  onClose: () => void
}) {
  const [name, setName] = useState("")
  const queryClient = useQueryClient()

  const { data: channels, isLoading } = useQuery({
    queryKey: ["video-store-counter-channels"],
    queryFn: () => ChannelsService.getChannels({ scope: "owned", limit: 100 }),
    enabled: action === "add",
    refetchOnWindowFocus: false,
  })

  const create = useMutation({
    mutationFn: async () => {
      const channel = await ChannelsService.createChannel({
        requestBody: {
          name: name.trim(),
          visibility: "private",
          anonymous: false,
        },
      })
      await addTitles(channel.id, titles)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      onClose()
    },
  })

  const add = useMutation({
    mutationFn: (channelId: string) => addTitles(channelId, titles),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      onClose()
    },
  })

  const pending = create.isPending || add.isPending

  return (
    <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-[min(24rem,90vw)] rounded-xl border border-white/15 bg-black/90 p-4 text-white">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">
            {action === "create" ? "Create channel" : "Add to channel"}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-white/60 hover:text-white"
          >
            <X className="size-4" />
          </button>
        </div>

        <p className="mt-1 text-xs text-white/50">
          {titles.length === 1
            ? "1 title at the counter"
            : `${titles.length.toLocaleString()} titles at the counter`}
        </p>

        {action === "create" && (
          <div className="mt-4 flex flex-col gap-3">
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Channel name"
              className="w-full rounded-md border border-white/15 bg-black/50 px-3 py-2 text-sm outline-none focus:border-white/40"
            />
            <button
              type="button"
              disabled={name.trim() === "" || titles.length === 0 || pending}
              onClick={() => create.mutate()}
              className="flex items-center justify-center gap-2 rounded-full border border-emerald-300/40 px-4 py-2 text-sm font-medium text-emerald-200 hover:bg-emerald-300/10 disabled:opacity-40"
            >
              {pending && <Loader2 className="size-4 animate-spin" />}
              Create channel
            </button>
          </div>
        )}

        {action === "add" && (
          <div className="mt-4 flex max-h-72 flex-col gap-2 overflow-y-auto pr-1">
            {isLoading && (
              <div className="flex items-center gap-2 text-sm text-white/60">
                <Loader2 className="size-4 animate-spin" />
                Loading channels…
              </div>
            )}
            {channels?.data.length === 0 && (
              <span className="text-sm text-white/60">
                You have no channels yet.
              </span>
            )}
            {channels?.data.map((channel) => (
              <button
                key={channel.id}
                type="button"
                disabled={titles.length === 0 || pending}
                onClick={() => add.mutate(channel.id)}
                className="rounded-md border border-white/15 px-3 py-2 text-left text-sm text-white/85 hover:bg-white/10 disabled:opacity-40"
              >
                {channel.custom_name || channel.name || "Untitled channel"}
              </button>
            ))}
          </div>
        )}

        {(create.isError || add.isError) && (
          <p className="mt-3 text-xs text-rose-300">
            That did not go through. Try again.
          </p>
        )}
      </div>
    </div>
  )
}
