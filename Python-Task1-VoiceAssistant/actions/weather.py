"""
Weather Action module.
Queries the OpenWeatherMap API to retrieve current weather conditions.
Supports a simulated fallback if no API key is configured.
"""

import requests
import sys
import random
from actions.base import BaseAction
from config.settings import settings
from core.nlu import INTENT_WEATHER

class WeatherAction(BaseAction):
    @property
    def name(self) -> str:
        return INTENT_WEATHER

    def execute(self, entities: dict) -> dict:
        location = entities.get("location", "").strip()

        if not location:
            return {
                "speech": "Which city would you like the weather forecast for?",
                "ui_data": {"status": "error", "message": "Missing location"}
            }

        # Format city name for query
        city = location.title()

        # Check if API Key is configured
        if not settings.WEATHER_API_KEY:
            return self._simulate_weather(city)
        else:
            return self._fetch_live_weather(city)

    def _simulate_weather(self, city: str) -> dict:
        """Simulates weather data when no API key is provided."""
        conditions = ["clear sky", "light rain", "overcast clouds", "scattered clouds", "foggy", "mist"]
        condition = random.choice(conditions)
        temp = random.randint(15, 32) if condition in ("clear sky", "scattered clouds") else random.randint(8, 20)
        humidity = random.randint(40, 95)
        
        speech_text = (
            f"Weather key is missing. Simulating: "
            f"The weather in {city} is currently {condition} with a temperature of {temp} degrees Celsius and {humidity} percent humidity."
        )

        return {
            "speech": speech_text,
            "ui_data": {
                "status": "simulated",
                "location": city,
                "temp": temp,
                "condition": condition,
                "humidity": humidity,
                "api_key_missing": True
            }
        }

    def _fetch_live_weather(self, city: str) -> dict:
        """Fetches live weather from OpenWeatherMap API."""
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": settings.WEATHER_API_KEY,
            "units": "metric"  # Retrieve in Celsius
        }

        try:
            print(f"Fetching live weather for {city} from OpenWeatherMap...")
            response = requests.get(url, params=params, timeout=8)
            
            if response.status_code == 200:
                data = response.json()
                temp = round(data["main"]["temp"])
                humidity = data["main"]["humidity"]
                condition = data["weather"][0]["description"]
                
                speech_text = f"The weather in {city} is currently {condition} with a temperature of {temp} degrees Celsius and {humidity} percent humidity."
                return {
                    "speech": speech_text,
                    "ui_data": {
                        "status": "success",
                        "location": city,
                        "temp": temp,
                        "condition": condition,
                        "humidity": humidity
                    }
                }
            elif response.status_code == 404:
                return {
                    "speech": f"I couldn't find the city '{city}' on OpenWeatherMap. Please check the spelling.",
                    "ui_data": {"status": "error", "message": "City not found"}
                }
            elif response.status_code == 401:
                return {
                    "speech": "My weather service API key is invalid. Please update the API key in the settings panel.",
                    "ui_data": {"status": "error", "message": "Unauthorized API key"}
                }
            else:
                return {
                    "speech": f"Sorry, I received an unexpected response from the weather service. Status code {response.status_code}.",
                    "ui_data": {"status": "error", "message": f"HTTP {response.status_code}"}
                }
                
        except requests.RequestException as e:
            print(f"Weather API request error: {e}", file=sys.stderr)
            return {
                "speech": "I had trouble connecting to the live weather service. Check your internet connection.",
                "ui_data": {"status": "error", "message": "Network exception"}
            }
        except Exception as e:
            print(f"Weather parsing error: {e}", file=sys.stderr)
            return {
                "speech": "I had an unexpected issue reading the weather report.",
                "ui_data": {"status": "error", "message": "Parsing error"}
            }
