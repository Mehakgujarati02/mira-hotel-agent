from datetime import date

from state import GuestState
from llm import extract_guest_intent, generate_hotel_response
from tools import search_hotels
from booking import calculate_booking


class MiraAgent:

    def __init__(self):
        self.state = GuestState()
        self.last_results = []
        self.asked_preference = False

    def process_message(self, message):

        # =====================================================
        # 0. DETECT MID-FLOW CHANGES (Task 5 #7, #8)
        # A guest saying "Actually, Mumbai" or "Actually make it
        # 20000" while already mid-selection should restart the
        # search with the new value, not be treated as an
        # invalid hotel/room pick.
        # =====================================================

        if self.state.booking_status in (
                "hotel_selection", "room_selection", "booking_pending", "no_results"
        ):
            change_intent = extract_guest_intent(message)

            new_destination = change_intent.get("destination")
            new_budget = change_intent.get("budget")
            new_preferences = [
                p for p in change_intent.get("preferences", [])
                if p not in self.state.preferences
            ]

            destination_changed = (
                    new_destination and new_destination != self.state.destination
            )
            budget_changed = (
                    new_budget is not None and new_budget != self.state.budget
            )
            preference_added = bool(new_preferences)

            if destination_changed or budget_changed or preference_added:

                if new_budget is not None and new_budget <= 0:
                    return {
                        "type": "clarification",
                        "message": "Budget must be a positive amount. Could you tell me your budget per night?",
                        "state": self.state.summary()
                    }

                self.state.selected_hotel = None
                self.state.selected_room = None
                self.state.booking_status = "not_started"

                self.state.update(
                    destination=new_destination,
                    budget=new_budget,
                )

                for preference in new_preferences:
                    self.state.preferences.append(preference)

                return self.run_search()

        # =====================================================
        # 1. HANDLE HOTEL/ROOM SELECTION
        # =====================================================

        if self.state.booking_status == "hotel_selection":
            selected_hotel = self.find_hotel_from_message(message)

            if selected_hotel:
                self.state.selected_hotel = selected_hotel["hotel_id"]
                self.state.booking_status = "room_selection"

                return {
                    "type": "room_selection",
                    "message": self.show_rooms(selected_hotel),
                    "results": [selected_hotel],
                    "state": self.state.summary()
                }

            # No match: don't fall through to a fresh search.
            # If several hotels exist, "yes" is ambiguous (Task 5 #12).
            if len(self.last_results) > 1 and self.is_confirmation(message):
                clarification = "Which hotel would you like? Please reply with a name or number."
            else:
                clarification = (
                    "I couldn't find that hotel among the options. "
                    "Please choose one of the hotels listed above."
                )

            return {
                "type": "hotel_selection",
                "message": clarification,
                "results": self.last_results,
                "state": self.state.summary()
            }

        elif self.state.booking_status == "room_selection":
            selected_room = self.find_room_from_message(message)

            if selected_room:
                self.state.selected_room = selected_room["name"]
                self.state.booking_status = "booking_pending"

                hotel = self.get_selected_hotel()

                return {
                    "type": "booking_pending",
                    "message": (
                        f"Great choice! You've selected the "
                        f"{selected_room['name']} at "
                        f"{hotel['hotel_name']}.\n\n"
                        f"💰 ₹{selected_room['price_per_night']}/night "
                        f"for up to {selected_room['capacity']} guests.\n\n"
                        f"Would you like to proceed with the booking?"
                    ),
                    "results": [hotel],
                    "state": self.state.summary()
                }

            hotel = self.get_selected_hotel()

            return {
                "type": "room_selection",
                "message": (
                    "I couldn't match that to one of the available rooms. "
                    "Please choose a room from the list above."
                ),
                "results": [hotel] if hotel else [],
                "state": self.state.summary()
            }

        elif self.state.booking_status == "booking_pending":

            if self.is_confirmation(message):

                self.state.booking_status = "collecting_dates"

                return {
                    "type": "collecting_dates",
                    "message": (
                        "Perfect! Your room selection is confirmed. "
                        "What are your check-in and check-out dates?"
                    ),
                    "state": self.state.summary()
                }

            return {
                "type": "booking_pending",
                "message": "Would you like to proceed with this booking? (yes/no)",
                "state": self.state.summary()
            }

        elif self.state.booking_status == "collecting_dates":
            return self.handle_date_collection(message)

        elif self.state.booking_status == "confirmed":

            return {
                "type": "confirmed",
                "message": (
                    "Your booking is already confirmed! 🎉 "
                    "Let me know if you'd like to start a new search."
                ),
                "state": self.state.summary()
            }

        elif self.state.booking_status == "no_results":

            return {
                "type": "no_results",
                "message": (
                    f"I still don't have a match for {self.state.destination}, "
                    f"{self.state.guests} guests, within "
                    f"₹{self.state.budget:,.0f} per night.\n\n"
                    f"Try a new budget or destination — for example "
                    f"'Actually make it 20000' or 'Try Mumbai instead.'"
                ),
                "state": self.state.summary()
            }

        # =====================================================
        # 2. UNDERSTAND GUEST MESSAGE
        # =====================================================

        intent = extract_guest_intent(message)

        print("\nExtracted intent:")
        print(intent)

        # =====================================================
        # 2b. VALIDATE (Task 5 #5, #6)
        # =====================================================

        guests = intent.get("guests")
        budget = intent.get("budget")

        if guests is not None and guests <= 0:
            return {
                "type": "clarification",
                "message": "The number of guests must be at least 1. How many guests will be staying?",
                "state": self.state.summary()
            }

        if budget is not None and budget <= 0:
            return {
                "type": "clarification",
                "message": "Budget must be a positive amount. Could you tell me your budget per night?",
                "state": self.state.summary()
            }

        # =====================================================
        # 3. UPDATE STATE
        # =====================================================

        self.state.update(
            destination=intent.get("destination"),
            check_in=intent.get("check_in"),
            check_out=intent.get("check_out"),
            guests=guests,
            rooms=intent.get("rooms"),
            budget=budget,
        )

        for preference in intent.get("preferences", []):
            if preference not in self.state.preferences:
                self.state.preferences.append(preference)

        # =====================================================
        # 4. CHECK MISSING INFORMATION
        # =====================================================

        missing = self.get_missing_information()

        if missing:
            return {
                "type": "clarification",
                "message": self.get_clarification_message(missing),
                "state": self.state.summary()
            }

        # =====================================================
        # 5-7. SEARCH HOTELS / SHOW RESULTS
        # =====================================================

        return self.run_search()

    # =========================================================
    # RUN SEARCH (shared by the normal flow and mid-flow changes)
    # =========================================================

    def run_search(self):

        preference = self.state.preferences[0] if self.state.preferences else None

        results = search_hotels(
            destination=self.state.destination,
            guests=self.state.guests,
            budget=self.state.budget,
            preference=preference
        )

        self.last_results = results

        if not results:
            self.state.booking_status = "no_results"

            return {
                "type": "no_results",
                "message": (
                    f"I couldn't find any hotels in "
                    f"{self.state.destination} for "
                    f"{self.state.guests} guests within "
                    f"₹{self.state.budget:,.0f} per night.\n\n"
                    f"Would you like to increase your budget?"
                ),
                "results": [],
                "state": self.state.summary()
            }

        self.state.booking_status = "hotel_selection"

        message = self.show_hotel_options(results)

        # Mention preferences once, without delaying the search itself.
        if not self.asked_preference and not self.state.preferences:
            self.asked_preference = True
            message += (
                "\n\n(By the way, if you have a preference like a pool "
                "or beach access, just mention it and I'll narrow this down.)"
            )

        return {
            "type": "hotel_selection",
            "message": message,
            "results": results,
            "state": self.state.summary()
        }

    # =========================================================
    # FIND HOTEL
    # =========================================================

    def find_hotel_from_message(self, message):

        message_lower = message.lower()

        # First try hotel name
        for hotel in self.last_results:

            hotel_name = hotel["hotel_name"].lower()

            if hotel_name in message_lower:
                return hotel

        # Allow selection by number
        numbers = {
            "1": 0,
            "2": 1,
            "3": 2,
            "4": 3,
            "5": 4
        }

        for number, index in numbers.items():

            if number in message_lower:

                if index < len(self.last_results):
                    return self.last_results[index]

        # If only one hotel exists and guest says yes
        if len(self.last_results) == 1:

            confirmation_words = [
                "yes",
                "yeah",
                "yep",
                "sure",
                "okay",
                "ok",
                "select it",
                "choose it",
                "book it"
            ]

            if any(word in message_lower for word in confirmation_words):
                return self.last_results[0]

        return None

    # =========================================================
    # SHOW HOTEL OPTIONS
    # =========================================================

    def show_hotel_options(self, hotels):

        response = "🏨 I found these hotels for you:\n\n"

        for i, hotel in enumerate(hotels, start=1):

            cheapest_room = min(
                hotel["rooms"],
                key=lambda room: room["price_per_night"]
            )

            response += (
                f"{i}. {hotel['hotel_name']}\n"
                f"   📍 {hotel['location']}\n"
                f"   From ₹{cheapest_room['price_per_night']:,}/night\n\n"
            )

        response += "Which hotel would you like to select?"

        return response

    # =========================================================
    # SHOW ROOMS
    # =========================================================

    def show_rooms(self, hotel):

        response = (
            f"🏨 {hotel['hotel_name']}\n"
            f"📍 {hotel['location']}\n\n"
            f"Available rooms:\n"
        )

        for i, room in enumerate(hotel["rooms"], start=1):

            response += (
                f"{i}. 🛏️ {room['name']} — "
                f"₹{room['price_per_night']:,}/night "
                f"(up to {room['capacity']} guests)\n"
            )

        response += "\nWhich room would you like?"

        return response

    # =========================================================
    # FIND ROOM
    # =========================================================

    def find_room_from_message(self, message):

        message_lower = message.lower()

        hotel = self.get_selected_hotel()

        if not hotel:
            return None

        rooms = hotel["rooms"]

        # Match room name
        for room in rooms:

            if room["name"].lower() in message_lower:
                return room

        # Match room number
        for i, room in enumerate(rooms, start=1):

            if str(i) in message_lower:
                return room

        return None

    # =========================================================
    # HANDLE DATE COLLECTION (Task 4)
    # =========================================================

    def handle_date_collection(self, message):

        intent = extract_guest_intent(message)

        check_in = intent.get("check_in") or self.state.check_in
        check_out = intent.get("check_out") or self.state.check_out

        if not check_in or not check_out:
            missing = []
            if not check_in:
                missing.append("check-in")
            if not check_out:
                missing.append("check-out")

            return {
                "type": "collecting_dates",
                "message": (
                    f"I still need your {' and '.join(missing)} date"
                    f"{'s' if len(missing) > 1 else ''}. "
                    f"For example: 'Check in September 10 and check out September 13.'"
                ),
                "state": self.state.summary()
            }

        check_in_date = date.fromisoformat(check_in)
        check_out_date = date.fromisoformat(check_out)

        if check_out_date <= check_in_date:
            return {
                "type": "collecting_dates",
                "message": (
                    "Your check-out date needs to be after your check-in date. "
                    "Could you confirm both dates again?"
                ),
                "state": self.state.summary()
            }

        self.state.check_in = check_in
        self.state.check_out = check_out

        hotel = self.get_selected_hotel()
        room = self.get_selected_room()
        nights = (check_out_date - check_in_date).days

        try:
            price_details = calculate_booking(
                hotel_id=self.state.selected_hotel,
                room_id=room["id"],
                nights=nights,
                guests=self.state.guests
            )
        except ValueError as error:
            # Deterministic pricing engine caught a real problem
            # (e.g. capacity/availability) - don't confirm the booking.
            return {
                "type": "collecting_dates",
                "message": (
                    f"I couldn't finalize that booking: {error} "
                    f"Could you adjust your dates or room choice?"
                ),
                "state": self.state.summary()
            }

        self.state.booking_status = "confirmed"

        return {
            "type": "confirmed",
            "message": (
                f"🎉 Booking confirmed!\n\n"
                f"🏨 {hotel['hotel_name']}\n"
                f"🛏️ {self.state.selected_room}\n"
                f"📅 {check_in} → {check_out} ({nights} night{'s' if nights != 1 else ''})\n"
                f"👥 {self.state.guests} guests\n\n"
                f"💰 ₹{price_details['room_total']:,} "
                f"({price_details['nights']} nights × "
                f"₹{room['price_per_night']:,}/night)\n"
                f"💵 Total: ₹{price_details['total']:,}\n\n"
                f"We look forward to hosting you!"
            ),
            "state": self.state.summary()
        }

    # =========================================================
    # GET SELECTED HOTEL
    # =========================================================

    def get_selected_hotel(self):

        for hotel in self.last_results:

            if hotel["hotel_id"] == self.state.selected_hotel:
                return hotel

        return None

    # =========================================================
    # GET SELECTED ROOM (full room dict, incl. room id/price)
    # =========================================================

    def get_selected_room(self):

        hotel = self.get_selected_hotel()

        if not hotel:
            return None

        for room in hotel["rooms"]:
            if room["name"] == self.state.selected_room:
                return room

        return None

    # =========================================================
    # CONFIRMATION
    # =========================================================

    def is_confirmation(self, message):

        message_lower = message.lower()

        confirmation_words = [
            "yes",
            "yeah",
            "yep",
            "sure",
            "okay",
            "ok",
            "confirm",
            "proceed",
            "book it"
        ]

        return any(
            word in message_lower
            for word in confirmation_words
        )

    # =========================================================
    # MISSING INFORMATION
    # =========================================================

    def get_missing_information(self):

        missing = []

        if not self.state.destination:
            missing.append("destination")

        if not self.state.guests:
            missing.append("number of guests")

        if not self.state.budget:
            missing.append("budget")

        return missing

    # =========================================================
    # CLARIFICATION MESSAGE
    # =========================================================

    def get_clarification_message(self, missing):

        if len(missing) == 1:
            return f"Could you tell me your {missing[0]}?"

        return (
                "I'd be happy to help! "
                "Could you tell me your "
                + " and ".join(missing)
                + "?"
        )