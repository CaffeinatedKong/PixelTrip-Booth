"""Fixed sample content; dates/record identities adapt to the shared demo room."""

from datetime import date, timedelta

from app.agents.proposals import ItineraryModel, RecommendationItem

DESTINATIONS = {
    "demo-da-nang": ("Da Nang, Vietnam", "Beach days, local food and nightlife", 94, 60),
    "demo-hoi-an": ("Hoi An, Vietnam", "Lantern streets, heritage and relaxed cafés", 88, 65),
    "demo-hue": ("Hue, Vietnam", "Imperial history, river walks and regional food", 82, 55),
}

DESTINATION_MATCH_COPY = {
    "demo-da-nang": {
        "whyThisFits": (
            "Da Nang gives Alice beachfront seafood, market food and lively evenings, "
            "while Bob gets coastal views, Marble Mountains and a pagoda visit. "
            "The Hoi An day trip adds culture without making every day a long transfer."
        ),
        "tradeOff": (
            "Bob gets scenic coast and viewpoints, but less time for history "
            "than Hue's dedicated heritage route."
        ),
    },
    "demo-hoi-an": {
        "whyThisFits": (
            "Hoi An's food stalls and cafés cater to Alice's food interests, "
            "while heritage streets and countryside cycling give Bob culture and scenery. "
            "Its compact centre lets the party explore together with beach breaks "
            "and relaxed riverside evenings."
        ),
        "tradeOff": "Alice may find the evenings too quiet if clubbing is a priority.",
    },
    "demo-hue": {
        "whyThisFits": (
            "Hue pairs regional food and markets for Alice with the Imperial City, "
            "pagoda and royal gardens for Bob's culture and scenery interests. "
            "Riverside downtime keeps the history-focused days from feeling crowded."
        ),
        "tradeOff": "Alice may have to trade lively club nights for quieter riverside evenings.",
    },
}

# time, title, location, description, sample SGD cost. All are demo estimates.
DA_NANG = [
    [
        (
            "16:30",
            "My Khe Beach Sunset",
            "My Khe Beach",
            "Settle in with a gentle beach walk after your flight.",
            0,
        ),
        (
            "19:00",
            "Local Seafood Dinner",
            "My Khe Beachfront",
            "Enjoy a relaxed beachfront dinner together.",
            35,
        ),
    ],
    [
        (
            "09:00",
            "Marble Mountains",
            "Ngu Hanh Son",
            "Explore the caves and viewpoints at an easy pace.",
            12,
        ),
        (
            "12:00",
            "Vietnamese Lunch",
            "Da Nang city centre",
            "Try a local lunch before the afternoon adventure.",
            15,
        ),
        (
            "15:00",
            "Han Market",
            "Han Market",
            "Browse local stalls and pick up small souvenirs.",
            10,
        ),
    ],
    [
        (
            "09:00",
            "Linh Ung Pagoda",
            "Son Tra Peninsula",
            "Visit the pagoda and take in the coastal views.",
            10,
        ),
        (
            "12:30",
            "City Café Lunch",
            "Hai Chau",
            "Share lunch and take a break in a city café.",
            15,
        ),
        (
            "19:30",
            "Dragon Bridge Evening Walk",
            "Dragon Bridge",
            "Explore the riverside lights; no scheduled fire show is assumed.",
            0,
        ),
    ],
    [
        (
            "09:00",
            "Hoi An Day Trip",
            "Hoi An Ancient Town",
            "Travel to the old town for a day of heritage and discovery.",
            30,
        ),
        (
            "13:00",
            "Local Food and Craft Stops",
            "Hoi An",
            "Sample local food and browse craft shops with the party.",
            20,
        ),
        (
            "18:00",
            "Lantern Streets",
            "Hoi An riverside",
            "Take an evening walk before returning to Da Nang.",
            10,
        ),
    ],
    [
        (
            "08:30",
            "Breakfast by the Beach",
            "My Khe",
            "Enjoy a final relaxed breakfast and pack for departure.",
            12,
        ),
        (
            "13:00",
            "Airport Transfer",
            "Da Nang International Airport",
            "Leave time for check-in before the fixed return flight.",
            15,
        ),
    ],
]

# Nearby destinations share DAD airport; each has its own prepared day content.
HOI_AN = [
    [
        (
            "16:30",
            "Ancient Town Arrival Walk",
            "Hoi An",
            "Settle in after the transfer from Da Nang airport.",
            10,
        ),
        (
            "19:00",
            "Cao Lau Dinner",
            "Hoi An Ancient Town",
            "Try regional noodles together in the old town.",
            20,
        ),
    ],
    [
        (
            "09:00",
            "Old Town Heritage Walk",
            "Hoi An Ancient Town",
            "Discover preserved streets and heritage buildings.",
            15,
        ),
        ("12:00", "Vietnamese Lunch", "Hoi An Market", "Pause for local dishes at the market.", 15),
        ("15:00", "Craft Shops", "Hoi An", "Browse handicrafts and souvenir stalls.", 10),
    ],
    [
        (
            "09:00",
            "Countryside Cycle",
            "Cam Thanh",
            "Explore quiet village lanes at an easy pace.",
            20,
        ),
        ("12:30", "Garden Café Lunch", "Hoi An", "Rest over lunch in a shady garden café.", 15),
        (
            "19:30",
            "Lantern Riverside Walk",
            "Thu Bon River",
            "Enjoy the lit streets and riverside atmosphere.",
            0,
        ),
    ],
    [
        ("09:00", "An Bang Beach", "An Bang", "Spend a relaxed morning at the beach.", 10),
        ("13:00", "Beach Café", "An Bang", "Enjoy food and conversation by the coast.", 20),
        (
            "18:00",
            "Old Town Evening",
            "Hoi An",
            "Return to the old town for a final evening stroll.",
            10,
        ),
    ],
    [
        (
            "08:30",
            "Breakfast in the Old Town",
            "Hoi An",
            "Have breakfast and prepare for the transfer.",
            12,
        ),
        (
            "13:00",
            "Airport Transfer",
            "Da Nang International Airport",
            "Transfer early enough for the fixed return flight.",
            25,
        ),
    ],
]
HUE = [
    [
        (
            "16:30",
            "Perfume River Arrival Walk",
            "Hue",
            "Settle in after the road transfer from Da Nang airport.",
            0,
        ),
        (
            "19:00",
            "Hue Regional Dinner",
            "Hue city centre",
            "Share a relaxed dinner of regional dishes.",
            20,
        ),
    ],
    [
        (
            "09:00",
            "Imperial City",
            "Hue Citadel",
            "Explore the historic courtyards and gardens.",
            20,
        ),
        (
            "12:00",
            "Vietnamese Lunch",
            "Hue city centre",
            "Enjoy regional food and a midday break.",
            15,
        ),
        ("15:00", "Dong Ba Market", "Dong Ba", "Browse local stalls and snacks.", 10),
    ],
    [
        (
            "09:00",
            "Thien Mu Pagoda",
            "Perfume River",
            "Visit the riverside pagoda and its grounds.",
            10,
        ),
        ("12:30", "Riverside Café Lunch", "Hue", "Pause over lunch near the river.", 15),
        (
            "19:30",
            "Hue Evening Walk",
            "Truong Tien Bridge",
            "Enjoy the riverside lights with the party.",
            0,
        ),
    ],
    [
        (
            "09:00",
            "Royal Tomb Gardens",
            "Hue outskirts",
            "Explore the landscaped historic grounds.",
            20,
        ),
        ("13:00", "Local Food Stops", "Hue", "Try regional snacks and local cafés.", 20),
        (
            "18:00",
            "Final River Evening",
            "Perfume River",
            "Enjoy a gentle last evening in Hue.",
            10,
        ),
    ],
    [
        (
            "08:30",
            "Breakfast and Check-out",
            "Hue",
            "Have breakfast and pack for the airport transfer.",
            12,
        ),
        (
            "11:30",
            "Airport Transfer",
            "Da Nang International Airport",
            "Allow extra road time to reach DAD for the return flight.",
            35,
        ),
    ],
]

PLANS = {"demo-da-nang": DA_NANG, "demo-hoi-an": HOI_AN, "demo-hue": HUE}
REFINEMENTS = {
    "Add a separate club visit after dinner": (1, "club"),
    "Replace lunch with a bar lunch": (2, "lunch"),
    "Add dinner before the evening walk": (3, "dinner"),
    "Start the morning later": (4, "later"),
    "Add a café stop before the airport transfer": (5, "cafe"),
}


def dates(room: dict) -> tuple[date, date]:
    start = date.fromisoformat(room["demo_start"])
    return start, start + timedelta(days=4)


def destination_items(room: dict) -> list[RecommendationItem]:
    start, end = dates(room)
    return [
        RecommendationItem(
            id=key,
            title=title,
            description=f"Prepared demo: {description}.",
            meta={
                "score": score,
                "pick": "Best fit" if index == 0 else "Wildcard",
                "tags": ["Vietnam", "Five days", "Sample plan"],
                "whyThisFits": DESTINATION_MATCH_COPY[key]["whyThisFits"],
                "bestFor": ["DemoAlice", "DemoBob"],
                "tradeOff": DESTINATION_MATCH_COPY[key]["tradeOff"],
                "details": f"Five-day sample adventure in {title}. Fly through DAD with transfers.",
                "estimatedDailyCostSgd": daily,
                "tripDays": 5,
                "tripStart": str(start),
                "tripEnd": str(end),
            },
        )
        for index, (key, (title, description, score, daily)) in enumerate(DESTINATIONS.items())
    ]


def flight_items(room: dict) -> list[RecommendationItem]:
    start, end = dates(room)
    options = [
        ("demo-flight-1", "Demo Air · direct", "09:00", "10:45", "16:00", "19:45", 280),
        ("demo-flight-2", "Sample Airways · direct", "10:00", "11:45", "17:00", "20:45", 320),
        ("demo-flight-3", "Booth Air · direct", "11:00", "12:45", "18:00", "21:45", 350),
    ]
    return [
        RecommendationItem(
            id=key,
            title=title,
            description="Sample return flight for this demo; not live or bookable.",
            meta={
                "price": price,
                "currency": "SGD",
                "carrier": title.split(" · ")[0],
                "origin": "SIN",
                "destination": "DAD",
                "duration_minutes": 165,
                "stops": 0,
                "depart_at": f"{start}T{depart}:00+08:00",
                "arrive_at": f"{start}T{arrive}:00+07:00",
                "return_at": f"{end}T{return_at}:00+07:00",
                "return_arrive_at": f"{end}T{return_arrive}:00+08:00",
                "score": 94 - index * 5,
                "pick": "Best fit" if index == 0 else "Wildcard",
                "tags": ["Direct", "Sample flight"],
                "whyThisFits": "Daytime flights leave time for the prepared activities.",
                "tradeOff": "Fictional airline, sample times and prices.",
                "details": "Direct sample SIN–DAD return flight. Flight cost is per person.",
            },
        )
        for index, (key, title, depart, arrive, return_at, return_arrive, price) in enumerate(
            options
        )
    ]


def build_itinerary(trip_id: str, room: dict, destination_id: str) -> ItineraryModel:
    start, _ = dates(room)
    title = DESTINATIONS[destination_id][0]
    return ItineraryModel(
        trip_id=trip_id,
        room_id=room["id"],
        title=f"The {title} Demo Quest",
        summary="Five days with DemoAlice and DemoBob. Costs and availability are sample data.",
        destination={"name": title},
        days=[
            {
                "day": n,
                "date": str(start + timedelta(days=n - 1)),
                "items": [
                    {
                        "id": f"d{n}-i{i}",
                        "time": time,
                        "title": name,
                        "location": location,
                        "description": description,
                        "cost": cost,
                        "tags": [],
                    }
                    for i, (time, name, location, description, cost) in enumerate(activities, 1)
                ],
            }
            for n, activities in enumerate(PLANS[destination_id], 1)
        ],
    )
