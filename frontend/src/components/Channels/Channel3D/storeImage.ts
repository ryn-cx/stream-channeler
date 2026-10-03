// TODO: Validate
import { OpenAPI } from "@/client"

// TODO: Validate
const pause = (milliseconds: number) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds))

// TODO: Validate
const attemptLoad = (url: string) =>
  new Promise<HTMLImageElement | null>((resolve) => {
    const image = new Image()
    image.crossOrigin = "anonymous"
    image.referrerPolicy = "no-referrer"
    image.onload = () => resolve(image)
    image.onerror = () => resolve(null)
    image.src = new URL(url, OpenAPI.BASE).href
  })

// TODO: Validate
export const loadStoreImage = async (url: string | null) => {
  if (!url) return null
  const loaded = await attemptLoad(url)
  if (loaded) return loaded
  await pause(300 + Math.random() * 500)
  return attemptLoad(url)
}
