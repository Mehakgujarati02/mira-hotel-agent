from booking import calculate_booking, create_booking


print("TEST 1: Calculate booking")

result = calculate_booking(
    hotel_id="HT001",
    room_id="PR_FAMILY",
    nights=3,
    guests=4,
    add_ons=["BREAKFAST"]
)

print(result)


print("\nTEST 2: Create booking")

booking = create_booking(
    hotel_id="HT001",
    room_id="PR_FAMILY",
    nights=3,
    guests=4,
    guest_name="Mehak",
    add_ons=["BREAKFAST"]
)

print(booking)