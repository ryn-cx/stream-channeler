// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"

const AddChannel = () => {
  return (
    <Button asChild className="mt-2 mb-4">
      <Link to="/onboarding">
        <Plus className="mr-2" />
        New Channel
      </Link>
    </Button>
  )
}

export default AddChannel
