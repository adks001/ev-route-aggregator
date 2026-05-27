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

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    phone = Column(String, primary_key=True, index=True)
    otp = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)

# Seed function to populate database on first boot
def seed_database(db: Session):
    # Clear tables to ensure database is updated with fresh ranges/models
    db.query(Connector).delete()
    db.query(Station).delete()
    db.query(VehicleModel).delete()
    db.query(OTPVerification).delete()
    db.commit()

    # Seed dummy verified record for developer/compatibility
    from datetime import datetime, timedelta
    dummy_auth = OTPVerification(
        phone="usr_whatsapp_tester",
        otp="9999",
        expires_at=datetime.utcnow() + timedelta(days=365),
        verified=True
    )
    db.add(dummy_auth)
    db.commit()

    # 1. Seed Vehicle Models
    vehicles_data = [
        # Premium Long-Range EVs
        {"id": "mercedes_eqs_sedan", "name": "Mercedes-Benz EQS Sedan", "battery_kwh": 107.8, "range_km": 857.0, "is_ice": False},
        {"id": "lucid_air", "name": "Lucid Air", "battery_kwh": 112.0, "range_km": 800.0, "is_ice": False},
        {"id": "mahindra_be_6", "name": "Mahindra BE 6", "battery_kwh": 79.0, "range_km": 683.0, "is_ice": False},
        {"id": "kia_ev6_gt_line", "name": "Kia EV6 GT Line", "battery_kwh": 84.0, "range_km": 708.0, "is_ice": False},
        {"id": "tesla_model3_lr", "name": "Tesla Model 3 Long Range", "battery_kwh": 82.0, "range_km": 750.0, "is_ice": False},
        {"id": "bmw_i7", "name": "BMW i7", "battery_kwh": 101.7, "range_km": 625.0, "is_ice": False},
        {"id": "byd_seal_extended", "name": "BYD Seal (Extended)", "battery_kwh": 82.56, "range_km": 650.0, "is_ice": False},
        {"id": "porsche_taycan_turbos", "name": "Porsche Taycan (Turbo S)", "battery_kwh": 93.0, "range_km": 678.0, "is_ice": False},
        {"id": "mercedes_eqs_suv", "name": "Mercedes-Benz EQS SUV", "battery_kwh": 122.0, "range_km": 820.0, "is_ice": False},
        {"id": "cadillac_escalade_iq", "name": "Cadillac Escalade IQ", "battery_kwh": 205.0, "range_km": 748.0, "is_ice": False},
        
        # Mid-Range & Popular SUV/Crossovers
        {"id": "hyundai_ioniq", "name": "Hyundai Ioniq 5/6", "battery_kwh": 84.0, "range_km": 630.0, "is_ice": False},
        {"id": "kia_ev9", "name": "Kia EV9", "battery_kwh": 99.8, "range_km": 560.0, "is_ice": False},
        {"id": "tesla_modely_juniper", "name": "Tesla Model Y Juniper", "battery_kwh": 78.0, "range_km": 525.0, "is_ice": False},
        {"id": "volvo_ex40", "name": "Volvo EX40", "battery_kwh": 78.0, "range_km": 590.0, "is_ice": False},
        {"id": "mahindra_xev_9e", "name": "Mahindra XEV 9e", "battery_kwh": 79.0, "range_km": 650.0, "is_ice": False},
        {"id": "byd_atto_3", "name": "BYD Atto 3", "battery_kwh": 60.5, "range_km": 520.0, "is_ice": False},
        {"id": "mg_zs_ev", "name": "MG ZS EV", "battery_kwh": 68.0, "range_km": 460.0, "is_ice": False},
        {"id": "bmw_ix", "name": "BMW iX1/iX3", "battery_kwh": 64.7, "range_km": 500.0, "is_ice": False},
        {"id": "tata_harrier_ev", "name": "Tata Harrier EV", "battery_kwh": 75.0, "range_km": 627.0, "is_ice": False},
        {"id": "audi_q8_etron", "name": "Audi Q8 e-tron", "battery_kwh": 114.0, "range_km": 580.0, "is_ice": False},

        # Affordable & Compact EVs
        {"id": "tata_punch_ev", "name": "Tata Punch EV", "battery_kwh": 40.0, "range_km": 350.0, "is_ice": False},
        {"id": "mg_windsor_ev", "name": "MG Windsor EV", "battery_kwh": 52.9, "range_km": 450.0, "is_ice": False},
        {"id": "maruti_evitara", "name": "Maruti Suzuki e Vitara", "battery_kwh": 61.0, "range_km": 540.0, "is_ice": False},
        {"id": "hyundai_kona", "name": "Hyundai Inster/Kona", "battery_kwh": 65.0, "range_km": 490.0, "is_ice": False},
        {"id": "tata_tiago_ev", "name": "Tata Tiago EV", "battery_kwh": 24.0, "range_km": 315.0, "is_ice": False},
        {"id": "citroen_ec3", "name": "Citroën E-C3", "battery_kwh": 44.0, "range_km": 320.0, "is_ice": False},
        {"id": "mg_comet_ev", "name": "MG Comet EV", "battery_kwh": 17.3, "range_km": 230.0, "is_ice": False},
        {"id": "kia_ev3", "name": "Kia EV3", "battery_kwh": 81.0, "range_km": 600.0, "is_ice": False},
        {"id": "vinfast_vf6", "name": "VinFast VF6/VF7", "battery_kwh": 59.0, "range_km": 460.0, "is_ice": False},
        {"id": "mini_countryman_electric", "name": "Mini Countryman Electric", "battery_kwh": 66.0, "range_km": 460.0, "is_ice": False},

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
