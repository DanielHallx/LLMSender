import requests
import logging
from typing import Dict, Any
from core.interfaces import ContentProvider
from core.utils import retry_with_backoff, get_env_var

logger = logging.getLogger(__name__)


class WeatherProvider(ContentProvider):
    """Fetch weather data from OpenWeatherMap API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = get_env_var('OPENWEATHER_API_KEY') or config.get('api_key')
        self.lat = config.get('lat')
        self.lon = config.get('lon')
        self.city_name = config.get('city_name')
        if not all([self.lat, self.lon, self.city_name]):
            raise ValueError("Latitude, longitude, and city_name are required in config")
        self.units = config.get('units', 'metric')
        self.language = config.get('language', 'zh-cn')
        
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is required")
        if not isinstance(self.lat, (int, float)) or not isinstance(self.lon, (int, float)):
            raise ValueError("Latitude and longitude must be numeric values")
    
    def get_prompt(self) -> str:
        """Return the prompt for AI to summarize weather data."""
        return (
            f"请用简洁、对话式的方式总结{self.city_name}的天气信息。包括温度、天气状况以及任何值得注意的天气特征。控制在100字以内，适合作为每日早晨的通知。不需要备注，直接输出内容"
        )
    
    @retry_with_backoff(max_retries=3, exceptions=(requests.RequestException,))
    def fetch(self) -> str:
        """Fetch weather data using One Call 3.0 API."""
        try:
            # Use One Call 3.0 API with coordinates
            url = (
                f"https://api.openweathermap.org/data/3.0/onecall"
                f"?lat={self.lat}&lon={self.lon}&appid={self.api_key}"
                f"&units={self.units}&lang={self.language}"
                f"&exclude=minutely,alerts"
            )
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Format the data
            result = self._format_weather_data(data)
            logger.info(f"Successfully fetched weather data for {self.city_name}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch weather data: {e}")
            raise
    
    def _format_weather_data(self, data: Dict) -> str:
        """Format One Call 3.0 API weather data into readable text."""
        temp_unit = "°C" if self.units == "metric" else "°F"
        speed_unit = "m/s" if self.units == "metric" else "mph"
        
        current = data['current']
        
        # Current weather
        current_weather = (
            f"Current weather in {self.city_name}:\n"
            f"Temperature: {current['temp']}{temp_unit} "
            f"(feels like {current['feels_like']}{temp_unit})\n"
            f"Conditions: {current['weather'][0]['description']}\n"
            f"Humidity: {current['humidity']}%\n"
            f"Wind: {current['wind_speed']} {speed_unit}\n"
        )
        
        # Today's forecast from hourly data
        hourly = data.get('hourly', [])
        if hourly:
            today_temps = []
            today_conditions = []
            
            for item in hourly[:8]:  # Next 24 hours
                today_temps.append(item['temp'])
                today_conditions.append(item['weather'][0]['main'])
            
            max_temp = max(today_temps)
            min_temp = min(today_temps)
            most_common_condition = max(set(today_conditions), key=today_conditions.count)
            
            forecast_summary = (
                f"\nToday's forecast:\n"
                f"High: {max_temp}{temp_unit}, Low: {min_temp}{temp_unit}\n"
                f"Mostly: {most_common_condition}\n"
            )
        else:
            # Fallback to daily forecast if hourly is not available
            daily = data.get('daily', [])
            if daily:
                today = daily[0]
                forecast_summary = (
                    f"\nToday's forecast:\n"
                    f"High: {today['temp']['max']}{temp_unit}, Low: {today['temp']['min']}{temp_unit}\n"
                    f"Conditions: {today['weather'][0]['description']}\n"
                )
            else:
                forecast_summary = "\nForecast data not available\n"
        
        return current_weather + forecast_summary


def factory(config: Dict[str, Any]) -> WeatherProvider:
    """Factory function to create WeatherProvider instance."""
    return WeatherProvider(config)