// TODO: Validate
import EmojiPickerReact, {
  type EmojiClickData,
  EmojiStyle,
  Theme,
} from "emoji-picker-react"
import { Smile, X } from "lucide-react"
import { useState } from "react"

import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface EmojiPickerProps {
  value: string | null
  onChange: (emoji: string | null) => void
  id?: string
}

// TODO: Validate
export function EmojiPicker({ value, onChange, id }: EmojiPickerProps) {
  const [open, setOpen] = useState(false)
  const { resolvedTheme } = useTheme()

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          className="h-10 w-10 p-0 text-xl leading-none"
          aria-label="Pick an icon"
        >
          {value ? (
            <span className="leading-none">{value}</span>
          ) : (
            <Smile className="size-4 text-muted-foreground" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        {value && (
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm text-muted-foreground">
              Current <span className="text-base">{value}</span>
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => {
                onChange(null)
                setOpen(false)
              }}
            >
              <X className="mr-1 size-3" />
              Clear
            </Button>
          </div>
        )}
        <EmojiPickerReact
          onEmojiClick={(emoji: EmojiClickData) => {
            onChange(emoji.emoji)
            setOpen(false)
          }}
          theme={resolvedTheme === "dark" ? Theme.DARK : Theme.LIGHT}
          emojiStyle={EmojiStyle.NATIVE}
          lazyLoadEmojis
          width={320}
          height={400}
          previewConfig={{ showPreview: false }}
        />
      </PopoverContent>
    </Popover>
  )
}
