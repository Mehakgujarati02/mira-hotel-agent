from agent import MiraAgent


mira = MiraAgent()

message = """
I want to visit Goa for 4 people.
My budget is around 20k per night.
I'd really like a place with a pool.
"""

results = mira.process_message(message)

print("\n========== HOTEL RESULTS ==========")

if not results:
    print("No matching hotels found.")

else:
    for hotel in results:
        print(f"\n🏨 {hotel['hotel_name']}")
        print(f"Location: {hotel['location']}")
        print(f"Description: {hotel['description']}")

        for room in hotel["rooms"]:
            print(
                f"  {room['name']} - "
                f"₹{room['price_per_night']}/night"
            )