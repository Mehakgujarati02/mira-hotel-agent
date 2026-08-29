from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GuestState:

    # =========================================
    # Guest requirements
    # =========================================

    destination: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None

    guests: Optional[int] = None
    rooms: int = 1
    budget: Optional[float] = None

    preferences: list[str] = field(default_factory=list)

    # =========================================
    # Selection
    # =========================================

    selected_hotel: Optional[str] = None
    selected_room: Optional[str] = None

    # =========================================
    # Booking
    # =========================================

    booking_status: str = "not_started"

    # =========================================
    # Update state
    # =========================================

    def update(self, **kwargs):
        """
        Update only fields for which the guest
        provided a new value.

        None values are ignored so that previous
        conversation information is not lost.
        """

        for key, value in kwargs.items():

            if not hasattr(self, key):
                continue

            if value is None:
                continue

            setattr(self, key, value)

    # =========================================
    # Reset hotel/room selection
    # =========================================

    def reset_selection(self):
        """
        Clear the currently selected hotel and room.
        """

        self.selected_hotel = None
        self.selected_room = None
        self.booking_status = "not_started"

    # =========================================
    # Reset entire conversation
    # =========================================

    def reset(self):
        """
        Reset the complete guest conversation.
        """

        self.destination = None
        self.check_in = None
        self.check_out = None
        self.guests = None
        self.rooms = 1
        self.budget = None

        self.preferences.clear()

        self.selected_hotel = None
        self.selected_room = None

        self.booking_status = "not_started"

    # =========================================
    # State summary
    # =========================================

    def summary(self) -> dict:
        """
        Return the current guest state.
        """

        return {
            "destination": self.destination,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "guests": self.guests,
            "rooms": self.rooms,
            "budget": self.budget,
            "preferences": self.preferences.copy(),
            "selected_hotel": self.selected_hotel,
            "selected_room": self.selected_room,
            "booking_status": self.booking_status
        }