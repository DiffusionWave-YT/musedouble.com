import copy
import re
from fastapi import HTTPException

RATIOS = {"1:1": (1024, 1024), "4:5": (1024, 1280), "5:4": (1280, 1024), "3:4": (960, 1280), "4:3": (1280, 960), "2:3": (848, 1280), "3:2": (1280, 848), "9:16": (720, 1280), "16:9": (1280, 720), "21:9": (1280, 544)}
RESOLUTIONS = (1280, 1920, 2560)
MAX_REFERENCES = 4


def title(node):
    return node.get("_meta", {}).get("title") or node.get("title", "")


def matches(graph, name):
    return [(key, node) for key, node in graph.items() if title(node).casefold() == name.casefold()]


def present(graph, name):
    return bool(matches(graph, name))


def named(graph, name):
    found = matches(graph, name)
    if len(found) != 1:
        raise HTTPException(400, f"El workflow debe contener exactamente un nodo {name}.")
    return found[0]


def needs(graph, name, fields):
    _, node = named(graph, name)
    if any(field not in node["inputs"] for field in fields):
        raise HTTPException(400, f"El nodo {name} no cumple el contrato de entradas.")


def finals(graph):
    found = [(key, node) for key, node in graph.items() if re.fullmatch(r"FINAL_IMAGE(_\d+)?", title(node), re.I)]
    return sorted(found, key=lambda item: title(item[1]).casefold())


def resolution_node(graph):
    found = matches(graph, "RESOLUTION")
    if not found:
        found = [(key, node) for key, node in graph.items() if node.get("class_type") == "dw_aspect_resolution"]
    if len(found) != 1:
        raise HTTPException(400, "El workflow debe contener exactamente un nodo RESOLUTION.")
    if any(field not in found[0][1]["inputs"] for field in ("aspect_ratio", "long_side")):
        raise HTTPException(400, "El nodo RESOLUTION no cumple el contrato de entradas.")
    return found[0]


def reference_slots(graph):
    count = 0
    while count < MAX_REFERENCES and present(graph, f"LOAD_IMAGE_{count + 1}"):
        count += 1
    return count


def reject_credentials(graph):
    for node in graph.values():
        for key, value in node["inputs"].items():
            if isinstance(value, str) and value and (re.search(r"password|api_?key|access_?token|secret", key, re.I)
                    or re.search(r"(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{20,}", value)):
                raise HTTPException(400, "El workflow contiene una entrada que podría guardar una credencial.")


def validate_reference(graph):
    needs(graph, "USER_PROMPT", ["text"])
    if not finals(graph):
        raise HTTPException(400, "El workflow debe contener al menos un nodo FINAL_IMAGE.")
    resolution_node(graph)
    if present(graph, "SEED"):
        needs(graph, "SEED", ["seed"])
        seed_node = "SEED"
    elif present(graph, "DW_SETUP"):
        needs(graph, "DW_SETUP", ["seed"])
        seed_node = "DW_SETUP"
    else:
        raise HTTPException(400, "El workflow necesita un nodo SEED o DW_SETUP.")
    slots = reference_slots(graph)
    if slots == 0:
        raise HTTPException(400, "El workflow necesita al menos un nodo LOAD_IMAGE_1.")
    for index in range(1, slots + 1):
        needs(graph, f"LOAD_IMAGE_{index}", ["image"])
    reject_credentials(graph)
    return {"mode": "reference", "seed_node": seed_node, "references": slots, "finals": len(finals(graph))}


def validate_graph(graph, mode):
    if not isinstance(graph, dict) or not graph or isinstance(graph.get("nodes"), list) or isinstance(graph.get("links"), list):
        raise HTTPException(400, "Exporta el workflow con Save (API Format).")
    if len(graph) > 1000 or not all(isinstance(n, dict) and isinstance(n.get("class_type"), str) and isinstance(n.get("inputs"), dict) for n in graph.values()):
        raise HTTPException(400, "El workflow no es un grafo API válido.")
    if mode == "reference":
        return validate_reference(graph)
    titles = {"SELECT_CHARACTER": [], "USER_PROMPT": ["text"], "CHARACTER_PROMPT": ["text"], "FINAL_IMAGE": []}
    if present(graph, "EYE_PROMPT"):
        titles["EYE_PROMPT"] = ["text"]
    if present(graph, "SEED"):
        titles["SEED"], seed_node = ["seed"], "SEED"
    elif present(graph, "DW_SETUP"):
        titles["DW_SETUP"], seed_node = ["seed", "batch_size"], "DW_SETUP"
    else:
        raise HTTPException(400, "El workflow necesita un nodo SEED o DW_SETUP.")
    if present(graph, "BATCH_SIZE"):
        titles["BATCH_SIZE"], batch_node = ["value"], "BATCH_SIZE"
    elif seed_node == "DW_SETUP":
        batch_node = "DW_SETUP"
    else:
        raise HTTPException(400, "El workflow necesita un nodo BATCH_SIZE o DW_SETUP.")
    for name, fields in titles.items():
        needs(graph, name, fields)
    _, character = named(graph, "SELECT_CHARACTER")
    if any(f"lora_{i}_{key}" not in character["inputs"] for i in range(1, 7) for key in ("name", "strength")):
        raise HTTPException(400, "SELECT_CHARACTER necesita seis ranuras de LoRA.")
    if present(graph, "RESOLUTION"):
        needs(graph, "RESOLUTION", ["aspect_ratio", "long_side"])
        aspect_mode = "resolution"
    elif present(graph, "ASPECT_RATIOS"):
        needs(graph, "ASPECT_RATIOS", ["aspect_ratio"])
        aspect_mode = "label"
    else:
        for name in ["HORIZONTAL_RES", "VERTICAL_RES"]:
            needs(graph, name, ["value"])
        aspect_mode = "dimensions"
    reject_credentials(graph)
    return {"mode": mode, "aspect_mode": aspect_mode, "seed_node": seed_node, "batch_node": batch_node, "titles": list(titles)}


def build_reference_graph(graph, contract, params, references):
    slots = contract["references"]
    if not 1 <= len(references) <= slots:
        raise ValueError("Reference upload missing")
    named(graph, "USER_PROMPT")[1]["inputs"]["text"] = params["prompt"]
    named(graph, contract["seed_node"])[1]["inputs"]["seed"] = params["seed"]
    inputs = resolution_node(graph)[1]["inputs"]
    inputs["aspect_ratio"] = params["ratio"]
    inputs["long_side"] = params.get("resolution") or RESOLUTIONS[1]
    removed = set()
    for index in range(1, slots + 1):
        if index <= len(references):
            named(graph, f"LOAD_IMAGE_{index}")[1]["inputs"]["image"] = references[index - 1]
            continue
        for name in (f"LOAD_IMAGE_{index}", f"RESIZE_IMAGE_{index}"):
            for key, _ in matches(graph, name):
                removed.add(key)
    for key in removed:
        del graph[key]
    for node in graph.values():
        for field in [f for f, value in node["inputs"].items() if isinstance(value, list) and len(value) == 2 and str(value[0]) in removed]:
            del node["inputs"][field]
    return graph


def build_graph(original, mode, model, params, references=None):
    graph = copy.deepcopy(original)
    contract = validate_graph(graph, mode)
    if mode == "reference":
        return build_reference_graph(graph, contract, params, references or [])
    texts = [("USER_PROMPT", params["prompt"]), ("CHARACTER_PROMPT", model["character_prompt"])]
    if present(graph, "EYE_PROMPT"):
        texts.append(("EYE_PROMPT", model["eye_prompt"]))
    for name, value in texts:
        named(graph, name)[1]["inputs"]["text"] = value
    if contract["seed_node"] == "SEED":
        named(graph, "SEED")[1]["inputs"]["seed"] = params["seed"]
    else:
        named(graph, "DW_SETUP")[1]["inputs"]["seed"] = params["seed"]
    if contract["batch_node"] == "BATCH_SIZE":
        named(graph, "BATCH_SIZE")[1]["inputs"]["value"] = params["batch"]
    else:
        named(graph, "DW_SETUP")[1]["inputs"]["batch_size"] = params["batch"]
    inputs = named(graph, "SELECT_CHARACTER")[1]["inputs"]
    for i in range(1, 7):
        item = model["loras"][i - 1] if len(model["loras"]) >= i else {"name": "None", "strength": 0}
        inputs[f"lora_{i}_name"] = item["name"]
        inputs[f"lora_{i}_strength"] = item["strength"]
    if contract["aspect_mode"] == "resolution":
        resolution = named(graph, "RESOLUTION")[1]["inputs"]
        resolution["aspect_ratio"] = params["ratio"]
        resolution["long_side"] = params.get("resolution") or RESOLUTIONS[1]
    elif contract["aspect_mode"] == "label":
        named(graph, "ASPECT_RATIOS")[1]["inputs"]["aspect_ratio"] = params["ratio"]
    else:
        width, height = RATIOS[params["ratio"]]
        named(graph, "HORIZONTAL_RES")[1]["inputs"]["value"] = width
        named(graph, "VERTICAL_RES")[1]["inputs"]["value"] = height
    assert named(graph, "FINAL_IMAGE")[1] == named(original, "FINAL_IMAGE")[1]
    return graph
