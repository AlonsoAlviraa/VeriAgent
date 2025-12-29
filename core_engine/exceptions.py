class CoreError(Exception):
    """Base class for core engine exceptions."""
    pass

class HashContinuityError(CoreError):
    """Raised when the hash chain is broken."""
    def __init__(self, message: str, expected_hash: str = "", received_hash: str = ""):
        super().__init__(message)
        self.expected_hash = expected_hash
        self.received_hash = received_hash
