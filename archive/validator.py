import shortuuid


def bootstrap(response):
    patch = {
        "details": {},
        "setting": {
            "keywords": response["world_setting"],
        }
    }
    del response["world_setting"]

    for k, v in response.items():
        if k in ["culture", "customs", "goals", "resources", "history", "external_influences", "timeline", "sites", "anecdotes"]:
            patch["details"][k] = {"keywords": v}
        else:
            patch["details"][k] = v

    return patch


def descriptions(response):
    order = []
    for k, _ in response["descriptions"]["long"].items():
        order.append(k)
    response["descriptions"]["order"] = order
    return {
        "details": response
    }


def detail(response):
    validated_response = {}
    for k, v in response.items():
        validated_response[k] = {"descriptions": v}

    return {
        "details": validated_response
    }


def external_influences(response):
    for k, v in response.items():
        v["name"] = k

    return {
        "details": {
            "external_influences": {
                "groups": {shortuuid.uuid(): v for v in response.values()}
            }
        }
    }


def activity_groups(content, response):
    # normalize population
    sum_pop = sum([v["population"] for v in response if v["population"] > 3])
    factor = content["details"]["population"] / sum_pop
    for v in response:
        if v["population"] > 3:
            v["population"] = int(v["population"] * factor)

    return {
        "groups": {
            "activity": {shortuuid.uuid(): v for v in response}
        }
    }
