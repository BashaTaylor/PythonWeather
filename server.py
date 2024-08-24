import datetime
import pytz
from flask import Flask, render_template, request
from waitress import serve
from weather import get_current_weather, get_5_day_forecast

app = Flask(__name__)

def celsius_to_fahrenheit(celsius_temp):
    return (celsius_temp * 9/5) + 32

def fahrenheit_to_celsius(fahrenheit_temp):
    return (fahrenheit_temp - 32) * 5/9

def convert_temp(temp, from_unit, to_unit):
    if from_unit == to_unit:
        return temp  # No conversion needed
    if to_unit == 'C':
        return fahrenheit_to_celsius(temp)
    return celsius_to_fahrenheit(temp)

def get_weather_icon(icon_code):
    return f'http://openweathermap.org/img/wn/{icon_code}.png'

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/weather')
def get_weather():
    city = request.args.get('city', '').strip()
    if not city:
        city = "Plainville"

    unit = request.args.get('unit', 'F')  # Desired unit, default to Fahrenheit
    from_unit = 'F'  # Assuming the API returns temperatures in Fahrenheit by default

    weather_data = get_current_weather(city)
    forecast_data = get_5_day_forecast(city)

    if weather_data['cod'] != 200:
        return render_template('city-not-found.html')

    # Extract weather details including latitude and longitude
    current_description = weather_data["weather"][0]["description"].lower()
    temp = convert_temp(weather_data['main']['temp'], from_unit, unit)
    feels_like_temp = convert_temp(weather_data['main']['feels_like'], from_unit, unit)
    low_temp = convert_temp(weather_data['main']['temp_min'], from_unit, unit)
    humidity = weather_data['main']['humidity']
    wind_speed_mph = weather_data['wind']['speed'] * 2.237
    latitude = weather_data['coord']['lat']
    longitude = weather_data['coord']['lon']

    # Extract precipitation data (rain or snow)
    precipitation = 0  # Default to 0 if no precipitation data is found
    if 'rain' in weather_data and '1h' in weather_data['rain']:
        precipitation = weather_data['rain']['1h']  # Rainfall in the last hour
    elif 'snow' in weather_data and '1h' in weather_data['snow']:
        precipitation = weather_data['snow']['1h']  # Snowfall in the last hour

    # Determine the video file based on the weather description
    if "clear sky" in current_description:
        video_file = "clearsky.mp4"
    elif "sunny" in current_description:
        video_file = "sunny.mp4"
    elif "few clouds" in current_description:
        video_file = "fewclouds.mp4"
    elif "partly cloudy" in current_description or "scattered clouds" in current_description:
        video_file = "partly-cloudy.mp4"
    elif "overcast clouds" in current_description: 
        video_file = "overcast.mp4" 
    elif "broken clouds" in current_description:
        video_file = "brokenclouds.mp4"
    elif "light rain" in current_description:
        video_file = "lightrain.mp4"
    elif "rain" in current_description or "moderate rain" in current_description:
        video_file = "rain.mp4"
    elif "mist" in current_description or "smoke" in current_description or "fog" in current_description:
        video_file = "mist.mp4"
    elif "thunderstorm" in current_description:
        video_file = "thunderstorm.mp4"
    elif "hail" in current_description:
        video_file = "hail.mp4"
    elif "snow" in current_description:
        video_file = "snow.mp4"
    elif "tornado" in current_description:
        video_file = "tornado.mp4"
    else:
        video_file = "default.mp4"  # Fallback video

    # Timezone for EDT (Eastern Daylight Time)
    local_tz = pytz.timezone('America/New_York')

    daily_forecast = []
    current_day = None
    min_temp = None
    max_temp = None

    for forecast in forecast_data['list']:
        date_str = forecast['dt_txt']
        date_obj_utc = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        date_obj_local = date_obj_utc.replace(tzinfo=pytz.utc).astimezone(local_tz)
        weekday = date_obj_local.strftime('%a')

        day_temp = forecast['main']['temp']
        low_temp_forecast = forecast['main']['temp_min']

        # Check if we're still on the same day
        if current_day != weekday:
            # Save the last day's forecast before starting a new one
            if current_day is not None and len(daily_forecast) < 5:  # Limit to 5 days
                day_forecast = {
                    'weekday': current_day,
                    'temp': f"{int(convert_temp(max_temp, from_unit, unit))}",
                    'low_temp': f"{int(convert_temp(min_temp, from_unit, unit))}",
                    'description': description.capitalize(),
                    'icon': icon_url
                }
                daily_forecast.append(day_forecast)
                # print(f"Added forecast for {current_day}: max_temp={max_temp}, min_temp={min_temp}")

            # Reset for the new day
            current_day = weekday
            min_temp = low_temp_forecast
            max_temp = day_temp
        else:
            # Update the minimum and maximum temperatures for the current day
            min_temp = min(min_temp, low_temp_forecast)
            max_temp = max(max_temp, day_temp)

        description = forecast['weather'][0]['description']
        icon_code = forecast['weather'][0]['icon']
        icon_url = get_weather_icon(icon_code)

    # Add the last day's forecast
    if current_day is not None and len(daily_forecast) < 5:
        day_forecast = {
            'weekday': current_day,
            'temp': f"{int(convert_temp(max_temp, from_unit, unit))}",
            'low_temp': f"{int(convert_temp(min_temp, from_unit, unit))}",
            'description': description.capitalize(),
            'icon': icon_url
        }
        daily_forecast.append(day_forecast)

    current_icon_code = weather_data["weather"][0]["icon"]
    current_icon_url = get_weather_icon(current_icon_code)

    return render_template(
        "weather.html",
        title=weather_data["name"],
        status=current_description.capitalize(),
        temp=f"{int(temp)}",
        feels_like=f"{int(feels_like_temp)}",
        low_temp=f"{int(low_temp)}",
        humidity=humidity,
        wind_speed=f"{int(wind_speed_mph)}",
        precipitation=f"{int(precipitation)} mm",  # Pass precipitation in mm to the template
        latitude=f"{latitude:.2f}",
        longitude=f"{longitude:.2f}",
        daily_forecast=daily_forecast,
        unit=unit,
        city=city,
        current_icon=current_icon_url,
        video_file=video_file  # Pass the video file name to the template
    )

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8000)  

