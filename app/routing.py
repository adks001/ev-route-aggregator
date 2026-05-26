import requests
from app.config import ORS_API_KEY

def get_driving_route(start_coords, end_coords):
    """
    Fetches real-world driving coordinates from OpenRouteService.
    Returns: dict with 'polyline' (List of [lat, lon]), 'distance_km', and 'duration_mins'.
    """
    if not ORS_API_KEY:
        # No API Key: return None to fall back to linear interpolation
        return None

    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        'Accept': 'application/json, application/geo+json, charset=utf-8',
        'Authorization': ORS_API_KEY,
        'Content-Type': 'application/json; charset=utf-8'
    }
    
    # ORS requires longitude first: [lon, lat]
    body = {
        "coordinates": [
            [start_coords["longitude"], start_coords["latitude"]],
            [end_coords["longitude"], end_coords["latitude"]]
        ]
    }
    
    try:
        res = requests.post(url, json=body, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            features = data.get("features", [])
            if features:
                geometry = features[0].get("geometry", {})
                coordinates = geometry.get("coordinates", [])
                
                # Convert from ORS [lon, lat] to Leaflet standard [lat, lon]
                leaflet_coords = [[c[1], c[0]] for c in coordinates]
                
                properties = features[0].get("properties", {})
                summary = properties.get("summary", {})
                
                # ORS returns distance in meters, duration in seconds
                distance_km = summary.get("distance", 0.0) / 1000.0
                duration_mins = summary.get("duration", 0.0) / 60.0
                
                return {
                    "polyline": leaflet_coords,
                    "distance_km": distance_km,
                    "duration_mins": duration_mins
                }
    except Exception as e:
        print("OpenRouteService API Exception:", str(e))
        
    return None
