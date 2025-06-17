# PArisNeoMCPServers/utils-mcp-server/utils_mcp_server/utils_wrapper.py
import asyncio
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from ascii_colors import ASCIIColors, trace_exception

# --- API Configuration ---
GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
CRYPTO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# --- Core Wrapper Functions ---

async def get_current_time(timezone_str: str = "UTC") -> Dict[str, Any]:
    """
    Gets the current time. Currently, only UTC is supported.
    """
    ASCIIColors.info(f"Utils Wrapper: Getting current time for timezone '{timezone_str}'.")
    if timezone_str.upper() != "UTC":
        return {
            "error": "Invalid timezone specified. Currently, only 'UTC' is supported."
        }
    
    try:
        now_utc = datetime.now(timezone.utc)
        return {
            "status": "success",
            "timezone": "UTC",
            "iso_format": now_utc.isoformat(),
            "pretty_format": now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    except Exception as e:
        trace_exception(e)
        return {"error": f"An unexpected error occurred while getting the time: {e}"}

async def get_weather_forecast(location: str) -> Dict[str, Any]:
    """
    Gets the current weather for a given location using a free, no-key API.
    Example locations: "Paris, France", "Tokyo", "New York"
    """
    ASCIIColors.info(f"Utils Wrapper: Getting weather for location '{location}'.")
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Geocode the location to get latitude and longitude
            geo_params = {'name': location, 'count': 1, 'language': 'en', 'format': 'json'}
            geo_response = await client.get(GEOCODING_API_URL, params=geo_params)
            geo_response.raise_for_status()
            geo_data = geo_response.json()

            if not geo_data.get('results'):
                return {"error": f"Location '{location}' could not be found."}
            
            location_info = geo_data['results'][0]
            lat = location_info['latitude']
            lon = location_info['longitude']
            display_name = location_info.get('name', location)
            
            # 2. Get weather forecast for the coordinates
            weather_params = {
                'latitude': lat,
                'longitude': lon,
                'current_weather': 'true'
            }
            weather_response = await client.get(WEATHER_API_URL, params=weather_params)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            current_weather = weather_data.get('current_weather')
            if not current_weather:
                 return {"error": f"Could not retrieve current weather data for '{location}'."}

            return {
                "status": "success",
                "location": display_name,
                "country_code": location_info.get('country_code'),
                "latitude": f"{lat:.4f}",
                "longitude": f"{lon:.4f}",
                "temperature_celsius": current_weather.get('temperature'),
                "wind_speed_kmh": current_weather.get('windspeed'),
                "summary": f"Current weather for {display_name}: Temperature is {current_weather.get('temperature')}°C with wind speeds of {current_weather.get('windspeed')} km/h."
            }

        except httpx.HTTPStatusError as e:
            trace_exception(e)
            return {"error": f"API request failed with status {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            trace_exception(e)
            return {"error": f"An unexpected error occurred: {e}"}

async def get_bitcoin_price(currency: str = "usd") -> Dict[str, Any]:
    """
    Gets the current price of Bitcoin in a specified fiat currency (e.g., 'usd', 'eur', 'jpy').
    """
    ASCIIColors.info(f"Utils Wrapper: Getting Bitcoin price in '{currency}'.")
    normalized_currency = currency.lower()

    async with httpx.AsyncClient() as client:
        try:
            params = {'ids': 'bitcoin', 'vs_currencies': normalized_currency}
            response = await client.get(CRYPTO_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'bitcoin' not in data or normalized_currency not in data['bitcoin']:
                return {"error": f"Could not retrieve Bitcoin price for currency '{currency}'. The currency may be invalid."}
            
            price = data['bitcoin'][normalized_currency]
            
            return {
                "status": "success",
                "coin": "Bitcoin",
                "currency": normalized_currency.upper(),
                "price": price
            }

        except httpx.HTTPStatusError as e:
            trace_exception(e)
            return {"error": f"API request failed with status {e.response.status_code}. The currency '{currency}' may not be supported."}
        except Exception as e:
            trace_exception(e)
            return {"error": f"An unexpected error occurred: {e}"}

# --- Standalone Test Block ---
if __name__ == '__main__':
    import json

    async def test_utils_wrapper():
        ASCIIColors.red("--- Testing Utils Wrapper ---")

        # 1. Test Time
        ASCIIColors.magenta("\n1. Getting current time (UTC)...")
        time_res = await get_current_time()
        print(json.dumps(time_res, indent=2))
        assert time_res["status"] == "success"
        
        # 2. Test Time (Error)
        ASCIIColors.magenta("\n2. Getting current time (invalid timezone)...")
        time_err_res = await get_current_time("PST")
        print(json.dumps(time_err_res, indent=2))
        assert "error" in time_err_res

        # 3. Test Weather
        ASCIIColors.magenta("\n3. Getting weather for 'Tokyo, Japan'...")
        weather_res = await get_weather_forecast("Tokyo, Japan")
        print(json.dumps(weather_res, indent=2))
        assert weather_res["status"] == "success"
        
        # 4. Test Weather (Error)
        ASCIIColors.magenta("\n4. Getting weather for invalid location 'Nowhereland'...")
        weather_err_res = await get_weather_forecast("Nowhereland12345")
        print(json.dumps(weather_err_res, indent=2))
        assert "error" in weather_err_res

        # 5. Test Bitcoin Price
        ASCIIColors.magenta("\n5. Getting Bitcoin price in USD...")
        btc_res_usd = await get_bitcoin_price("usd")
        print(json.dumps(btc_res_usd, indent=2))
        assert btc_res_usd["status"] == "success"
        assert btc_res_usd["currency"] == "USD"
        
        # 6. Test Bitcoin Price (EUR)
        ASCIIColors.magenta("\n6. Getting Bitcoin price in EUR...")
        btc_res_eur = await get_bitcoin_price("eur")
        print(json.dumps(btc_res_eur, indent=2))
        assert btc_res_eur["status"] == "success"
        assert btc_res_eur["currency"] == "EUR"
        
        # 7. Test Bitcoin Price (Error)
        ASCIIColors.magenta("\n7. Getting Bitcoin price in invalid currency 'XYZ'...")
        btc_err_res = await get_bitcoin_price("XYZ")
        print(json.dumps(btc_err_res, indent=2))
        assert "error" in btc_err_res

        ASCIIColors.red("\n--- Utils Wrapper Tests Finished ---")

    asyncio.run(test_utils_wrapper())