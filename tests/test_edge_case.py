from agent import MiraAgent


def run_scenario(name, messages):
    print(f"\n\n========== {name} ==========")
    mira = MiraAgent()

    for message in messages:
        print(f"\nGUEST: {message}")
        response = mira.process_message(message)
        print(f"MIRA: {response['message']}")
        print(f"STATUS: {response['state']['booking_status']}")


# 1. Missing destination
run_scenario("Missing destination", [
    "I need a hotel.",
])

# 2. Missing guests
run_scenario("Missing guests", [
    "I want a hotel in Goa.",
])

# 3. Missing budget
run_scenario("Missing budget", [
    "I need a hotel in Goa for 4 people.",
])

# 4. No hotel results (budget too low)
run_scenario("No results", [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "My budget is 2000 per night.",
])

# 5. Invalid guests
run_scenario("Invalid guests (0)", [
    "I want a hotel in Goa.",
    "0 guests",
])

# 6. Invalid budget
run_scenario("Invalid budget (negative)", [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "My budget is ₹-5000",
])

# 7. Guest changes budget mid-flow
run_scenario("Change budget mid-flow", [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "Our budget is around 15000 per night.",
    "Actually make it 20000.",
])

# 8. Guest changes destination mid-flow
run_scenario("Change destination mid-flow", [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "Our budget is around 15000 per night.",
    "Actually, Mumbai.",
])

# 9. Invalid hotel selection
run_scenario("Invalid hotel selection", [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "Our budget is around 15000 per night.",
    "I want Hotel XYZ",
])

# 10. Invalid room selection
run_scenario("Invalid room selection", [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "Our budget is around 15000 per night.",
    "1",
    "I want the Presidential Suite",
])