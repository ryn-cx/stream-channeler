// TODO: Validate
declare module "winbox/src/js/winbox.js" {
  interface WinBoxOptions {
    title?: string
    mount?: HTMLElement
    root?: HTMLElement
    width?: string | number
    height?: string | number
    x?: string | number
    y?: string | number
    background?: string
    index?: number
    border?: string | number
    class?: string | string[]
    onclose?: (force: boolean) => boolean
  }

  // TODO: Validate
  export default class WinBox {
    constructor(options: WinBoxOptions)
    dom: HTMLElement | null
    body: HTMLElement | null
    close(force?: boolean): void
    setTitle(title: string): this
    focus(): this
    resize(width?: string | number, height?: string | number): this
    move(x?: string | number, y?: string | number): this
  }
}
