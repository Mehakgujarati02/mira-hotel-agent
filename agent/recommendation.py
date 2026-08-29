def calculate_hotel_score(hotel, guests, budget, preferences):
    """
    Calculate a deterministic recommendation score
    and explain why the hotel received that score.
    """

    score = 0
    reasons = []

    rooms = hotel.get("rooms", [])

    if not rooms:
        return 0, []

    # Find the cheapest suitable room
    suitable_rooms = [
        room for room in rooms
        if not guests or room["capacity"] >= guests
    ]
    if not suitable_rooms:
        return 0

    best_room = min(
         suitable_rooms,
         key=lambda room: room["price_per_night"]
    )

    price = best_room["price_per_night"]
    capacity = best_room["capacity"]

    # --------------------------------
    # 1. Budget match
    # --------------------------------

    if budget:

        if price <= budget:

            score += 40

            remaining = budget - price

            if price <= budget * 0.8:
                score += 10
                reasons.append(
                    f"₹{remaining} under your budget"
                )
            else:
                reasons.append(
                    "fits within your budget"
                )

        else:
            score -= 30

    # --------------------------------
    # 2. Guest capacity
    # --------------------------------

    if guests and capacity >= guests:

        extra_capacity = capacity - guests

        if extra_capacity == 0:
            score += 30
            reasons.append(
                "fits your group perfectly"
            )

        elif extra_capacity <= 2:
            score += 20
            reasons.append(
                "comfortably fits your group"
            )

        else:
            score += 10
            reasons.append(
                "has plenty of capacity for your group"
            )

    # --------------------------------
    # 3. Preference matching
    # --------------------------------

    hotel_text = " ".join(
        hotel.get("amenities", [])
    ).lower()

    room_text = " ".join(
        best_room.get("amenities", [])
    ).lower()

    for preference in preferences:

        preference_lower = preference.lower()

        if (
                preference_lower in hotel_text
                or preference_lower in room_text
        ):
            score += 20

            reasons.append(
                f"matches your {preference} preference"
            )

    return score, reasons


def rank_hotels(
        hotels,
        guests=None,
        budget=None,
        preferences=None
):
    """
    Rank hotels from best to worst match.
    """

    if preferences is None:
        preferences = []

    scored_hotels = []

    for hotel in hotels:

        score, reasons = calculate_hotel_score(
            hotel,
            guests,
            budget,
            preferences
        )

        hotel_copy = hotel.copy()

        hotel_copy["recommendation_score"] = score

        hotel_copy["recommendation_reasons"] = reasons

        scored_hotels.append(hotel_copy)

    # Highest score first
    scored_hotels.sort(
        key=lambda hotel:
        hotel["recommendation_score"],
        reverse=True
    )

    return scored_hotels