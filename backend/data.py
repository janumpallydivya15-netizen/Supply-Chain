"""
Mock data store containing deterministic benchmark records for Phase 1 and Phase 2.
Includes shipments, inventory, disruptions, alternative suppliers, and alternate logistics routes.
All mock data is deterministic, clearly labeled as illustrative, and consistent across records.
"""

SHIPMENTS = [
    {
        "id": "SH-101",
        "supplier": "Apex Electronics Ltd.",
        "product": "Enterprise Laptop Ultra 15",
        "sku": "SKU-LAP-1001",
        "quantity": 50,
        "destination": "Hyderabad Distribution Center",
        "expected_arrival": "2026-10-29",
        "status": "Delayed",
        "risk_level": "Critical",
        "delay_days": 3,
        "origin": "Shenzhen, CN",
        "notes": "Customs clearance delay at port of entry. Directly impacts Hyderabad inventory."
    },
    {
        "id": "SH-102",
        "supplier": "Pacific Silicon Co.",
        "product": "Power Management IC",
        "sku": "SKU-SEMI-2045",
        "quantity": 4000,
        "destination": "Bengaluru Assembly Plant",
        "expected_arrival": "2026-10-27",
        "status": "In Transit",
        "risk_level": "Low",
        "delay_days": 0,
        "origin": "Hsinchu, TW",
        "notes": "Air cargo cleared; on schedule for standard arrival."
    },
    {
        "id": "SH-103",
        "supplier": "EuroLogistics Maritime",
        "product": "Industrial Lithium Batteries",
        "sku": "SKU-BAT-4420",
        "quantity": 600,
        "destination": "Chennai Central Hub",
        "expected_arrival": "2026-11-04",
        "status": "Rerouted",
        "risk_level": "High",
        "delay_days": 4,
        "origin": "Rotterdam, NL",
        "notes": "Vessel rerouted via Cape of Good Hope due to severe weather in Arabian Sea."
    },
    {
        "id": "SH-104",
        "supplier": "Deccan Precision Castings",
        "product": "Anodized Aluminum Chassis",
        "sku": "SKU-CHS-3310",
        "quantity": 1200,
        "destination": "Pune Manufacturing Facility",
        "expected_arrival": "2026-10-26",
        "status": "Delivered",
        "risk_level": "Low",
        "delay_days": 0,
        "origin": "Coimbatore, IN",
        "notes": "Delivered on schedule and accepted into incoming quality control."
    },
    {
        "id": "SH-105",
        "supplier": "Nordic Display Tech",
        "product": "OLED 14-inch Display Panels",
        "sku": "SKU-DSP-8890",
        "quantity": 850,
        "destination": "Bengaluru Assembly Plant",
        "expected_arrival": "2026-10-31",
        "status": "Delayed",
        "risk_level": "Medium",
        "delay_days": 2,
        "origin": "Seoul, KR",
        "notes": "Sub-tier assembly equipment breakdown reported at factory."
    },
    {
        "id": "SH-106",
        "supplier": "Trans-Bharat Freight",
        "product": "Thermal Cooling Modules",
        "sku": "SKU-THM-1120",
        "quantity": 2500,
        "destination": "Hyderabad Distribution Center",
        "expected_arrival": "2026-10-28",
        "status": "In Transit",
        "risk_level": "Low",
        "delay_days": 0,
        "origin": "Ahmedabad, IN",
        "notes": "Interstate highway transit on track."
    }
]

INVENTORY = [
    {
        "product_name": "Enterprise Laptop Ultra 15",
        "sku": "SKU-LAP-1001",
        "location": "Hyderabad Distribution Center",
        "available_stock": 14,
        "reorder_threshold": 60,
        "target_stock": 80,
        "daily_burn_rate": 8,
        "unit_cost_usd": 850,
        "stock_status": "Critical",
        "percentage": 23,
        "unit": "units",
        "notes": "Buffer critically depleted; waiting on delayed shipment SH-101 (50 units)."
    },
    {
        "product_name": "Power Management IC",
        "sku": "SKU-SEMI-2045",
        "location": "Bengaluru Assembly Plant",
        "available_stock": 6800,
        "reorder_threshold": 3000,
        "target_stock": 6000,
        "daily_burn_rate": 200,
        "unit_cost_usd": 4.5,
        "stock_status": "Healthy",
        "percentage": 100,
        "unit": "units",
        "notes": "Adequate inventory for 4 weeks of continuous production."
    },
    {
        "product_name": "Industrial Lithium Batteries",
        "sku": "SKU-BAT-4420",
        "location": "Chennai Central Hub",
        "available_stock": 210,
        "reorder_threshold": 500,
        "target_stock": 700,
        "daily_burn_rate": 45,
        "unit_cost_usd": 120,
        "stock_status": "Low Stock",
        "percentage": 42,
        "unit": "units",
        "notes": "Safety threshold breached; maritime shipment SH-103 rerouted (+4 days)."
    },
    {
        "product_name": "Anodized Aluminum Chassis",
        "sku": "SKU-CHS-3310",
        "location": "Pune Manufacturing Facility",
        "available_stock": 1450,
        "reorder_threshold": 800,
        "target_stock": 1500,
        "daily_burn_rate": 60,
        "unit_cost_usd": 45,
        "stock_status": "Healthy",
        "percentage": 100,
        "unit": "units",
        "notes": "Replenished today by shipment SH-104."
    },
    {
        "product_name": "OLED 14-inch Display Panels",
        "sku": "SKU-DSP-8890",
        "location": "Bengaluru Assembly Plant",
        "available_stock": 320,
        "reorder_threshold": 700,
        "target_stock": 1000,
        "daily_burn_rate": 70,
        "unit_cost_usd": 95,
        "stock_status": "Low Stock",
        "percentage": 45,
        "unit": "units",
        "notes": "Stock running thin; supplier Apex/Nordic delay creates assembly risk."
    },
    {
        "product_name": "Thermal Cooling Modules",
        "sku": "SKU-THM-1120",
        "location": "Hyderabad Distribution Center",
        "available_stock": 3100,
        "reorder_threshold": 1500,
        "target_stock": 3000,
        "daily_burn_rate": 100,
        "unit_cost_usd": 18,
        "stock_status": "Healthy",
        "percentage": 100,
        "unit": "units",
        "notes": "Healthy stock level supported by domestic supply lines."
    }
]

DISRUPTIONS = [
    {
        "id": "DIS-2026-001",
        "title": "Supplier Transit Delay: Enterprise Laptops",
        "type": "Supplier Delay",
        "severity": "Critical",
        "affected_item": "Enterprise Laptop Ultra 15 (SKU-LAP-1001)",
        "affected_shipment": "SH-101",
        "facility": "Hyderabad Distribution Center",
        "reported_date": "2026-10-25 14:30",
        "description": "Apex Electronics shipment SH-101 carrying 50 Enterprise Laptops is delayed by 3 days due to export documentation backlog at Shenzhen port. Hyderabad DC inventory is at 14 units (reorder threshold: 60). Customer fulfillments at immediate risk.",
        "impact_summary": "Expected stockout in 36 hours without expedited intervention. Estimated enterprise customer revenue at risk: $65,000.",
        "future_agent_task": "Multi-agent engine will evaluate emergency air-freight quotes from Apex vs. local transfer from Bengaluru facility."
    },
    {
        "id": "DIS-2026-002",
        "title": "Severe Inventory Deficit: Industrial Lithium Batteries",
        "type": "Inventory Shortage",
        "severity": "High",
        "affected_item": "Industrial Lithium Batteries (SKU-BAT-4420)",
        "affected_shipment": "SH-103",
        "facility": "Chennai Central Hub",
        "reported_date": "2026-10-25 18:15",
        "description": "Chennai Hub stock has fallen to 210 units (critical threshold: 500). Primary replenishment vessel SH-103 rerouted around Cape of Good Hope, extending arrival by 4 days.",
        "impact_summary": "Assembly line slowdown projected within 5 days if battery stock dips below 100 units.",
        "future_agent_task": "Inventory Agent will compute stock depletion curve; Supplier Agent will poll secondary domestic battery fabricators."
    },
    {
        "id": "DIS-2026-003",
        "title": "Maritime Storm Route Reroute: Arabian Sea Corridor",
        "type": "Logistics Route Disruption",
        "severity": "Medium",
        "affected_item": "Multiple Shipments / Industrial Lithium Batteries (SKU-BAT-4420)",
        "affected_shipment": "SH-103",
        "facility": "Chennai Central Hub",
        "reported_date": "2026-10-26 06:00",
        "description": "Tropical cyclone warning in North Arabian Sea necessitated maritime route diversion for vessels bound for Western and Southern Indian ports.",
        "impact_summary": "Average ocean freight transit delay of 4-6 days across maritime lanes; increased fuel surcharge expected.",
        "future_agent_task": "Logistics Agent will query real-time maritime telemetry and calculate alternate transshipment via Colombo port."
    }
]

# Alternative supplier catalog for investigation agent
ALTERNATIVE_SUPPLIERS = {
    "SKU-LAP-1001": [
        {
            "name": "Bharat Micro Systems Ltd.",
            "location": "Bengaluru, IN",
            "capacity": 75,
            "lead_time_days": 2,
            "unit_price_usd": 890,
            "reliability_score": 94,
            "notes": "Domestic buffer stock available for immediate bonded truck dispatch."
        },
        {
            "name": "Pacific Edge Computron",
            "location": "Penang, MY",
            "capacity": 120,
            "lead_time_days": 5,
            "unit_price_usd": 840,
            "reliability_score": 89,
            "notes": "Requires air express clearance; 5-day cycle time."
        }
    ],
    "SKU-BAT-4420": [
        {
            "name": "Deccan Energy Cells",
            "location": "Hyderabad, IN",
            "capacity": 400,
            "lead_time_days": 2,
            "unit_price_usd": 135,
            "reliability_score": 91,
            "notes": "Local certified battery pack fabricator with reserve batches."
        }
    ],
    "SKU-DSP-8890": [
        {
            "name": "Taipei Optronics",
            "location": "Taipei, TW",
            "capacity": 500,
            "lead_time_days": 3,
            "unit_price_usd": 105,
            "reliability_score": 93,
            "notes": "Express air-cargo slot available."
        }
    ]
}

# Alternate logistics routes and carriers for logistics agent
ALTERNATIVE_LOGISTICS = {
    "SH-101": [
        {
            "carrier": "BlueDart Aero Priority",
            "mode": "Expedited Air Freight",
            "transit_days": 1,
            "indicative_cost_usd": 1850,
            "feasibility": "High",
            "description": "Fast-track customs clearance and charter air courier directly to Hyderabad Airport."
        },
        {
            "carrier": "SpeedExpress Roadways",
            "mode": "Dedicated Bonded Trucking",
            "transit_days": 3,
            "indicative_cost_usd": 650,
            "feasibility": "Medium",
            "description": "Direct point-to-point highway transit upon port release."
        }
    ],
    "SH-103": [
        {
            "carrier": "Colombo Transshipment Express",
            "mode": "Feeder Vessel + Express Rail",
            "transit_days": 2,
            "indicative_cost_usd": 2400,
            "feasibility": "High",
            "description": "Disembark container at Colombo Port, bypass Arabian storm track, rail feeder to Chennai Hub."
        }
    ],
    "SH-105": [
        {
            "carrier": "Korean Air Cargo Priority",
            "mode": "Air Freight Direct",
            "transit_days": 1,
            "indicative_cost_usd": 1200,
            "feasibility": "High",
            "description": "Shift partial batch of 300 panels onto direct Incheon-Bengaluru cargo flight."
        }
    ]
}


def get_shipment_by_id(shipment_id: str):
    """Retrieve a shipment record by its identifier."""
    for s in SHIPMENTS:
        if s["id"].upper() == shipment_id.strip().upper():
            return s
    return None


def get_inventory_by_sku(sku: str):
    """Retrieve an inventory record by SKU."""
    for item in INVENTORY:
        if item["sku"].upper() == sku.strip().upper():
            return item
    return None


def get_disruptions_for_shipment(shipment_id: str):
    """Retrieve disruption incidents associated with a shipment."""
    return [
        d for d in DISRUPTIONS
        if d.get("affected_shipment", "").upper() == shipment_id.strip().upper()
    ]


def get_alternative_suppliers_for_sku(sku: str):
    """Retrieve mock alternative suppliers for a given SKU."""
    return ALTERNATIVE_SUPPLIERS.get(sku.upper(), [])


def get_alternative_logistics_for_shipment(shipment_id: str):
    """Retrieve mock alternative carriers and routes for a given shipment."""
    return ALTERNATIVE_LOGISTICS.get(shipment_id.upper(), [])
