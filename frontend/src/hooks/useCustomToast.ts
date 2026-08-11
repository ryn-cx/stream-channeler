// TODO: Validate
import { toast } from "sonner"

// TODO: Validate
const useCustomToast = () => {
  // TODO: Validate
  const showSuccessToast = (description: string) => {
    toast.success("Success!", {
      description,
    })
  }

  // TODO: Validate
  const showErrorToast = (description: string) => {
    toast.error("Something went wrong!", {
      description,
    })
  }

  // TODO: Validate
  const showWarningToast = (description: string) => {
    toast.warning("Warning", {
      description,
    })
  }

  return { showSuccessToast, showErrorToast, showWarningToast }
}

export default useCustomToast
