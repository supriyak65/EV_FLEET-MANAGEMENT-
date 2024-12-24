import csv
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

class RouteOptimizer:
    def __init__(self, csv_file="TG_ev_charging_stations.csv"):
        self.charging_stations = []
        self.geolocator = Nominatim(user_agent="ev_route_optimizer")
        if csv_file:
            self.upload_csv(csv_file)

    def upload_csv(self, file_path):
        """Load charging stations from a CSV file."""
        self.charging_stations = []
        try:
            with open(file_path, mode='r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    self.charging_stations.append({
                        "name": row["Name"],
                        "latitude": float(row["Latitude"]),
                        "longitude": float(row["Longitude"]),
                        "address": row["Address"],
                        "charger_type": row["Charger Type"]
                    })
            print(f"Loaded {len(self.charging_stations)} charging stations.")
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            raise

    def geocode_location(self, location_name):
        """Convert a city/area name into latitude and longitude."""
        try:
            location = self.geolocator.geocode(location_name)
            if location:
                return (location.latitude, location.longitude)
            else:
                raise ValueError(f"Could not geocode location: {location_name}")
        except Exception as e:
            print(f"Error during geocoding: {e}")
            raise

    def get_stations_in_range(self, start_location, range_km):
        """Get all stations within the range, sorted by distance."""
        stations_in_range = []
        for station in self.charging_stations:
            station_location = (station["latitude"], station["longitude"])
            distance = geodesic(start_location, station_location).km
            if distance <= range_km:
                station["distance"] = distance
                stations_in_range.append(station)
        return sorted(stations_in_range, key=lambda x: x["distance"])

    def optimize_route(self, start_name, destination_name, range_km):
        """Optimize route by showing stations in range and suggesting a route."""
        if not self.charging_stations:
            return {"error": "No charging station data available. Please upload the CSV file."}

        start_location = self.geocode_location(start_name)
        destination_location = self.geocode_location(destination_name)

        # Find stations in range
        stations_in_range = self.get_stations_in_range(start_location, range_km)

        # Generate Google Maps URL for the fastest route
        start_coords = f"{start_location[0]},{start_location[1]}"
        destination_coords = f"{destination_location[0]},{destination_location[1]}"
        maps_url = f"https://www.google.com/maps/dir/?api=1&origin={start_coords}&destination={destination_coords}"

        return {
            "stations_in_range": stations_in_range,
            "fastest_route_url": maps_url
        }
