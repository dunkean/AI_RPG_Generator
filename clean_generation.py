# create project folders
import os
from pathlib import Path

from rpg_generator import query, generate
import prompt as P
from parsers import json_parser, table_parser
from logger import Logger
from llm import ChatGPT
import data_formatter as V
import generator as G

from defines import OUTPUT_FOLDER, INTERMEDIATE_FOLDER, LOG_FOLDER, CACHE_FOLDER, PORTRAITS_FOLDER, BUILDINGS_FOLDER


########


PROJECT_ID = "Enclave"
LORE = """A medieval fantasy world. Only one God exists (the god is non-gendered and called "the Old One") but people believes also in local beliefs. No undead. A single big nation (empire) on a unique continent the size of europe. """
GROUP_DESCRIPTION = "Deep within the heart of the formidable mountains lies The Forgotten Enclave, a resilient community eking out an existence within the vast ruins of a once-majestic city. Cut off from the outside world, these settlers and beggars have embraced their precarious existence, fashioning crude shelters amidst crumbling architecture and overgrown foliage. Silent whispers of a lost civilization echo through the labyrinthine streets, while weathered statues and dilapidated structures stand as testament to a grandeur long past. Life in The Forgotten Enclave is a constant struggle for survival, as residents scavenge for meager resources, relying on their resourcefulness and communal bonds to endure within this hauntingly beautiful, forgotten realm."
WORLD_TYPE = "Medieval fantasy"
INSTRUCTION = f"You are an assistant who generates on-demand data for a tabletop {WORLD_TYPE} role-playing game"
SCALE = "local"
TYPE = "small community"
POPULATION = 80
SEED = 42
# ratio = {"human": 0.75, "elf": 0.05, "half-elf": 0.05, "dwarf": 0.1, "halfling": 0.025, "gnome": 0.025}
RACE_RATIO = {"human": 0.6, "half-elf": 0.15, "elf":0.05, "dwarf": 0.15, "halfling": 0.025, "gnome": 0.025}
# potentially all generation parameters (groups distributions, and so on)

# MEAN_GROUP_SIZE = 8 ?????

# Bootstrap data
content = {
    "project_id": PROJECT_ID,
    "generation": {
        "seed": SEED,  # "optional"
        "instruction": INSTRUCTION,  # "optional"
    },
    "lore": {
        "bootstrap_description": LORE,
        "type": WORLD_TYPE  # "optional"
    },
    "details": {
        "scale": SCALE,  # "optional"
        "population": POPULATION,  # "optional"
        "bootstrap_description": GROUP_DESCRIPTION,
        "bootstrap_forced_context": "",
        "type": TYPE,  # "optional"
        "races": RACE_RATIO  # "optional"
    }
}

PROJECT_ID = content["project_id"]

# create project folders
for folder in [OUTPUT_FOLDER, INTERMEDIATE_FOLDER, LOG_FOLDER, CACHE_FOLDER, PORTRAITS_FOLDER, BUILDINGS_FOLDER]:
    Path(os.path.join(folder, PROJECT_ID, folder)).mkdir(parents=True, exist_ok=True)

# init Services
with open("openai.key", "r") as f:
    api_key = f.readline().strip()
    api_id = f.readline().strip()

# LLM = ChatGPT(Logger, INSTRUCTION, model_name="gpt-3.5-turbo", api_key=api_key, api_id=api_id)
# Q = query.LLM_Query(LLM, Logger)

# Bootstrap query
query(
    content,
    (f"{PROJECT_ID}_bootstrap", P.bootstrap),
    json_parser, V.bootstrap
)

# Query Details
categories_to_details = ["customs", "resources", "history", "external_influences", "timeline", "sites", "anecdotes"]
query(
    content,
    [(f"{PROJECT_ID}_details_{category}", P.details, category) for category in categories_to_details],
    json_parser, V.details, 
)

# Query Workplaces
query(
    content,
    (f"{PROJECT_ID}_workplaces", P.workplaces),
    table_parser, V.workplaces
)

# Generate population and groups
generate(
    content, G.population
)

# Query population per group
query(
    content,
    [(f"{PROJECT_ID}_population_{group_name}", P.population, group)
        for group_name, group in content["groups"].items()],
    table_parser, V.population
)

# Generate employees
generate(
    content, G.employees
)

# Query employees per workplace
query(
    content,
    [(f"{PROJECT_ID}_employees_{workplace_name}", P.employees, workplace)
        for workplace_name, workplace in content["workplaces"].items()],
    table_parser, V.employees
)

# Query workplaces details
query(
    content,
    [(f"{PROJECT_ID}_workplace_{workplace_name}", P.workplace_details, workplace)
        for workplace_name, workplace in content["workplaces"].items()],
    json_parser, V.workplace_details
)

# Query architecture and points of interest
query(
    content,
    (f"{PROJECT_ID}_architecture_and_poi", P.architecture_and_poi),
    json_parser, V.architecture_and_poi
)

# Query workplaces sites
query(
    content,
    [(f"{PROJECT_ID}_workplace_sites_{workplace_name}", P.workplace_sites, workplace)
        for workplace_name, workplace in content["workplaces"].items()],
    json_parser, V.workplace_sites
)

# Query key figures per groups and workplaces
key_figures = [member for group in content["groups"].values() for member in group["members"] if member["key_figure"]]
+ [member for workplace in content["workplaces"].values() for member in workplace["employees"] if member["key_figure"]]
query(
    content,
    [(f"{PROJECT_ID}_key_figure_{key_figure['name']}", P.key_figure, key_figure)
        for key_figure in key_figures],
    json_parser, V.key_figure
)

# Generate Portraits
# Generate Buildings
# Generate local_html
# Upload images
# Generate html