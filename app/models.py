import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Session
from app.database import Base

class VehicleModel(Base):
    __tablename__ = "vehicle_models"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    battery_kwh = Column(Float, default=0.0)
    range_km = Column(Float, nullable=False)
    is_ice = Column(Boolean, default=False)

class Station(Base):
    __tablename__ = "stations"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    operator = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    distance_from_start = Column(Float, nullable=False) # km offset on NH44
    is_ice_only = Column(Boolean, default=False) # Fuel pumps vs EV chargers
    opening_hours = Column(String, default="Open 24 Hours")

    connectors = relationship("Connector", back_populates="station", cascade="all, delete-orphan")

class Connector(Base):
    __tablename__ = "connectors"

    id = Column(String, primary_key=True, index=True)
    station_id = Column(String, ForeignKey("stations.id"), nullable=False)
    type = Column(String, nullable=False) # CCS2, Type 2, Petrol/Diesel/CNG Nozzle
    power_kw = Column(Float, default=0.0)
    rate_inr = Column(Float, nullable=False) # rate per kWh or Liter

    station = relationship("Station", back_populates="connectors")

class ProximityBooking(Base):
    __tablename__ = "proximity_bookings"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    connector_id = Column(String, ForeignKey("connectors.id"), nullable=False)
    status = Column(String, default="LOCKED") # LOCKED, COMPLETED, EXPIRED
    security_pin = Column(String, nullable=False)
    lock_expires_at = Column(DateTime, nullable=False)

# Seed function to populate database on first boot
def seed_database(db: Session):
    # Clear tables to ensure database is updated with fresh ranges/models
    db.query(Connector).delete()
    db.query(Station).delete()
    db.query(VehicleModel).delete()
    db.commit()

    # 1. Seed Vehicle Models
    vehicles_data = [
        # Mercedes-Benz
        {"id": "mercedes_eqs_suv", "name": "Mercedes-Benz EQS SUV (~108-118 kWh, Up to 857 km)", "battery_kwh": 118.0, "range_km": 857.0, "is_ice": False},
        # BMW
        {"id": "bmw_i7", "name": "BMW i7 (101.7 kWh, Up to 625 km)", "battery_kwh": 101.7, "range_km": 625.0, "is_ice": False},
        {"id": "bmw_ix", "name": "BMW iX (76.6 kWh, 575 km)", "battery_kwh": 76.6, "range_km": 575.0, "is_ice": False},
        # Porsche
        {"id": "porsche_taycan", "name": "Porsche Taycan (Up to 105 kWh, Up to 705 km)", "battery_kwh": 105.0, "range_km": 705.0, "is_ice": False},
        {"id": "porsche_macan_ev", "name": "Porsche Macan EV (95 kWh, 624 km)", "battery_kwh": 95.0, "range_km": 624.0, "is_ice": False},
        # Mahindra
        {"id": "mahindra_be_6", "name": "Mahindra BE 6 (79 kWh, 683 km)", "battery_kwh": 79.0, "range_km": 683.0, "is_ice": False},
        {"id": "mahindra_xev_9e", "name": "Mahindra XEV 9e (~80 kWh, 656 km)", "battery_kwh": 80.0, "range_km": 656.0, "is_ice": False},
        {"id": "mahindra_xuv400", "name": "Mahindra XUV400 EV (39.4 kWh, 456 km)", "battery_kwh": 39.4, "range_km": 456.0, "is_ice": False},
        # Kia
        {"id": "kia_ev6", "name": "Kia EV6 (77.4 kWh, 663 km)", "battery_kwh": 77.4, "range_km": 663.0, "is_ice": False},
        # BYD
        {"id": "byd_seal", "name": "BYD Seal (82.5 kWh, 650 km)", "battery_kwh": 82.5, "range_km": 650.0, "is_ice": False},
        # Tata Motors
        {"id": "tata_harrier_ev", "name": "Tata Harrier EV (~60-80 kWh, 627 km)", "battery_kwh": 80.0, "range_km": 627.0, "is_ice": False},
        {"id": "tata_nexon_ev_lr", "name": "Tata Nexon EV Long Range (40.5 kWh, 465 km)", "battery_kwh": 40.5, "range_km": 465.0, "is_ice": False},
        # Lotus
        {"id": "lotus_eletre", "name": "Lotus Eletre (112 kWh, 600 km)", "battery_kwh": 112.0, "range_km": 600.0, "is_ice": False},
        # Volvo
        {"id": "volvo_ex40", "name": "Volvo EX40 (XC40) (79 kWh, 592 km)", "battery_kwh": 79.0, "range_km": 592.0, "is_ice": False},
        # Audi
        {"id": "audi_q8_etron", "name": "Audi Q8 e-tron (114 kWh, 582 km)", "battery_kwh": 114.0, "range_km": 582.0, "is_ice": False},
        # Hyundai
        {"id": "hyundai_ioniq_5", "name": "Hyundai IONIQ 5 (72.6 kWh, ~550 km)", "battery_kwh": 72.6, "range_km": 550.0, "is_ice": False},
        {"id": "hyundai_kona", "name": "Hyundai Kona Electric (39.2-65.4 kWh, 452-490 km)", "battery_kwh": 65.4, "range_km": 490.0, "is_ice": False},
        # Maruti Suzuki
        {"id": "maruti_evitara", "name": "Maruti Suzuki e Vitara (61 kWh, 543 km)", "battery_kwh": 61.0, "range_km": 543.0, "is_ice": False},
        # MG
        {"id": "mg_zs_ev", "name": "MG ZS EV (50.3 kWh, 461 km)", "battery_kwh": 50.3, "range_km": 461.0, "is_ice": False},
        {"id": "mg_windsor_ev", "name": "MG Windsor EV (38-50 kWh, 332-460 km)", "battery_kwh": 50.0, "range_km": 460.0, "is_ice": False},

        # Non-EV Combustion & Hybrid Cars
        {"id": "ice_petrol", "name": "Petrol Car", "battery_kwh": 50.0, "range_km": 15.0, "is_ice": True}, # battery_kwh represents tank size (L), range_km represents default mileage (km/L)
        {"id": "ice_diesel", "name": "Diesel Car", "battery_kwh": 55.0, "range_km": 18.0, "is_ice": True},
        {"id": "ice_cng", "name": "CNG Car", "battery_kwh": 10.0, "range_km": 25.0, "is_ice": True},
        {"id": "ice_petrol_hybrid", "name": "Petrol-Hybrid Car", "battery_kwh": 50.0, "range_km": 24.0, "is_ice": True},
        {"id": "ice_diesel_hybrid", "name": "Diesel-Hybrid Car", "battery_kwh": 55.0, "range_km": 26.0, "is_ice": True}
    ]

    for v in vehicles_data:
        db.add(VehicleModel(**v))

    # 2. Seed Stations (EV Chargers & Petrol/CNG Pumps)
    stations_data = [
        # EV Chargers
        {
            "id": "chickballapur_jio_bp",
            "name": "Jio-BP Pulse - Chickballapur",
            "operator": "Jio-BP Pulse",
            "latitude": 13.4350,
            "longitude": 77.7288,
            "distance_from_start": 60.0,
            "is_ice_only": False,
            "opening_hours": "Open 24 Hours",
            "connectors": [
                {"id": "con_chick_1", "type": "CCS2 DC Fast", "power_kw": 50.0, "rate_inr": 18.0},
                {"id": "con_chick_2", "type": "Type 2 AC", "power_kw": 7.4, "rate_inr": 12.0},
                {"id": "con_chick_3", "type": "Type 2 AC", "power_kw": 22.0, "rate_inr": 15.0}
            ]
        },
        {
            "id": "anantapur_zeon",
            "name": "Zeon Charging - Anantapur Highway",
            "operator": "Zeon Charging",
            "latitude": 14.6819,
            "longitude": 77.6006,
            "distance_from_start": 210.0,
            "is_ice_only": False,
            "opening_hours": "06:00 AM - 11:00 PM",
            "connectors": [
                {"id": "99ee4a2a-711e-4cb2-83b6-9bbffb12c140", "type": "CCS2 DC HyperFast", "power_kw": 120.0, "rate_inr": 22.0},
                {"id": "con_anant_ev2", "type": "CCS2 DC Fast", "power_kw": 60.0, "rate_inr": 19.0},
                {"id": "con_anant_ev3", "type": "Type 2 AC", "power_kw": 22.0, "rate_inr": 15.0}
            ]
        },
        {
            "id": "kurnool_jio_bp",
            "name": "Jio-BP Pulse - Kurnool Bypass",
            "operator": "Jio-BP Pulse",
            "latitude": 15.8281,
            "longitude": 78.0373,
            "distance_from_start": 360.0,
            "is_ice_only": False,
            "opening_hours": "Open 24 Hours",
            "connectors": [
                {"id": "con_kurnool_1", "type": "CCS2 DC Fast", "power_kw": 60.0, "rate_inr": 18.0},
                {"id": "con_kurnool_2", "type": "CCS2 DC Fast", "power_kw": 30.0, "rate_inr": 16.0},
                {"id": "con_kurnool_3", "type": "Type 2 AC", "power_kw": 7.4, "rate_inr": 12.0}
            ]
        },
        # Petrol / Diesel / CNG Fuel Stations
        {
            "id": "chickballapur_hpcl",
            "name": "HPCL Refueling Pump - Chickballapur",
            "operator": "HPCL",
            "latitude": 13.4350,
            "longitude": 77.7288,
            "distance_from_start": 60.0,
            "is_ice_only": True,
            "opening_hours": "Open 24 Hours",
            "connectors": [
                {"id": "con_chick_petrol", "type": "Petrol Nozzle", "power_kw": 0.0, "rate_inr": 104.5},
                {"id": "con_chick_diesel", "type": "Diesel Nozzle", "power_kw": 0.0, "rate_inr": 90.8},
                {"id": "con_chick_cng", "type": "CNG Nozzle", "power_kw": 0.0, "rate_inr": 85.0}
            ]
        },
        {
            "id": "anantapur_bpcl",
            "name": "BPCL Ghar Pump - Anantapur",
            "operator": "BPCL",
            "latitude": 14.6819,
            "longitude": 77.6006,
            "distance_from_start": 210.0,
            "is_ice_only": True,
            "opening_hours": "06:00 AM - 11:30 PM",
            "connectors": [
                {"id": "con_anant_petrol", "type": "Petrol Nozzle", "power_kw": 0.0, "rate_inr": 103.8},
                {"id": "con_anant_diesel", "type": "Diesel Nozzle", "power_kw": 0.0, "rate_inr": 89.9},
                {"id": "con_anant_cng", "type": "CNG Nozzle", "power_kw": 0.0, "rate_inr": 84.5}
            ]
        },
        {
            "id": "kurnool_iocl",
            "name": "IOCL Petrol Station - Kurnool Bypass",
            "operator": "IOCL",
            "latitude": 15.8281,
            "longitude": 78.0373,
            "distance_from_start": 360.0,
            "is_ice_only": True,
            "opening_hours": "Open 24 Hours",
            "connectors": [
                {"id": "con_kurnool_petrol", "type": "Petrol Nozzle", "power_kw": 0.0, "rate_inr": 105.2},
                {"id": "con_kurnool_diesel", "type": "Diesel Nozzle", "power_kw": 0.0, "rate_inr": 91.2},
                {"id": "con_kurnool_cng", "type": "CNG Nozzle", "power_kw": 0.0, "rate_inr": 86.0}
            ]
        }
    ]

    for s in stations_data:
        station_db = Station(
            id=s["id"],
            name=s["name"],
            operator=s["operator"],
            latitude=s["latitude"],
            longitude=s["longitude"],
            distance_from_start=s["distance_from_start"],
            is_ice_only=s["is_ice_only"],
            opening_hours=s["opening_hours"]
        )
        db.add(station_db)
        db.flush()
        
        for c in s["connectors"]:
            db.add(Connector(
                id=c["id"],
                station_id=station_db.id,
                type=c["type"],
                power_kw=c["power_kw"],
                rate_inr=c["rate_inr"]
            ))
    
    db.commit()
