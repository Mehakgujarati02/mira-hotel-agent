from state import GuestState


state = GuestState()

print("Initial state:")
print(state.summary())

state.update(
    destination="Goa",
    guests=4,
    budget=20000
)

print("\nAfter first update:")
print(state.summary())

state.update(guests=5)

print("\nAfter guest changes number of guests:")
print(state.summary())