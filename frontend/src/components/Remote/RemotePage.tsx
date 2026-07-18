// TODO: Validate
import { Download, Github, ListPlus, Play } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

const INSTALL_URL =
  "https://ryn-cx.github.io/stream-channeler-tuner/index.prod.user.js"
const SOURCE_URL = "https://github.com/ryn-cx/stream-channeler-remote"
const TAMPERMONKEY_URL = "https://www.tampermonkey.net/"

export function RemotePage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10 px-4 py-8">
      {/* Hero */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-bold tracking-tight">
          Stream Channeler Remote
        </h1>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
          A companion userscript that lets Stream Channeler play episodes back to
          back across streaming sites and queue shows for bulk import while you
          browse.
        </p>
        <div className="flex flex-wrap gap-3 justify-center pt-2">
          <Button asChild size="lg">
            <a href={INSTALL_URL} target="_blank" rel="noopener noreferrer">
              <Download className="mr-2" />
              Install
            </a>
          </Button>
          <Button asChild size="lg" variant="outline">
            <a href={SOURCE_URL} target="_blank" rel="noopener noreferrer">
              <Github className="mr-2" />
              Source Code
            </a>
          </Button>
        </div>
      </div>

      {/* What it does */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center shrink-0">
              <Play className="text-primary" />
            </div>
            <h2 className="text-xl font-semibold">Playback</h2>
          </div>
          <p className="text-muted-foreground">
            Turn a channel into a TV-like experience. The remote plays each
            episode and automatically advances to the next one when it ends.
          </p>
          <p className="text-sm text-muted-foreground">
            Autoplay works on YouTube, NHK World, Crunchyroll, HBO Max, and
            Netflix. Fullscreen is supported on YouTube and NHK World.
          </p>
        </Card>

        <Card className="p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-primary/10 w-12 h-12 flex items-center justify-center shrink-0">
              <ListPlus className="text-primary" />
            </div>
            <h2 className="text-xl font-semibold">Manage</h2>
          </div>
          <p className="text-muted-foreground">
            Build channels faster. Queue shows straight from content discovery
            sites with an "Add to Channel" button, then bulk import them into
            Stream Channeler.
          </p>
          <p className="text-sm text-muted-foreground">
            Queuing works on YouTube, NHK World, Crunchyroll, and JustWatch.
          </p>
        </Card>
      </div>

      {/* Installation */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold tracking-tight">Installation</h2>
        <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
          <li>
            Install a userscript manager such as{" "}
            <a
              href={TAMPERMONKEY_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Tampermonkey
            </a>
            .
          </li>
          <li>
            Click{" "}
            <a
              href={INSTALL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Install Stream Channeler Remote
            </a>{" "}
            and confirm the installation in your userscript manager.
          </li>
        </ol>
      </div>

      {/* Usage */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold tracking-tight">How to Use</h2>
        <div className="space-y-3 text-sm">
          <p>
            <strong>Playback:</strong> open a channel on streamchanneler.com,
            select <strong>Start Remote</strong>, and episodes will play
            sequentially.
          </p>
          <p>
            <strong>Manage:</strong> open the Bulk Import modal on the channels
            page, load your channel list, browse shows on a supported site and
            queue them with the <strong>Add to Channel</strong> button, then
            return to import the collected URLs.
          </p>
        </div>
      </div>
    </div>
  )
}
