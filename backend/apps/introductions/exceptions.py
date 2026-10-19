class InvalidTransition(Exception):
    """Raised when a status change violates the introduction lifecycle."""

    def __init__(self, current_status=None, next_status=None, message=None):
        self.current_status = current_status
        self.next_status = next_status
        detail = message or (
            f"Invalid transition from {current_status} to {next_status}."
            if current_status and next_status
            else "Invalid status transition."
        )
        super().__init__(detail)
