// TODO: Validate
import { Link } from "@tanstack/react-router"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"

// TODO: Validate
const AddChannel = () => {
  return (
    <Button asChild>
      <Link to="/onboarding">
        <Plus className="mr-2" />
        New Channel
      </Link>
    </Button>
  )
}

export default AddChannel
