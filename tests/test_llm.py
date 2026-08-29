from llm import extract_guest_intent


message = """
I want to visit Goa for 4 people.
My budget is around 20k per night.
I'd really like a place with a pool.
"""

result = extract_guest_intent(message)

print(result)