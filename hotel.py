import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_hotels(destination, budget, travelers, duration):
    """
    Finds hotel options for the trip.

    NOTE: unlike the original Gemini version, Groq does not have a built-in
    Google Search grounding tool attached here — this relies on the model's
    own knowledge, so prices/names may be less current. If real-time accuracy
    matters, look into adding a search tool (e.g. Tavily) later.

    Inputs:
        destination: string, e.g. "Istanbul, Turkey"
        budget: number, the user's total trip budget (same value used across all agents)
        travelers: number of people
        duration: number of nights for the stay

    Returns:
        list of hotel dicts, EXACTLY matching the team's agreed contract:
        [
          {
            "name": "Hotel Sunrise",
            "price_per_night": 8000,
            "rating": 4.2,
            "location": "City Center",
            "amenities": ["wifi", "breakfast included"]
          },
          ...
        ]
    """

    prompt = f"""
You are a travel research assistant finding hotel options.

Destination: {destination}
Number of travelers: {travelers}
Trip length: {duration} nights
User's total trip budget (whole trip, all expenses): {budget}

Task:
1. Suggest 5 realistic hotel options in {destination} that make sense for a group of {travelers}, keeping the overall trip budget of {budget} in mind (hotel should be a reasonable share of it, not the whole amount).
2. Give a spread of price points so there's something to choose between.
3. Do not invent exact prices/ratings you're unsure of — give a realistic estimate if uncertain.

Return ONLY valid JSON, no extra text, no markdown — a JSON array of EXACTLY 5 objects in this format:
[
  {{
    "name": "<hotel name>",
    "price_per_night": <number>,
    "rating": <number>,
    "location": "<area/neighborhood>",
    "amenities": ["<amenity>", "..."]
  }}
]
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",  
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2000,
    )

    raw_text = response.choices[0].message.content.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("[")
        end = raw_text.rfind("]") + 1
        try:
            return json.loads(raw_text[start:end])
        except Exception:
            return []


# quick manual test — run this file directly to check it works
if __name__ == "__main__":
    result = get_hotels(destination="Istanbul, Turkey", budget=100000, travelers=3, duration=4)
    print(json.dumps(result, indent=2))
