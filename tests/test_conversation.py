from agent.agent import MiraAgent


mira = MiraAgent()


messages = [
    "I want a hotel in Goa.",
    "There will be 4 of us.",
    "Our budget is around 15000 per night.",
    "1",
    "1",
    "Yes",
    "Check in September 10 and check out September 13."
]


for message in messages:

    print("\n================================")
    print("GUEST:", message)

    response = mira.process_message(message)

    print("\nMIRA:")
    print(response["message"])

    print("\nSTATE:")
    print(response["state"])
    print("Booking status:", response["state"]["booking_status"])
