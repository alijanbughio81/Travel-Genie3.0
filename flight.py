import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_flights(origin, destination, budget, travelers, duration):
    """
    Finds flight options for the trip.

    NOTE: unlike the original Gemini version, Groq does not have a built-in
    Google Search grounding tool attached here — this relies on the model's
    own knowledge, so fares may be less current. If real-time accuracy
    matters, look into adding a search tool (e.g. Tavily) later.

    Inputs:
        origin: string, e.g. "Karachi" — needed since flights need a starting point
        destination: string, e.g. "Istanbul"
        budget: number, the user's total trip budget (same value used across all agents)
        travelers: number of people
        duration: trip length in days (used only for context, not fare calc)

    Returns:
        list of flight dicts, EXACTLY matching the team's agreed contract:
        [
          {
            "airline": "PIA",
            "price": 25000,
            "departure_time": "08:00",
            "arrival_time": "10:30",
            "from": "Karachi",
            "to": "Istanbul"
          },
          ...
        ]
    """

    prompt = f"""
You are a travel research assistant finding flight options.

Origin: {origin}
Destination: {destination}
Number of travelers: {travelers}
Trip length: {duration} days
User's total trip budget (whole trip, all expenses): {budget}

Task:
1. Suggest 5 realistic flight options from {origin} to {destination}, keeping the overall trip budget of {budget} in mind (flights should be a reasonable share of it, not the whole amount).
2. Give a spread of price points so there's something to choose between.
3. price should be the PER PERSON one-way (or round-trip, pick one and stay consistent) fare — don't multiply by travelers, that's done later by another agent.
4. If a precise fare can't be determined, give a realistic estimated number anyway rather than leaving it blank.

Return ONLY valid JSON, no extra text, no markdown — a JSON array of EXACTLY 5 objects in this format:
[
  {{
    "airline": "<airline name>",
    "price": <number>,
    "departure_time": "<HH:MM>",
    "arrival_time": "<HH:MM>",
    "from": "{origin}",
    "to": "{destination}"
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
    result = get_flights(origin="Karachi, Pakistan", destination="Istanbul, Turkey", budget=100000, travelers=3, duration=4)
    print(json.dumps(result, indent=2))
