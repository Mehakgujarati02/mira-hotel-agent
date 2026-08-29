import os
import json
import re
from datetime import date

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=API_KEY)

USE_MOCK_LLM = True
# ==========================================================
# INTENT EXTRACTION
# ==========================================================

SYSTEM_PROMPT = """
You are Mira, an AI hotel assistant.

Your job is to extract hotel search requirements from the guest's
natural language message.

Return ONLY valid JSON.

The JSON must contain these fields:

{
    "destination": string or null,
    "check_in": string or null,
    "check_out": string or null,
    "guests": integer or null,
    "rooms": integer or null,
    "budget": number or null,
    "preference": string or null
}

Rules:
- Do not invent information.
- If the guest did not provide a value, return null.
- "20k" means 20000.
- Extract only information explicitly stated or clearly implied.
"""


# ==========================================================
# SIMPLE DATE PARSING (mock LLM only)
# ==========================================================

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

MONTH_DAY_PATTERN = re.compile(
    r"\b(" + "|".join(MONTHS.keys()) + r")\.?\s+(\d{1,2})\b",
    re.IGNORECASE
)

DAY_MONTH_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(MONTHS.keys()) + r")\b",
    re.IGNORECASE
)


def parse_dates(message: str):
    """
    Find up to two dates in a message, in either "Month Day"
    (e.g. "September 10") or "Day Month" (e.g. "10 September")
    order.

    Does NOT invent dates. Returns (check_in, check_out) as
    ISO date strings ("YYYY-MM-DD"), or None where not found.

    Matches are read in the order they appear in the message,
    so the first date mentioned is treated as check-in and the
    second as check-out.
    """

    found = []

    for match in MONTH_DAY_PATTERN.finditer(message):
        found.append((match.start(), match.group(1), match.group(2)))

    for match in DAY_MONTH_PATTERN.finditer(message):
        found.append((match.start(), match.group(2), match.group(1)))

    found.sort(key=lambda item: item[0])

    if not found:
        return None, None

    today = date.today()

    def to_iso(month_name, day_str):
        month = MONTHS[month_name.lower()]
        day = int(day_str)

        year = today.year

        try:
            candidate = date(year, month, day)
        except ValueError:
            return None

        # If the date has already passed this year, assume next year.
        if candidate < today:
            candidate = date(year + 1, month, day)

        return candidate.isoformat()

    check_in = to_iso(found[0][1], found[0][2]) if len(found) >= 1 else None
    check_out = to_iso(found[1][1], found[1][2]) if len(found) >= 2 else None

    return check_in, check_out


# ==========================================================
# GENERIC FIELD PARSING (mock LLM only)
# ==========================================================

def _known_destinations():
    """
    Pull real destinations from the hotel inventory instead of
    hardcoding "Goa". Keeps the mock extractor in sync with
    whatever cities actually exist in data/hotels.json.
    """
    try:
        from tools import load_hotels
        hotels = load_hotels()
        return {hotel["location"].lower(): hotel["location"] for hotel in hotels}
    except Exception:
        # Fallback so llm.py still works if tools.py import fails
        # for any reason (e.g. running llm.py in isolation).
        return {"goa": "Goa", "mumbai": "Mumbai", "manali": "Manali"}


GUEST_PATTERN = re.compile(
    r"(-?\d+)\s*(?:guests?|people|pax|adults?|of us)",
    re.IGNORECASE
)

# Budget patterns, checked in priority order. Each one requires the
# number to be directly adjacent to a budget-specific signal (currency
# symbol, "k" suffix, the word "budget", a "per night" style suffix,
# or an explicit correction phrase) so a guest count or date elsewhere
# in the same message is never mistaken for a budget.
BUDGET_PATTERNS = [
    re.compile(r"₹\s*(-?[\d,]+)\s*(k)?", re.IGNORECASE),
    re.compile(r"\brs\.?\s*(-?[\d,]+)\s*(k)?", re.IGNORECASE),
    re.compile(r"(-?[\d,]+)\s*(k)?\s*(?:per night|/night|rupees)\b", re.IGNORECASE),
    re.compile(r"budget[^\d\-]{0,20}(-?[\d,]+)\s*(k)?", re.IGNORECASE),
    re.compile(
        r"(?:make it|instead|change (?:it )?to)[^\d\-]{0,10}(-?[\d,]+)\s*(k)?",
        re.IGNORECASE
    ),
    re.compile(r"(-?\d+)\s*(k)\b", re.IGNORECASE),
]


def parse_guests(message_lower: str):
    """
    Extract a guest count. Returns an int (possibly 0 or
    negative, so the caller can validate it) or None if no
    guest count was mentioned at all.
    """

    match = GUEST_PATTERN.search(message_lower)
    if match:
        return int(match.group(1))

    # A few explicit word-numbers used in the original demo script.
    if "four" in message_lower:
        return 4
    if "two" in message_lower:
        return 2

    return None


def parse_budget(message_lower: str):
    """
    Extract a budget amount. Returns a number (possibly 0 or
    negative, so the caller can validate it) or None if no
    budget-looking number was mentioned.

    Tries each BUDGET_PATTERNS entry in order and uses the first
    match. Each pattern requires the number to sit directly next
    to a budget-specific signal, so a guest count or date elsewhere
    in the same message is never mistaken for a budget (e.g. "4 of
    us... budget is 2000" correctly extracts 2000, not 4).
    """

    for pattern in BUDGET_PATTERNS:
        match = pattern.search(message_lower)

        if not match or not match.group(1):
            continue

        number = match.group(1).replace(",", "")

        try:
            value = int(number)
        except ValueError:
            continue

        if len(match.groups()) > 1 and match.group(2):  # "k" suffix
            value *= 1000

        return value

    return None


def extract_guest_intent(message: str):

    if USE_MOCK_LLM:
        message_lower = message.lower()

    intent = {
        "destination": None,
        "check_in": None,
        "check_out": None,
        "guests": None,
        "rooms": None,
        "budget": None,
        "preference": None,
        "preferences": []
    }

    # Destination — checked against the real hotel inventory.
    for lower_name, display_name in _known_destinations().items():
        if lower_name in message_lower:
            intent["destination"] = display_name
            break

    # Guests
    intent["guests"] = parse_guests(message_lower)

    # Budget
    intent["budget"] = parse_budget(message_lower)

    # Preferences — collect ALL matches, not just the last one.
    preferences_found = []

    if "pool" in message_lower:
        preferences_found.append("pool")

    if "beach" in message_lower:
        preferences_found.append("beach")

    intent["preferences"] = preferences_found
    intent["preference"] = preferences_found[0] if preferences_found else None

    # Dates
    check_in, check_out = parse_dates(message)
    intent["check_in"] = check_in
    intent["check_out"] = check_out

    return intent

    prompt = SYSTEM_PROMPT + f"""

Guest message:

{message}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
    except Exception as e:
        print(f"Gemini API error: {e}")
        raise

    text = response.text.strip()

    # Remove markdown code fences if Gemini adds them
    if text.startswith("```"):
        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

    return json.loads(text)


# ==========================================================
# MIRA FINAL RESPONSE
# ==========================================================

def generate_hotel_response(guest_message, hotel_results):

    if not hotel_results:
        return (
            "I couldn't find a hotel matching your requirements. "
            "Would you like to increase your budget or try another destination?"
        )

    best_hotel = hotel_results[0]

    response = "🏆 I found a great match for you!\n\n"

    response += f"🏨 {best_hotel['hotel_name']}\n"
    response += f"📍 {best_hotel['location']}\n"

    # --------------------------------
    # Best room
    # --------------------------------

    if best_hotel.get("rooms"):

        room = best_hotel["rooms"][0]

        response += "\n🛏️ Recommended room:\n"

        response += (
            f"• {room['name']}\n"
            f"• ₹{room['price_per_night']}/night\n"
            f"• Suitable for up to {room['capacity']} guests\n"
        )

        if room.get("amenities"):
            response += (
                f"• Amenities: "
                f"{', '.join(room['amenities'])}\n"
            )

    # --------------------------------
    # Recommendation score
    # --------------------------------

    score = best_hotel.get("recommendation_score")

    if score is not None:
        response += f"\n⭐ Match score: {score}/100\n"

    # --------------------------------
    # Recommendation reasons
    # --------------------------------

    reasons = best_hotel.get(
        "recommendation_reasons",
        []
    )

    if reasons:

        response += "\n💡 Why this is a good match:\n"

        for reason in reasons:
            response += f"✓ {reason}\n"

    # --------------------------------
    # Alternatives
    # --------------------------------

    if len(hotel_results) > 1:

        response += "\n🔎 Other options:\n"

        for hotel in hotel_results[1:3]:

            if hotel.get("rooms"):

                room = hotel["rooms"][0]

                response += (
                    f"• {hotel['hotel_name']} — "
                    f"₹{room['price_per_night']}/night\n"
                )

    response += (
        "\nWould you like to select this hotel?"
    )

    return response

    # YOUR EXISTING GEMINI CODE BELOW
    ...

    # existing Gemini code below this
    prompt = f"""
You are Mira, an AI hospitality assistant.

Guest message:
{guest_message}

Hotel search results from the hotel's database:
{json.dumps(hotel_results, indent=2)}

Your task is to respond naturally and helpfully to the guest.

Rules:
- Use ONLY the hotel information provided in the search results.
- Do not invent hotels.
- Do not invent prices.
- Do not invent availability.
- Do not invent amenities.
- Mention the hotel name, room type and price when available.
- Explain briefly why the option fits the guest's request.
- Keep the response concise and conversational.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text.strip()