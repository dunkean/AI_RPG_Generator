"""Mock LLM responses for testing — ported from archive/responses.py."""


def bootstrap() -> str:
    return """{
    "name": "Rust Riders",
    "keywords": ["Bikers", "Pillaging", "Robbing", "Corporate Transports", "Charismatic Leader", "Former Soldier", "Desert Nomads", "Survivalists", "Highly Organized", "Weaponry"],
    "setting_setting": ["Nuclear Devastation", "Biological Wars", "Cybernetic Implants", "High Technology", "Low Life", "Rich Corporations", "Bunkered Cities", "Savage Desert Land", "Post-apocalyptic", "Ravaged World"],
    "influence_areas": ["Desert Wasteland", "Corporate Trade Routes", "Abandoned Settlements", "Outskirts of New York", "Hidden Bunkers"],
    "structure": "hierarchy",
    "prosperity": "low",
    "culture": ["Rebellion", "Adaptability", "Individualism", "Survival Skills", "Biker Aesthetics", "Comradery"],
    "customs": ["Motorcycle Rituals", "Weapons Modification", "Bartering System", "Nomadic Lifestyle", "Respect for the Leader", "Tattoo Tradition"],
    "goals": ["Challenging Corporate Authority", "Seeking Independence", "Gaining Wealth", "Expanding Territory", "Protecting Their Own", "Obtaining Advanced Technology"],
    "resources": ["Stolen Supplies", "Weapons Stockpile", "Scavenged Technology", "Knowledge of Trade Routes", "Hidden Stashes", "Mobile Hideouts", "Criminal Connections", "Survival Gear"],
    "history": ["Founding in Chaos", "Rise of the Charismatic Leader", "First Successful Robbery", "Conflict with Rival Gang", "Alliance with Mercenary Group", "Siege on Corporate Outpost"],
    "external_influences": ["Rival Gangs", "Mercenary Groups", "Corporate Security Forces", "Desert Bandits", "Mutant Tribes", "Resistance Movements", "Corrupt Officials", "Underground Market", "Post-apocalyptic Cults", "Mysterious Techno-Religious Order"],
    "timeline": ["Annual Celebration of Survival", "Leader's Day of Remembrance", "Raid on Corporate Convoy", "Encounter with a Mutated Beast", "Devastating Sandstorm", "Execution of a Traitor"],
    "sites": ["Ruined Factory Hideout", "Scrapyard Stronghold", "Abandoned Subway Tunnels", "Rooftop Lookout Points", "Junkyard Temple"],
    "anecdotes": ["Legend of the Unbreakable Motorcycle Chain", "The Lost Treasure of the Megacorp Vault", "The Night the City Lights Went Out", "The Unlikely Friendship with a Robot", "The Biker's Ghostly Encounter", "The Epic Sand Race"],
    "races": {
        "human": 0.9,
        "cyborg": 0.05,
        "mutant": 0.05
    },
    "member_bonds": {
        "family": 0.3,
        "friends": 0.25,
        "colleagues": 0.15,
        "strangers": 0.2,
        "common goal": 0.1
    }
}"""


def description() -> str:
    return """{
    "descriptions": {
        "short": "The Rust Riders, a post-apocalyptic gang of bikers, ravage the savage desert lands near New York.",
        "long": {
            "Overview": "In the wastelands surrounding New York, the Rust Riders emerge as a formidable force.",
            "The Charismatic Leader": "At the helm stands their enigmatic leader, a former soldier."
        }
    }
}"""


def culture() -> str:
    return """{
    "culture": {
        "A Resilient Brotherhood": "The Rust Riders embody a resilient brotherhood.",
        "Motorcycle Madness": "Motorcycles are the lifeblood of the Rust Riders."
    }
}"""


def external_influences() -> str:
    return """{
    "Rival Gangs": {
        "type": "Gang",
        "scale": "local",
        "description": "Rust Riders have several rival gangs in the desert.",
        "keywords": ["Bikers", "Conflict", "Power Struggle", "Desert Territory", "Weapons", "Cybernetic Enhancements", "Survival", "Raiding"],
        "population": 25,
        "relationship": "Rust Riders and their rival gangs have a long history of conflict."
    },
    "Desert Nomads": {
        "type": "Tribe",
        "scale": "regional",
        "description": "Desert Nomads are a loose collection of tribes.",
        "keywords": ["Nomads", "Survivalism", "Cybernetic Enhancements", "Trade", "Desert Wasteland", "Small-scale Communities", "Resourceful", "Cultural Diversity"],
        "population": 200,
        "relationship": "Rust Riders and Desert Nomads have a complex relationship."
    }
}"""


def activity_groups() -> str:
    return """{
    "groups": [
        {
            "name": "The Mechanic Gang",
            "activity": "Mechanics",
            "type": "Service Group",
            "keywords": ["Mechanics", "Repairs", "Modifications"],
            "motivations": ["Improving vehicles"],
            "role": "Service",
            "structure": "decentralized",
            "population": 8,
            "prosperity": "poor",
            "origin": {"local": 0.9, "foreign": 0.1},
            "age_ratio": {"child": 0, "teen": 0, "adult": 1, "middle-aged": 0, "old": 0},
            "common_bonds": ["Business", "Knowledge", "Place", "Interests"]
        },
        {
            "name": "The Scrap Collectors",
            "activity": "Scavengers",
            "type": "Resource Group",
            "keywords": ["Scavenging", "Recycling", "Upcycling"],
            "motivations": ["Sourcing materials"],
            "role": "Resource",
            "structure": "decentralized",
            "population": 12,
            "prosperity": "poor",
            "origin": {"local": 0.7, "foreign": 0.3},
            "age_ratio": {"child": 0.1, "teen": 0.15, "adult": 0.6, "middle-aged": 0.1, "old": 0.05},
            "common_bonds": ["Business", "Place", "Knowledge", "Interests"]
        }
    ]
}"""
