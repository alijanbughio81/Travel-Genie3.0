import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
 
 
def calculate_budget(flights, hotels, activities, user_budget, travelers, duration):
    """
    Takes the outputs from flights, hotels, and activities agents,
    the user's total budget, number of travelers, and trip duration (nights).
    Picks ONE flight, ONE hotel, and a set of activities that fit the budget,
    accounting for group size and length of stay.
 
    Inputs:
        flights: list of flight dicts (each has "price" — price is PER PERSON)
        hotels: list of hotel dicts (each has "price_per_night" — price is PER ROOM, PER NIGHT)
        activities: list of activity dicts (each has "estimated_cost" — cost is PER PERSON)
        user_budget: number, total budget the user entered (for the whole group)
        travelers: number of people traveling
        duration: number of days of the trip (nights stayed = duration - 1, but for
                   simplicity in a hackathon demo, treat duration as nights needed)
 
    Returns:
        dict like:
        {
          "chosen_flight": {...},
          "chosen_hotel": {...},
          "rooms_needed": 2,
          "chosen_activities": [...],
          "total_estimated_cost": 95000,
          "user_budget": 100000,
          "within_budget": true,
          "breakdown": {"flights": 25000, "hotels": 40000, "activities": 15000, "misc": 15000},
          "suggestions": ["..."]
        }
    """
 
    prompt = f"""
You are a travel budget planning assistant.
 
Here is the trip data (all prices in PKR):
 
Flights (price is PER PERSON): {json.dumps(flights)}
Hotels (price_per_night is PER ROOM): {json.dumps(hotels)}
Activities (estimated_cost is PER PERSON): {json.dumps(activities)}
User's total budget (for the whole group): {user_budget}
Number of travelers: {travelers}
Trip duration: {duration} nights
 
Task:
1. From the given flights, CHOOSE the single best flight option. Multiply its price by {travelers} to get total flight cost.
2. From the given hotels, CHOOSE the single best hotel option. Assume 2 travelers can share 1 room — calculate rooms_needed by rounding up ({travelers} travelers / 2). Total hotel cost = price_per_night × rooms_needed × {duration} nights.
3. From activities, choose a reasonable selection that fits the remaining budget. Multiply each activity's per-person cost by {travelers}.
4. Add a small "misc" buffer (food, local transport, etc.) scaled to group size.
5. Add up total cost across flights + hotels + activities + misc, and compare to the user's budget.
6. If over budget even with cheapest options, say so and suggest what to cut.
 
Return ONLY valid JSON, no extra text, no markdown, in EXACTLY this format:
{{
  "chosen_flight": <flight object>,
  "chosen_hotel": <hotel object>,
  "rooms_needed": <number>,
  "chosen_activities": [<activity object>, "..."],
  "total_estimated_cost": <number>,
  "user_budget": {user_budget},
  "within_budget": <true or false>,
  "breakdown": {{
    "flights": <number>,
    "hotels": <number>,
    "activities": <number>,
    "misc": <number>
  }},
  "suggestions": ["<string>", "..."]
}}
"""
 
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
 
    raw_text = response.choices[0].message.content.strip()
 
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}") + 1
        try:
            return json.loads(raw_text[start:end])
        except Exception:
            return {
                "chosen_flight": None,
                "chosen_hotel": None,
                "rooms_needed": 0,
                "chosen_activities": [],
                "total_estimated_cost": 0,
                "user_budget": user_budget,
                "within_budget": False,
                "breakdown": {"flights": 0, "hotels": 0, "activities": 0, "misc": 0},
                "suggestions": ["Could not calculate budget — check agent output."],
            }
 
 
# quick manual test — run this file directly to check it works
if __name__ == "__main__":
    fake_flights = [
        {"airline": "PIA", "price": 25000, "departure_time": "08:00", "arrival_time": "10:30"},
        {"airline": "AirBlue", "price": 18000, "departure_time": "14:00", "arrival_time": "16:30"},
        {"airline": "SereneAir", "price": 30000, "departure_time": "06:00", "arrival_time": "08:30"},
    ]
    fake_hotels = [
        {"name": "Hotel Sunrise", "price_per_night": 8000, "rating": 4.2},
        {"name": "Budget Inn", "price_per_night": 4500, "rating": 3.5},
        {"name": "Grand Palace", "price_per_night": 15000, "rating": 4.8},
    ]
    fake_activities = [
        {"name": "Faisal Mosque", "estimated_cost": 0},
        {"name": "Lok Virsa Museum", "estimated_cost": 500},
        {"name": "Monal Restaurant Dinner", "estimated_cost": 3000},
    ]
 
    result = calculate_budget(fake_flights, fake_hotels, fake_activities, user_budget=100000, travelers=3, duration=4)
    print(json.dumps(result, indent=2))
 
