"""
Custom exception classes for the booking system.
"""


class AppException(Exception):
    """Base application exception."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class SlotNotAvailableError(AppException):
    def __init__(self, detail: str = "Slot is not available"):
        super().__init__(status_code=409, detail=detail)


class SlotAlreadyLockedError(AppException):
    def __init__(self, detail: str = "Slot is currently locked by another user"):
        super().__init__(status_code=423, detail=detail)


class LockExpiredError(AppException):
    def __init__(self, detail: str = "Slot lock has expired"):
        super().__init__(status_code=410, detail=detail)


class BookingNotFoundError(AppException):
    def __init__(self, detail: str = "Booking not found"):
        super().__init__(status_code=404, detail=detail)


class ProviderNotFoundError(AppException):
    def __init__(self, detail: str = "Provider not found"):
        super().__init__(status_code=404, detail=detail)


class InvalidInputError(AppException):
    def __init__(self, detail: str = "Invalid input"):
        super().__init__(status_code=422, detail=detail)


class DoubleBookingError(AppException):
    def __init__(self, detail: str = "This slot is already booked"):
        super().__init__(status_code=409, detail=detail)


class ConcurrencyError(AppException):
    def __init__(self, detail: str = "Concurrent modification detected, please retry"):
        super().__init__(status_code=409, detail=detail)


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "This slot is reserved by a different user"):
        super().__init__(status_code=403, detail=detail)
