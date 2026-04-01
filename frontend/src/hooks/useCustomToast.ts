import { toast } from "sonner"

const useCustomToast = () => {
  const showSuccessToast = (description: string) => {
    toast.success("Success!", {
      description,
    })
  }

  const showErrorToast = (description: string) => {
    toast.error("Something went wrong!", {
      description,
    })
  }

  const showWarningToast = (description: string) => {
    toast.warning("Warning", {
      description,
    })
  }

  return { showSuccessToast, showErrorToast, showWarningToast }
}

export default useCustomToast
