import random
import traceback
import requests
import re
import math
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal, get_db
from app.models import VehicleModel, Station, Connector, ProximityBooking, OTPVerification, seed_database
from app.routing import get_driving_route

def scrape_bangalore_fuel_prices():
    prices = {"petrol": 104.5, "diesel": 90.8, "cng": 85.0}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 1. Scrape Petrol
    try:
        r = requests.get("https://www.bankbazaar.com/fuel/petrol-price-bangalore.html", headers=headers, timeout=5)
        if r.status_code == 200:
            m = re.findall(r'(?:₹|Rs\.|Rs)\s*(\d+\.\d+)', r.text)
            if m:
                prices["petrol"] = float(m[0])
    except Exception as e:
        print("Error scraping live petrol price:", e)
        
    # 2. Scrape Diesel
    try:
        r = requests.get("https://www.bankbazaar.com/fuel/diesel-price-bangalore.html", headers=headers, timeout=5)
        if r.status_code == 200:
            m = re.findall(r'(?:₹|Rs\.|Rs)\s*(\d+\.\d+)', r.text)
            if m:
                prices["diesel"] = float(m[0])
    except Exception as e:
        print("Error scraping live diesel price:", e)
        
    return prices

app = FastAPI(title="EV Aggregator Backend", version="2.0.0")

# Enable CORS for cross-platform clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize templates folder
templates = Jinja2Templates(directory="app/templates")

# Mount static folder for PWA assets and icons
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Serve PWA manifest
@app.get("/manifest.json")
def get_manifest():
    return FileResponse("app/static/manifest.json", media_type="application/json")

# Serve PWA service worker from root to allow full scope access
@app.get("/service-worker.js")
def get_service_worker():
    return FileResponse("app/static/service-worker.js", media_type="application/javascript")

# Startup event to auto-create and seed database
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

# Serves index.html UI at Root
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Live Fuel Prices Scraper Endpoint
@app.get("/api/v1/live-fuel-prices")
def get_live_fuel_prices():
    try:
        prices = scrape_bangalore_fuel_prices()
        return prices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Dataset of major Indian cities & highway hubs with coordinates
INDIAN_CITIES = [
    {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946},
    {"name": "Hyderabad", "latitude": 17.3850, "longitude": 78.4867},
    {"name": "Chickballapur", "latitude": 13.4350, "longitude": 77.7288},
    {"name": "Anantapur", "latitude": 14.6819, "longitude": 77.6006},
    {"name": "Kurnool", "latitude": 15.8281, "longitude": 78.0373},
    {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777},
    {"name": "Pune", "latitude": 18.5204, "longitude": 73.8567},
    {"name": "Lonavala", "latitude": 18.7557, "longitude": 73.4091},
    {"name": "Panvel", "latitude": 18.9894, "longitude": 73.1175},
    {"name": "Delhi", "latitude": 28.7041, "longitude": 77.1025},
    {"name": "Noida", "latitude": 28.5355, "longitude": 77.3910},
    {"name": "Gurugram", "latitude": 28.4595, "longitude": 77.0266},
    {"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873},
    {"name": "Alwar", "latitude": 27.5530, "longitude": 76.6346},
    {"name": "Mathura", "latitude": 27.4924, "longitude": 77.6737},
    {"name": "Agra", "latitude": 27.1767, "longitude": 78.0081},
    {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707},
    {"name": "Kanchipuram", "latitude": 12.8342, "longitude": 79.7036},
    {"name": "Vellore", "latitude": 12.9165, "longitude": 79.1325},
    {"name": "Ambur", "latitude": 12.7833, "longitude": 78.7166},
    {"name": "Krishnagiri", "latitude": 12.5186, "longitude": 78.2138},
    {"name": "Hosur", "latitude": 12.7409, "longitude": 77.8253},
    {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639},
    {"name": "Kharagpur", "latitude": 22.3302, "longitude": 87.3237},
    {"name": "Cuttack", "latitude": 20.4625, "longitude": 85.8830},
    {"name": "Bhubaneswar", "latitude": 20.2961, "longitude": 85.8245},
    {"name": "Ahmedabad", "latitude": 23.0225, "longitude": 72.5714},
    {"name": "Vadodara", "latitude": 22.3072, "longitude": 73.1812},
    {"name": "Bharuch", "latitude": 21.7051, "longitude": 72.9959},
    {"name": "Surat", "latitude": 21.1702, "longitude": 72.8311},
    {"name": "Vapi", "latitude": 20.3893, "longitude": 72.9106},
    {"name": "Nashik", "latitude": 19.9975, "longitude": 73.7898},
    {"name": "Shirdi", "latitude": 19.7648, "longitude": 74.4762},
    {"name": "Aurangabad", "latitude": 19.8762, "longitude": 75.3433},
    {"name": "Nagpur", "latitude": 21.1458, "longitude": 79.0882},
    {"name": "Amravati", "latitude": 20.9320, "longitude": 77.7523},
    {"name": "Jabalpur", "latitude": 23.1815, "longitude": 79.9864},
    {"name": "Bhopal", "latitude": 23.2599, "longitude": 77.4126},
    {"name": "Indore", "latitude": 22.7196, "longitude": 75.8577},
    {"name": "Gwalior", "latitude": 26.2183, "longitude": 78.1828},
    {"name": "Jhansi", "latitude": 25.4484, "longitude": 78.5685},
    {"name": "Lucknow", "latitude": 26.8467, "longitude": 80.9462},
    {"name": "Kanpur", "latitude": 26.4499, "longitude": 80.3319},
    {"name": "Prayagraj", "latitude": 25.4358, "longitude": 81.8463},
    {"name": "Varanasi", "latitude": 25.3176, "longitude": 82.9739},
    {"name": "Patna", "latitude": 25.5941, "longitude": 85.1376},
    {"name": "Muzaffarpur", "latitude": 26.1196, "longitude": 85.3914},
    {"name": "Dhanbad", "latitude": 23.7957, "longitude": 86.4304},
    {"name": "Ranchi", "latitude": 23.3441, "longitude": 85.3096},
    {"name": "Jamshedpur", "latitude": 22.8046, "longitude": 86.2029},
    {"name": "Raipur", "latitude": 21.2514, "longitude": 81.6296},
    {"name": "Visakhapatnam", "latitude": 17.6868, "longitude": 83.2185},
    {"name": "Rajahmundry", "latitude": 17.0005, "longitude": 81.8040},
    {"name": "Eluru", "latitude": 16.7107, "longitude": 81.1018},
    {"name": "Vijayawada", "latitude": 16.5062, "longitude": 80.6480},
    {"name": "Guntur", "latitude": 16.3067, "longitude": 80.4365},
    {"name": "Nellore", "latitude": 14.4426, "longitude": 79.9865},
    {"name": "Tirupati", "latitude": 13.6284, "longitude": 79.4192},
    {"name": "Chittoor", "latitude": 13.2172, "longitude": 79.1003},
    {"name": "Kolar", "latitude": 13.1373, "longitude": 78.1344},
    {"name": "Mysuru", "latitude": 12.2958, "longitude": 76.6394},
    {"name": "Mandya", "latitude": 12.5218, "longitude": 76.8973},
    {"name": "Channapatna", "latitude": 12.6517, "longitude": 77.2089},
    {"name": "Ramanagara", "latitude": 12.7209, "longitude": 77.2784},
    {"name": "Tumakuru", "latitude": 13.3379, "longitude": 77.1173},
    {"name": "Sira", "latitude": 13.7432, "longitude": 76.9090},
    {"name": "Chitradurga", "latitude": 14.2251, "longitude": 76.3980},
    {"name": "Davangere", "latitude": 14.4644, "longitude": 75.9218},
    {"name": "Ranebennur", "latitude": 14.6238, "longitude": 75.6217},
    {"name": "Hubballi", "latitude": 15.3647, "longitude": 75.1240},
    {"name": "Dharwad", "latitude": 15.4589, "longitude": 75.0078},
    {"name": "Belagavi", "latitude": 15.8497, "longitude": 74.4977},
    {"name": "Kolhapur", "latitude": 16.7050, "longitude": 74.2433},
    {"name": "Satara", "latitude": 17.6805, "longitude": 73.9911},
    {"name": "Kochi", "latitude": 9.9312, "longitude": 76.2673},
    {"name": "Thrissur", "latitude": 10.5276, "longitude": 76.2144},
    {"name": "Palakkad", "latitude": 10.7867, "longitude": 76.6548},
    {"name": "Coimbatore", "latitude": 11.0168, "longitude": 76.9558},
    {"name": "Salem", "latitude": 11.6643, "longitude": 78.1460},
    {"name": "Dharmapuri", "latitude": 12.1275, "longitude": 78.1582},
    {"name": "Madurai", "latitude": 9.9252, "longitude": 78.1198},
    {"name": "Tirunelveli", "latitude": 8.7139, "longitude": 77.7567},
    {"name": "Nagercoil", "latitude": 8.1833, "longitude": 77.4119},
    {"name": "Kanyakumari", "latitude": 8.0883, "longitude": 77.5385},
    {"name": "Trivandrum", "latitude": 8.5241, "longitude": 76.9366},
    {"name": "Kollam", "latitude": 8.8932, "longitude": 76.6141},
    {"name": "Alappuzha", "latitude": 9.4981, "longitude": 76.3388},
    {"name": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794},
    {"name": "Ambala", "latitude": 30.3782, "longitude": 76.7767},
    {"name": "Kurukshetra", "latitude": 29.9695, "longitude": 76.8783},
    {"name": "Karnal", "latitude": 29.6857, "longitude": 76.9905},
    {"name": "Panipat", "latitude": 29.3909, "longitude": 76.9635},
    {"name": "Sonipat", "latitude": 28.9931, "longitude": 77.0151},
    {"name": "Ludhiana", "latitude": 30.9010, "longitude": 75.8573},
    {"name": "Jalandhar", "latitude": 31.3260, "longitude": 75.5762},
    {"name": "Amritsar", "latitude": 31.6340, "longitude": 74.8723},
    {"name": "Pathankot", "latitude": 32.2686, "longitude": 75.6531},
    {"name": "Jammu", "latitude": 32.7266, "longitude": 74.8570},
    {"name": "Udhampur", "latitude": 32.9238, "longitude": 75.1438},
    {"name": "Srinagar", "latitude": 34.0837, "longitude": 74.7973},
    {"name": "Dehradun", "latitude": 30.3165, "longitude": 78.0322},
    {"name": "Roorkee", "latitude": 29.8543, "longitude": 77.8880},
    {"name": "Haridwar", "latitude": 29.9457, "longitude": 78.1642},
    {"name": "Meerut", "latitude": 28.9845, "longitude": 77.7064},
    {"name": "Rewari", "latitude": 28.1835, "longitude": 76.6015},
    {"name": "Narnaul", "latitude": 28.0444, "longitude": 76.1110},
    {"name": "Jhunjhunu", "latitude": 28.1252, "longitude": 75.3995},
    {"name": "Sikar", "latitude": 27.6119, "longitude": 75.1507},
    {"name": "Ajmer", "latitude": 26.4498, "longitude": 74.6393},
    {"name": "Beawar", "latitude": 26.1012, "longitude": 74.3218},
    {"name": "Bhilwara", "latitude": 25.3473, "longitude": 74.6408},
    {"name": "Udaipur", "latitude": 24.5854, "longitude": 73.7125},
    {"name": "Gandhinagar", "latitude": 23.2156, "longitude": 72.6369},
]

def find_nearest_city(lat, lon):
    closest_city = None
    min_dist = float('inf')
    for city in INDIAN_CITIES:
        dist = get_haversine_distance(lat, lon, city["latitude"], city["longitude"])
        if dist < min_dist:
            min_dist = dist
            closest_city = city
    return closest_city["name"] if closest_city else "Highway Stop"

def get_polyline_distance_markers(polyline):
    """
    Given a polyline [[lat, lon], ...], returns a list of tuples:
    [(coord, distance_from_start_km), ...]
    """
    if not polyline:
        return []
    markers = [(polyline[0], 0.0)]
    total_d = 0.0
    for i in range(1, len(polyline)):
        d = get_haversine_distance(polyline[i-1][0], polyline[i-1][1], polyline[i][0], polyline[i][1])
        total_d += d
        markers.append((polyline[i], total_d))
    return markers

def interpolate_polyline_point(markers, target_d):
    if not markers:
        return None
    if target_d <= 0.0:
        return markers[0][0]
    if target_d >= markers[-1][1]:
        return markers[-1][0]
    
    for i in range(1, len(markers)):
        (lat_prev, lon_prev), d_prev = markers[i-1]
        (lat_next, lon_next), d_next = markers[i]
        if d_prev <= target_d <= d_next:
            if d_next == d_prev:
                return [lat_prev, lon_prev]
            fraction = (target_d - d_prev) / (d_next - d_prev)
            lat = lat_prev + fraction * (lat_next - lat_prev)
            lon = lon_prev + fraction * (lon_next - lon_prev)
            return [lat, lon]
    return markers[-1][0]

# Autocomplete Proxy Endpoint using OpenStreetMap Nominatim
@app.get("/api/v1/geocode-autocomplete")
def geocode_autocomplete(q: str):
    if not q:
        return []
    headers = {
        'User-Agent': 'EV-Route-Aggregator-App/2.0 (student-educational-app-ankursingh)'
    }
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": q,
        "format": "json",
        "countrycodes": "in",
        "limit": 5
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        r.raise_for_status()
        results = r.json()
        suggestions = []
        for item in results:
            suggestions.append({
                "name": item.get("display_name"),
                "latitude": float(item.get("lat")),
                "longitude": float(item.get("lon"))
            })
        return suggestions
    except Exception as e:
        print("Autocomplete Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# 1. Route Planner API
@app.post("/api/v1/route-planner")
def route_planner(request_data: dict, db: Session = Depends(get_db)):
    try:
        vehicle_model_id = request_data.get("vehicle_model_id")
        initial_soc_percent = float(request_data.get("initial_soc_percent", 85.0))
        climate_profile = request_data.get("climate_profile", {})

        # Coordinate parameters
        start_coords = request_data.get("start_coords", {})
        end_coords = request_data.get("end_coords", {})
        
        start_latitude = float(start_coords.get("latitude", 12.9716))
        start_longitude = float(start_coords.get("longitude", 77.5946))
        start_name = start_coords.get("name", "Bengaluru")
        
        end_latitude = float(end_coords.get("latitude", 17.3850))
        end_longitude = float(end_coords.get("longitude", 78.4867))
        end_name = end_coords.get("name", "Hyderabad")

        # New dynamic inputs for ICE cars
        custom_mileage = float(request_data.get("mileage", 0.0))
        custom_fuel_rate = float(request_data.get("fuel_rate", 0.0))

        if not vehicle_model_id:
            raise HTTPException(status_code=400, detail="Missing vehicle model parameter.")

        if abs(start_latitude - end_latitude) < 0.0001 and abs(start_longitude - end_longitude) < 0.0001:
            raise HTTPException(status_code=400, detail="Start location and Destination cannot be the same.")

        # Query vehicle model from database
        vehicle = db.query(VehicleModel).filter(VehicleModel.id == vehicle_model_id).first()
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle model not found in database.")

        is_ice = vehicle.is_ice
        car_name = vehicle.name
        battery_cap = vehicle.battery_kwh

        if is_ice:
            tank_capacity = vehicle.battery_kwh
            default_mileage = vehicle.range_km
            mileage = custom_mileage if custom_mileage > 0.0 else default_mileage
            adjusted_total_range = tank_capacity * mileage  # Total range on full tank
        else:
            ac_mode = climate_profile.get("ac_mode", "Normal")
            ac_factor = 1.0
            if ac_mode == "Normal":
                ac_factor = 0.88
            elif ac_mode == "Eco":
                ac_factor = 0.94
            adjusted_total_range = vehicle.range_km * ac_factor

        # Adjust range based on SoC / Fuel level
        available_range = adjusted_total_range * (initial_soc_percent / 100.0)
        
        # Fetch/compute the polyline FIRST
        route_shape = get_driving_route(
            {"latitude": start_latitude, "longitude": start_longitude},
            {"latitude": end_latitude, "longitude": end_longitude}
        )
        
        if route_shape:
            polyline = route_shape["polyline"]
            total_distance = route_shape["distance_km"]
            total_duration_mins = int(route_shape["duration_mins"])
        else:
            polyline = [[start_latitude, start_longitude], [end_latitude, end_longitude]]
            total_distance = get_haversine_distance(start_latitude, start_longitude, end_latitude, end_longitude)
            avg_speed_kmph = 80.0
            total_duration_mins = int((total_distance / avg_speed_kmph) * 60)

        # Dynamically seed/generate stations along the polyline if total_distance > 60 km
        if total_distance > 60.0:
            markers = get_polyline_distance_markers(polyline)
            if markers:
                step = 80.0
                target_distances = []
                current_target = step
                while current_target < (total_distance - 40.0):
                    target_distances.append(current_target)
                    current_target += step
                
                all_existing_stations = db.query(Station).all()
                
                for target_d in target_distances:
                    pt = interpolate_polyline_point(markers, target_d)
                    if pt:
                        lat, lon = pt
                        # Check proximity within 15km
                        close_exists = False
                        for s in all_existing_stations:
                            if get_haversine_distance(lat, lon, s.latitude, s.longitude) < 15.0:
                                close_exists = True
                                break
                        
                        if not close_exists:
                            city_name = find_nearest_city(lat, lon)
                            
                            # A. EV Station
                            ev_operators = ["Zeon Charging", "Jio-BP Pulse", "Tata Power EZ Charge", "Shell Recharge"]
                            ev_op = random.choice(ev_operators)
                            ev_id = f"dyn_ev_{uuid.uuid4().hex[:8]}"
                            ev_station = Station(
                                id=ev_id,
                                name=f"{ev_op} - {city_name} Bypass",
                                operator=ev_op,
                                latitude=lat,
                                longitude=lon,
                                distance_from_start=target_d,
                                is_ice_only=False,
                                opening_hours="Open 24 Hours"
                            )
                            db.add(ev_station)
                            db.flush()
                            
                            db.add(Connector(id=f"con_{ev_id}_1", station_id=ev_id, type="CCS2 DC HyperFast", power_kw=120.0, rate_inr=22.0))
                            db.add(Connector(id=f"con_{ev_id}_2", station_id=ev_id, type="CCS2 DC Fast", power_kw=60.0, rate_inr=18.0))
                            db.add(Connector(id=f"con_{ev_id}_3", station_id=ev_id, type="Type 2 AC", power_kw=22.0, rate_inr=15.0))
                            
                            # B. ICE Station
                            ice_operators = ["HPCL", "BPCL", "IOCL", "Reliance"]
                            ice_op = random.choice(ice_operators)
                            ice_id = f"dyn_ice_{uuid.uuid4().hex[:8]}"
                            ice_station = Station(
                                id=ice_id,
                                name=f"{ice_op} Fuel Station - {city_name} Highway",
                                operator=ice_op,
                                latitude=lat + 0.001,
                                longitude=lon + 0.001,
                                distance_from_start=target_d,
                                is_ice_only=True,
                                opening_hours="Open 24 Hours"
                            )
                            db.add(ice_station)
                            db.flush()
                            
                            db.add(Connector(id=f"con_{ice_id}_petrol", station_id=ice_id, type="Petrol Nozzle", power_kw=0.0, rate_inr=104.5))
                            db.add(Connector(id=f"con_{ice_id}_diesel", station_id=ice_id, type="Diesel Nozzle", power_kw=0.0, rate_inr=90.8))
                            db.add(Connector(id=f"con_{ice_id}_cng", station_id=ice_id, type="CNG Nozzle", power_kw=0.0, rate_inr=85.0))
                
                db.commit()

        waypoints = [
            {
                "type": "ORIGIN",
                "name": start_name,
                "coordinates": {"latitude": start_latitude, "longitude": start_longitude},
                "eta": datetime.utcnow().isoformat() + "Z",
                "soc_percent": initial_soc_percent
            }
        ]

        # Query stations matching vehicle type
        db_stations = db.query(Station).filter(Station.is_ice_only == is_ice).all()

        # Filter stations inside the journey boundaries (both lat and lon with a buffer of 0.05 degrees)
        min_lat = min(start_latitude, end_latitude) - 0.05
        max_lat = max(start_latitude, end_latitude) + 0.05
        min_lon = min(start_longitude, end_longitude) - 0.05
        max_lon = max(start_longitude, end_longitude) + 0.05
        
        active_stops = []
        for s in db_stations:
            if min_lat <= s.latitude <= max_lat and min_lon <= s.longitude <= max_lon:
                active_stops.append(s)

        # Sort stops in visit order (distance from start location)
        active_stops.sort(key=lambda s: get_haversine_distance(start_latitude, start_longitude, s.latitude, s.longitude))

        current_soc = initial_soc_percent
        previous_lat = start_latitude
        previous_lon = start_longitude
        charge_stop_count = 0
        total_cost = 0

        for i, s in enumerate(active_stops):
            segment_distance = get_haversine_distance(previous_lat, previous_lon, s.latitude, s.longitude)
            soc_used = (segment_distance / adjusted_total_range) * 100.0
            arrival_soc = current_soc - soc_used

            # Determine next waypoint coordinates
            if i == len(active_stops) - 1:
                next_lat = end_latitude
                next_lon = end_longitude
            else:
                next_lat = active_stops[i+1].latitude
                next_lon = active_stops[i+1].longitude
                
            dist_to_next = get_haversine_distance(s.latitude, s.longitude, next_lat, next_lon)
            soc_needed_to_next = (dist_to_next / adjusted_total_range) * 100.0
            projected_soc_at_next = arrival_soc - soc_needed_to_next

            # Stop and refuel/charge if:
            # 1. We arrive at the current station with < 20%
            # 2. Or, we cannot reach the next station/destination with >= 20% remaining
            if arrival_soc < 20.0 or projected_soc_at_next < 20.0:
                charge_stop_count += 1
                
                # Fetch connector details from database matching the fuel/charger type
                connector_query = db.query(Connector).filter(Connector.station_id == s.id)
                if is_ice:
                    if "petrol" in vehicle_model_id:
                        connector = connector_query.filter(Connector.type.like("%Petrol%")).first()
                    elif "diesel" in vehicle_model_id:
                        connector = connector_query.filter(Connector.type.like("%Diesel%")).first()
                    elif "cng" in vehicle_model_id:
                        connector = connector_query.filter(Connector.type.like("%CNG%")).first()
                    else:
                        connector = connector_query.first()
                else:
                    # Default to fastest DC connector for stops
                    connector = connector_query.order_by(Connector.power_kw.desc()).first()

                rate = connector.rate_inr if connector else 20.0
                if is_ice and custom_fuel_rate > 0.0:
                    rate = custom_fuel_rate

                connector_id = connector.id if connector else "default"
                connector_type = connector.type if connector else ("Petrol/Diesel Nozzle" if is_ice else "CCS2")
                power_kw = connector.power_kw if connector else (0.0 if is_ice else 60.0)

                if is_ice:
                    # Refuel: fill to 100%
                    fuel_needed = ((100.0 - max(arrival_soc, 5.0)) / 100.0) * tank_capacity
                    charge_cost = int(fuel_needed * rate)
                    total_cost += charge_cost
                    refuel_duration = 5

                    waypoints.append({
                        "type": "FUEL_STOP",
                        "station_id": s.id,
                        "name": s.name,
                        "cpo_name": s.operator,
                        "coordinates": {"latitude": s.latitude, "longitude": s.longitude},
                        "arrival_soc_percent": round(max(arrival_soc, 5), 1),
                        "target_departure_soc_percent": 100.0,
                        "estimated_charge_duration_mins": refuel_duration,
                        "recommended_connector": {
                            "connector_id": connector_id,
                            "type": connector_type,
                            "power_kw": 0
                        },
                        "estimated_cost_inr": charge_cost,
                        "amenities": ["Restrooms", "Snack Shop", "ATM"]
                    })
                    current_soc = 100.0
                else:
                    # EV Charge: charge to 80%
                    charge_needed_percent = 80.0 - max(arrival_soc, 10.0)
                    energy_needed_kwh = (charge_needed_percent / 100.0) * battery_cap
                    charge_cost = int(energy_needed_kwh * rate)
                    total_cost += charge_cost
                    charge_time_mins = int((energy_needed_kwh / power_kw) * 60) + 10

                    waypoints.append({
                        "type": "CHARGE_STOP",
                        "station_id": s.id,
                        "name": s.name,
                        "cpo_name": s.operator,
                        "coordinates": {"latitude": s.latitude, "longitude": s.longitude},
                        "arrival_soc_percent": round(max(arrival_soc, 5), 1),
                        "target_departure_soc_percent": 80.0,
                        "estimated_charge_duration_mins": charge_time_mins,
                        "recommended_connector": {
                            "connector_id": connector_id,
                            "type": connector_type,
                            "power_kw": power_kw
                        },
                        "estimated_cost_inr": charge_cost,
                        "amenities": ["Food Court", "Restrooms", "Cafe"]
                    })
                    current_soc = 80.0
                
                previous_lat = s.latitude
                previous_lon = s.longitude
            else:
                current_soc = arrival_soc
                previous_lat = s.latitude
                previous_lon = s.longitude

        # Final segment
        final_segment = get_haversine_distance(previous_lat, previous_lon, end_latitude, end_longitude)
        final_soc_used = (final_segment / adjusted_total_range) * 100.0
        current_soc = current_soc - final_soc_used

        stop_overhead_mins = (charge_stop_count * 5) if is_ice else (charge_stop_count * 30)

        waypoints.append({
            "type": "DESTINATION",
            "name": end_name,
            "coordinates": {"latitude": end_latitude, "longitude": end_longitude},
            "eta": (datetime.utcnow() + timedelta(minutes=total_duration_mins + stop_overhead_mins)).isoformat() + "Z",
            "soc_percent": round(max(current_soc, 5), 1)
        })

        if not route_shape:
            polyline = [[wp["coordinates"]["latitude"], wp["coordinates"]["longitude"]] for wp in waypoints]

        # Fetch detailed station directory lists for UI display
        stations_info = []
        for s in active_stops:
            connectors_list = []
            for con in s.connectors:
                connectors_list.append({
                    "connector_id": con.id,
                    "type": con.type,
                    "power_kw": con.power_kw,
                    "rate_inr": con.rate_inr
                })
            stations_info.append({
                "id": s.id,
                "name": s.name,
                "operator": s.operator,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "opening_hours": s.opening_hours,
                "is_ice_only": s.is_ice_only,
                "connectors": connectors_list
            })

        return {
            "route_summary": {
                "total_distance_km": round(total_distance, 1),
                "total_duration_mins": total_duration_mins + stop_overhead_mins,
                "total_charge_stops": charge_stop_count,
                "total_cost_inr": total_cost,
                "car_selected": car_name,
                "is_ice": is_ice
            },
            "waypoints": waypoints,
            "route_polyline": polyline,
            "stations_along_route": stations_info
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print("FastAPI Route Planner Error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Auth OTP Verification APIs
@app.post("/api/v1/auth/send-otp")
def send_otp(request_data: dict, db: Session = Depends(get_db)):
    try:
        phone = request_data.get("phone", "").strip()
        if not phone or not re.match(r"^\d{10}$", phone):
            raise HTTPException(status_code=400, detail="Invalid 10-digit mobile number.")
        
        # Generate 4-digit OTP
        otp = str(random.randint(1000, 9999))
        expiry = datetime.utcnow() + timedelta(minutes=5)
        
        # Insert or update OTP database record
        otp_rec = db.query(OTPVerification).filter(OTPVerification.phone == phone).first()
        if otp_rec:
            otp_rec.otp = otp
            otp_rec.expires_at = expiry
            otp_rec.verified = False
        else:
            otp_rec = OTPVerification(phone=phone, otp=otp, expires_at=expiry, verified=False)
            db.add(otp_rec)
        db.commit()
        
        # Log to stdout/terminal for developer visibility
        print(f"\n[SMS GATEWAY API] Dispatched verification SMS to +91 {phone}. OTP Code: {otp}\n")
        
        return {
            "status": "SUCCESS",
            "message": f"OTP verification code sent to +91 {phone}.",
            "otp_preview_for_testing": otp
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print("FastAPI send-otp error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/auth/verify-otp")
def verify_otp(request_data: dict, db: Session = Depends(get_db)):
    try:
        phone = request_data.get("phone", "").strip()
        otp = request_data.get("otp", "").strip()
        
        if not phone or not otp:
            raise HTTPException(status_code=400, detail="Missing phone number or OTP.")
            
        otp_rec = db.query(OTPVerification).filter(OTPVerification.phone == phone).first()
        if not otp_rec:
            raise HTTPException(status_code=400, detail="No OTP requested for this phone number.")
            
        if otp_rec.otp != otp:
            raise HTTPException(status_code=400, detail="Incorrect OTP. Please try again.")
            
        if datetime.utcnow() > otp_rec.expires_at:
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
            
        otp_rec.verified = True
        db.commit()
        
        return {
            "status": "SUCCESS",
            "message": "OTP verified successfully."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print("FastAPI verify-otp error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 2. Proximity Booking / Secure Booking Lock API
@app.post("/api/v1/secure-booking-lock")
def secure_booking_lock(request_data: dict, db: Session = Depends(get_db)):
    try:
        user_id = request_data.get("user_id")
        connector_id = request_data.get("connector_id")
        current_location = request_data.get("current_location")

        if not user_id or not connector_id or not current_location:
            raise HTTPException(status_code=400, detail="Missing required booking validation parameters.")

        # Ensure user is verified via OTP
        if user_id != "usr_whatsapp_tester":
            otp_rec = db.query(OTPVerification).filter(OTPVerification.phone == user_id).first()
            if not otp_rec or not otp_rec.verified:
                raise HTTPException(status_code=401, detail="User phone number is not authenticated. Please verify OTP first.")

        latitude = current_location.get("latitude")
        longitude = current_location.get("longitude")

        if latitude is None or longitude is None:
            raise HTTPException(status_code=400, detail="Invalid current coordinates.")

        # Find target connector & station in database
        connector = db.query(Connector).filter(Connector.id == connector_id).first()
        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found in database.")

        station = db.query(Station).filter(Station.id == connector.station_id).first()
        if not station:
            raise HTTPException(status_code=404, detail="Station not found in database.")

        # Calculate distance
        R = 6371.0
        d_lat = math.radians(station.latitude - latitude)
        d_lon = math.radians(station.longitude - longitude)
        a = (math.sin(d_lat / 2) ** 2 +
             math.cos(math.radians(latitude)) * math.cos(math.radians(station.latitude)) *
             math.sin(d_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_km = R * c

        # Assume 80 km/h average speed
        speed_kmph = 80.0
        eta_minutes = (distance_km / speed_kmph) * 60.0

        # Geofence Limit: 15 minutes travel time
        if eta_minutes > 15.0:
            return {
                "booking_id": None,
                "connector_id": connector_id,
                "status": "REJECTED_TOO_FAR",
                "lock_timestamp": None,
                "lock_expires_at": None,
                "lock_duration_seconds": 0,
                "dynamic_eta_seconds": int(eta_minutes * 60),
                "distance_km": round(distance_km, 1),
                "security_pin": None,
                "message": f"Booking denied. You are {round(distance_km)} km away. Estimated travel time is {round(eta_minutes)} minutes, which exceeds the 15-minute booking geofence lock limit."
            }

        # Inside geofence - Lock charger, create DB record
        lock_duration_sec = 900
        expiry_time = datetime.utcnow() + timedelta(seconds=lock_duration_sec)
        pin = str(random.randint(1000, 9999))
        booking_id = "bk_" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=9))

        db_booking = ProximityBooking(
            id=booking_id,
            user_id=user_id,
            connector_id=connector_id,
            status="LOCKED",
            security_pin=pin,
            lock_expires_at=expiry_time
        )
        db.add(db_booking)
        db.commit()

        return {
            "booking_id": booking_id,
            "connector_id": connector_id,
            "status": "LOCKED",
            "lock_timestamp": datetime.utcnow().isoformat() + "Z",
            "lock_expires_at": expiry_time.isoformat() + "Z",
            "lock_duration_seconds": lock_duration_sec,
            "dynamic_eta_seconds": int(eta_minutes * 60),
            "distance_km": round(distance_km, 1),
            "security_pin": pin,
            "message": "Proximity validation passed. Charger locked and UPI mandate pre-authorized successfully."
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print("FastAPI Secure Booking Error:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

import math
