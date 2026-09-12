import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def get_activities(destination, budget, travelers, duration, preferences=None):
    """
    Suggests activities / things-to-do for the trip.

    NOTE: like the other agents, this relies on the model's own knowledge of
    common tourist attractions. If you want fresher pricing, plug in a search
    tool (Tavily / SerpAPI) later — same pattern as the other agents.

    Inputs:
        destination: string, e.g. "Istanbul, Turkey"
        budget: number, user's total trip budget (same value used across all agents)
        travelers: number of people
        duration: number of nights / days
        preferences: optional list of strings, e.g. ["outdoor", "food", "culture"]

    Returns:
        list of activity dicts, EXACTLY in this format:
        [
          {
            "name": "Hagia Sophia Tour",
            "category": "culture",          # culture | food | outdoor | adventure | shopping | relaxation
            "estimated_cost": 2000,         # PER PERSON, in PKR (or local currency)
            "duration_hours": 2.5,
            "best_time_of_day": "morning",  # morning | afternoon | evening | any
            "indoor_outdoor": "indoor",     # indoor | outdoor | both
            "description": "Short 1-line blurb."
          },
          ...
        ]
    """

    pref_text = (
        f"User's interests / preferences: {', '.join(preferences)}"
        if preferences
        else "User has not specified preferences — give a balanced mix."
    )

    prompt = f"""
You are a travel research assistant finding activities / things-to-do.

Destination: {destination}
Number of travelers: {travelers}
Trip length: {duration} days
User's total trip budget (whole trip, all expenses): {budget}
{pref_text}

Task:
1. Suggest 8 realistic, well-known activities / attractions in {destination}.
2. Spread across categories (culture, food, outdoor, adventure, shopping, relaxation) so there's something for any mood.
3. Keep total activity cost reasonable — these are a slice of the overall budget of {budget}, not the whole thing.
4. estimated_cost is PER PERSON in PKR. If free (mosque visit, walking tour, public beach, etc.) use 0.
5. If unsure about exact cost, give a realistic estimate anyway rather than leaving it blank.
6. duration_hours is how long the activity typically takes (number, can be 0.5 increments).
7. best_time_of_day: morning / afternoon / evening / any.
8. indoor_outdoor: indoor / outdoor / both.
9. description: 1 short sentence, friendly tone.

Return ONLY valid JSON, no extra text, no markdown — a JSON array of EXACTLY 8 objects in this format:
[
  {{
    "name": "<activity name>",
    "category": "<one of: culture | food | outdoor | adventure | shopping | relaxation>",
    "estimated_cost": <number>,
    "duration_hours": <number>,
    "best_time_of_day": "<morning | afternoon | evening | any>",
    "indoor_outdoor": "<indoor | outdoor | both>",
    "description": "<short 1-line blurb>"
  }}
]
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2500,
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
    result = get_activities(
        destination="Istanbul, Turkey",
        budget=100000,
        travelers=3,
        duration=4,
        preferences=["culture", "food"],
    )
    print(json.dumps(result, indent=2))
