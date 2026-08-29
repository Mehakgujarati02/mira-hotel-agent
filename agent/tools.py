import json
from pathlib import Path


# Load hotel inventory
DATA_PATH = Path(__file__).parent.parent / "data" / "hotels.json"


def load_hotels():
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data["hotels"]


def search_hotels(
        destination=None,
        guests=None,
        budget=None,
        preference=None
):
    """
    Search and rank hotels based on guest requirements.

    Hard filters:
    - Destination
    - Guest capacity
    - Budget
    - Preference

    Ranking:
    - Preference match
    - Guest capacity
    - Price/value
    """

    hotels = load_hotels()
    results = []

    for hotel in hotels:

        # -----------------------------
        # 1. Destination filter
        # -----------------------------
        if destination:
            if hotel["location"].lower() != destination.lower():
                continue

        matching_rooms = []

        for room in hotel["rooms"]:

            # -----------------------------
            # 2. Guest capacity filter
            # -----------------------------
            if guests and room["capacity"] < guests:
                continue

            # -----------------------------
            # 3. Budget filter
            # -----------------------------
            if budget and room["price_per_night"] > budget:
                continue

            # -----------------------------
            # 4. Preference filter
            # -----------------------------
            if preference:

                room_text = " ".join(room["amenities"]).lower()
                hotel_text = " ".join(hotel["amenities"]).lower()

                if preference.lower() not in room_text and \
                        preference.lower() not in hotel_text:
                    continue

            matching_rooms.append(room)

        # Skip hotel if no suitable rooms
        if not matching_rooms:
            continue

        # --------------------------------
        # 5. Find the best room
        # --------------------------------
        best_room = min(
            matching_rooms,
            key=lambda room: room["price_per_night"]
        )

        score = 0
        reasons = []

        # --------------------------------
        # 6. Preference score
        # --------------------------------
        if preference:

            preference_lower = preference.lower()

            hotel_amenities = " ".join(
                hotel["amenities"]
            ).lower()

            room_amenities = " ".join(
                best_room["amenities"]
            ).lower()

            if preference_lower in hotel_amenities or \
                    preference_lower in room_amenities:

                score += 40
                reasons.append(
                    f"matches your {preference} preference"
                )

        # --------------------------------
        # 7. Guest capacity score
        # --------------------------------
        if guests:

            extra_capacity = (
                    best_room["capacity"] - guests
            )

            if extra_capacity == 0:
                score += 30
                reasons.append(
                    "fits your group perfectly"
                )

            elif extra_capacity <= 2:
                score += 25
                reasons.append(
                    "comfortably fits your group"
                )

            else:
                score += 20
                reasons.append(
                    "has plenty of room for your group"
                )

        # --------------------------------
        # 8. Budget/value score
        # --------------------------------
        if budget:

            price = best_room["price_per_night"]

            remaining_budget = budget - price

            if remaining_budget >= budget * 0.20:
                score += 30
                reasons.append(
                    f"is ₹{remaining_budget:.0f} under your budget"
                )

            elif remaining_budget >= 0:
                score += 20
                reasons.append(
                    "fits within your budget"
                )

        # --------------------------------
        # 9. Store result
        # --------------------------------
        results.append({
            "hotel_id": hotel["id"],
            "hotel_name": hotel["name"],
            "location": hotel["location"],
            "description": hotel["description"],
            "rooms": matching_rooms,
            "recommendation_score": score,
            "recommendation_reasons": reasons
        })

    # --------------------------------
    # 10. Rank best hotel first
    # --------------------------------
    results.sort(
        key=lambda hotel: hotel["recommendation_score"],
        reverse=True
    )

    return results

    hotels = load_hotels()
    results = []

    for hotel in hotels:

        # Destination filter
        if destination:
            if hotel["location"].lower() != destination.lower():
                continue

        matching_rooms = []

        for room in hotel["rooms"]:

            # Guest capacity filter
            if guests and room["capacity"] < guests:
                continue

            # Budget filter
            if budget and room["price_per_night"] > budget:
                continue

            # Preference filter
            if preference:
                room_text = " ".join(room["amenities"]).lower()
                hotel_text = " ".join(hotel["amenities"]).lower()

                if preference.lower() not in room_text and \
                        preference.lower() not in hotel_text:
                    continue

            matching_rooms.append(room)

        if matching_rooms:
            results.append({
                "hotel_id": hotel["id"],
                "hotel_name": hotel["name"],
                "location": hotel["location"],
                "description": hotel["description"],
                "rooms": matching_rooms
            })

    return results

def hotel_search_tool(
        destination: str,
        guests: int,
        budget: int
):
    """
    Search available hotels based on guest requirements.
    """

    return search_hotels(
        destination=destination,
        guests=guests,
        budget=budget,
        preference=None
    )