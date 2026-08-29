import uuid
from datetime import datetime

from tools import load_hotels


def calculate_booking(
        hotel_id,
        room_id,
        nights,
        guests,
        add_ons=None
):
    """
    Calculate the booking price using hotel inventory data.

    Pricing is deterministic and does not depend on the LLM.
    """

    if nights <= 0:
        raise ValueError("Number of nights must be greater than 0.")

    if guests <= 0:
        raise ValueError("Number of guests must be greater than 0.")

    hotels = load_hotels()

    hotel = next(
        (h for h in hotels if h["id"] == hotel_id),
        None
    )

    if not hotel:
        raise ValueError("Hotel not found.")

    room = next(
        (r for r in hotel["rooms"] if r["id"] == room_id),
        None
    )

    if not room:
        raise ValueError("Room not found.")

    if guests > room["capacity"]:
        raise ValueError(
            f"This room can accommodate only {room['capacity']} guests."
        )

    if room["available_rooms"] <= 0:
        raise ValueError("This room is currently unavailable.")

    room_total = room["price_per_night"] * nights

    add_on_total = 0
    selected_add_ons = []

    add_ons = add_ons or []

    for requested_add_on in add_ons:

        add_on = next(
            (
                a for a in hotel["add_ons"]
                if a["id"] == requested_add_on
            ),
            None
        )

        if not add_on:
            raise ValueError(
                f"Add-on '{requested_add_on}' is not available."
            )

        if "price_per_guest" in add_on:
            price = add_on["price_per_guest"] * guests
        else:
            price = add_on["price"]

        add_on_total += price

        selected_add_ons.append({
            "name": add_on["name"],
            "price": price
        })

    total = room_total + add_on_total

    return {
        "hotel": hotel["name"],
        "room": room["name"],
        "guests": guests,
        "nights": nights,
        "room_total": room_total,
        "add_ons": selected_add_ons,
        "add_on_total": add_on_total,
        "total": total
    }


def create_booking(
        hotel_id,
        room_id,
        nights,
        guests,
        guest_name,
        add_ons=None
):
    """
    Create a simple demo booking.
    """

    price_details = calculate_booking(
        hotel_id=hotel_id,
        room_id=room_id,
        nights=nights,
        guests=guests,
        add_ons=add_ons
    )

    booking_id = "MIRA-" + str(uuid.uuid4())[:8].upper()

    return {
        "booking_id": booking_id,
        "guest_name": guest_name,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "confirmed",
        **price_details
    }