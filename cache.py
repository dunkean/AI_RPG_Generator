import json
import os

import defines as D

cache_dict = {}
cache_file = os.path.join(D.CACHE_FOLDER, "cache.json")
if os.path.exists(cache_file):
    with open(cache_file, "r") as infile:
        cache_dict = json.load(infile)


def hasCache(id, key):
#     return key in cache

# def getCache(cache, key):
#     return cache[key]

# def setCache(cache, key, value):
#     cache[key] = value