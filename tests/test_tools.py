from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

from tools import hotel_search_tool


# ==========================================================
# LOAD ENVIRONMENT
# ==========================================================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ==========================================================
# DEFINE HOTEL SEARCH TOOL
# ==========================================================

tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="hotel_search_tool",
            description=(
                "Search available hotels based on destination, "
                "number of guests, and maximum budget per night."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "destination": types.Schema(
                        type="STRING",
                        description="The destination the guest wants to visit."
                    ),
                    "guests": types.Schema(
                        type="INTEGER",
                        description="Number of guests."
                    ),
                    "budget": types.Schema(
                        type="INTEGER",
                        description="Maximum budget per night in Indian Rupees."
                    )
                },
                required=[
                    "destination",
                    "guests",
                    "budget"
                ]
            )
        )
    ]
)


# ==========================================================
# GUEST REQUEST
# ==========================================================

guest_message = """
I want to stay in Goa.
There are 4 of us.
Our budget is 15000 rupees per night.

Find suitable hotels for me.
"""


# ==========================================================
# FIRST GEMINI REQUEST
# ==========================================================

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=guest_message,
    config=types.GenerateContentConfig(
        tools=[tool]
    )
)


# ==========================================================
# CHECK FUNCTION CALL
# ==========================================================

print("\n========== GEMINI TOOL DECISION ==========")

if response.function_calls:

    for function_call in response.function_calls:

        print("Function:", function_call.name)
        print("Arguments:", function_call.args)

        # ==================================================
        # EXECUTE TOOL
        # ==================================================

        if function_call.name == "hotel_search_tool":

            tool_result = hotel_search_tool(
                destination=function_call.args["destination"],
                guests=function_call.args["guests"],
                budget=function_call.args["budget"]
            )

            print("\n========== TOOL RESULT ==========")
            print(tool_result)

            # ==================================================
            # SEND TOOL RESULT BACK TO GEMINI
            # ==================================================

            final_prompt = f"""
You are Mira, an AI hospitality assistant.

The guest asked:

{guest_message}

You searched the hotel inventory using the hotel search tool.

The tool returned:

{tool_result}

Based ONLY on the tool results, give the guest a helpful,
concise recommendation.

Mention:
- hotel name
- room type
- price per night
- why it fits their request

Do not invent hotels, prices, availability, or amenities.
"""

            final_response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=final_prompt
            )

            # ==================================================
            # FINAL RESPONSE
            # ==================================================

            print("\n========== MIRA'S RESPONSE ==========")
            print(final_response.text)

else:

    print("\nGemini did not request a hotel search.")
    print("Gemini response:")
    print(response.text)