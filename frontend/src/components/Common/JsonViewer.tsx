// TODO: Validate
import { ChevronRight } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Nodes shallower than this auto-expand on first render; deeper ones start
// collapsed so large payloads stay scannable.
const AUTO_EXPAND_DEPTH = 2

type InitialState = "default" | "expanded" | "collapsed"

function isContainer(
  value: unknown,
): value is Record<string, unknown> | unknown[] {
  return typeof value === "object" && value !== null
}

function PrimitiveValue({ value }: { value: unknown }) {
  if (typeof value === "string") {
    return (
      <span className="text-emerald-600 dark:text-emerald-400">"{value}"</span>
    )
  }
  if (typeof value === "number") {
    return <span className="text-blue-600 dark:text-blue-400">{value}</span>
  }
  if (typeof value === "boolean") {
    return (
      <span className="text-purple-600 dark:text-purple-400">
        {String(value)}
      </span>
    )
  }
  return <span className="text-muted-foreground">null</span>
}

function KeyLabel({ name, isIndex }: { name: string; isIndex: boolean }) {
  return (
    <span
      className={
        isIndex ? "text-muted-foreground" : "text-sky-700 dark:text-sky-300"
      }
    >
      {isIndex ? name : `"${name}"`}
      <span className="text-muted-foreground">: </span>
    </span>
  )
}

function JsonNode({
  name,
  isIndex,
  value,
  depth,
  initialState,
}: {
  name?: string
  isIndex?: boolean
  value: unknown
  depth: number
  initialState: InitialState
}) {
  const startsOpen =
    initialState === "expanded"
      ? true
      : initialState === "collapsed"
        ? false
        : depth < AUTO_EXPAND_DEPTH
  const [open, setOpen] = useState(startsOpen)

  const label =
    name !== undefined ? <KeyLabel name={name} isIndex={!!isIndex} /> : null

  if (!isContainer(value)) {
    return (
      <div className="whitespace-pre-wrap break-all">
        {label}
        <PrimitiveValue value={value} />
      </div>
    )
  }

  const isArray = Array.isArray(value)
  const entries: [string, unknown][] = isArray
    ? value.map((item, index) => [String(index), item])
    : Object.entries(value)
  const openBracket = isArray ? "[" : "{"
  const closeBracket = isArray ? "]" : "}"

  if (entries.length === 0) {
    return (
      <div>
        {label}
        <span className="text-muted-foreground">
          {openBracket}
          {closeBracket}
        </span>
      </div>
    )
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        className="flex w-full items-start gap-1 rounded text-left hover:bg-muted/60"
      >
        <ChevronRight
          className={cn(
            "mt-[3px] size-3 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
        <span>
          {label}
          <span className="text-muted-foreground">{openBracket}</span>
          {!open && (
            <span className="text-muted-foreground">
              <span className="opacity-70">
                {" "}
                {entries.length} {isArray ? "items" : "keys"}{" "}
              </span>
              {closeBracket}
            </span>
          )}
        </span>
      </button>
      {open && (
        <>
          <div className="ml-[6px] border-l border-border/60 pl-3">
            {entries.map(([childName, childValue]) => (
              <JsonNode
                key={childName}
                name={childName}
                isIndex={isArray}
                value={childValue}
                depth={depth + 1}
                initialState={initialState}
              />
            ))}
          </div>
          <div className="text-muted-foreground">{closeBracket}</div>
        </>
      )}
    </div>
  )
}

export function JsonViewer({ value }: { value: unknown }) {
  const [initialState, setInitialState] = useState<InitialState>("default")
  // Bumping the key remounts the tree so every node re-reads `initialState`.
  const [generation, setGeneration] = useState(0)

  const applyState = (next: InitialState) => {
    setInitialState(next)
    setGeneration((previous) => previous + 1)
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => applyState("expanded")}
        >
          Expand all
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => applyState("collapsed")}
        >
          Collapse all
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto rounded-md bg-muted p-4 font-mono text-xs leading-relaxed">
        <JsonNode
          key={generation}
          value={value}
          depth={0}
          initialState={initialState}
        />
      </div>
    </div>
  )
}
