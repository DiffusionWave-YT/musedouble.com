import copy
import re
from fastapi import HTTPException

RATIOS = {"4:5": (1024, 1280), "5:4": (1280, 1024), "1:1": (1024, 1024), "9:16": (720, 1280), "16:9": (1280, 720)}


def title(node):
    return node.get("_meta", {}).get("title") or node.get("title", "")


def named(graph, name):
    matches = [(key, node) for key, node in graph.items() if title(node) == name]
    if len(matches) != 1:
        raise HTTPException(400, f"El workflow debe contener exactamente un nodo {name}.")
    return matches[0]


def validate_graph(graph, mode):
    if not isinstance(graph, dict) or not graph or isinstance(graph.get("nodes"), list) or isinstance(graph.get("links"), list):
        raise HTTPException(400, "Exporta el workflow con Save (API Format).")
    if len(graph) > 1000 or not all(isinstance(n, dict) and isinstance(n.get("class_type"), str) and isinstance(n.get("inputs"), dict) for n in graph.values()):
        raise HTTPException(400, "El workflow no es un grafo API válido.")
    required = {"SELECT_CHARACTER": [], "USER_PROMPT": ["text"], "CHARACTER_PROMPT": ["text"],
                "EYE_PROMPT": ["text"], "SEED": ["seed"], "BATCH_SIZE": ["value"], "FINAL_IMAGE": []}
    if mode == "reference":
        required.update({"LOAD_IMAGE": ["image"], "REFERENCE_STRENGTH": ["value"]})
    for name, fields in required.items():
        _, n = named(graph, name)
        if any(field not in n["inputs"] for field in fields):
            raise HTTPException(400, f"El nodo {name} no cumple el contrato de entradas.")
    _, character = named(graph, "SELECT_CHARACTER")
    if any(f"lora_{i}_{key}" not in character["inputs"] for i in range(1, 7) for key in ("name", "strength")):
        raise HTTPException(400, "SELECT_CHARACTER necesita seis ranuras de LoRA.")
    aspect_mode = "reference"
    if mode == "generate":
        if any(title(n) == "ASPECT_RATIOS" for n in graph.values()):
            _, n = named(graph, "ASPECT_RATIOS")
            if "aspect_ratio" not in n["inputs"]:
                raise HTTPException(400, "ASPECT_RATIOS necesita aspect_ratio.")
            aspect_mode = "label"
        else:
            for name in ["HORIZONTAL_RES", "VERTICAL_RES"]:
                if "value" not in named(graph, name)[1]["inputs"]:
                    raise HTTPException(400, "Faltan las dimensiones del workflow.")
            aspect_mode = "dimensions"
    for node in graph.values():
        for key, value in node["inputs"].items():
            if isinstance(value, str) and value and (re.search(r"password|api_?key|access_?token|secret", key, re.I)
                    or re.search(r"(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{20,}", value)):
                raise HTTPException(400, "El workflow contiene una entrada que podría guardar una credencial.")
    return {"mode": mode, "aspect_mode": aspect_mode, "titles": list(required)}


def build_graph(original, mode, model, params, reference_name=None):
    graph = copy.deepcopy(original)
    contract = validate_graph(graph, mode)
    for name, value in [("USER_PROMPT", params["prompt"]), ("CHARACTER_PROMPT", model["character_prompt"]), ("EYE_PROMPT", model["eye_prompt"])]:
        named(graph, name)[1]["inputs"]["text"] = value
    named(graph, "SEED")[1]["inputs"]["seed"] = params["seed"]
    named(graph, "BATCH_SIZE")[1]["inputs"]["value"] = params["batch"]
    inputs = named(graph, "SELECT_CHARACTER")[1]["inputs"]
    for i in range(1, 7):
        item = model["loras"][i - 1] if len(model["loras"]) >= i else {"name": "None", "strength": 0}
        inputs[f"lora_{i}_name"] = item["name"]
        inputs[f"lora_{i}_strength"] = item["strength"]
    if mode == "generate":
        if contract["aspect_mode"] == "label":
            named(graph, "ASPECT_RATIOS")[1]["inputs"]["aspect_ratio"] = params["ratio"]
        else:
            width, height = RATIOS[params["ratio"]]
            named(graph, "HORIZONTAL_RES")[1]["inputs"]["value"] = width
            named(graph, "VERTICAL_RES")[1]["inputs"]["value"] = height
    else:
        if not reference_name:
            raise ValueError("Reference upload missing")
        named(graph, "LOAD_IMAGE")[1]["inputs"]["image"] = reference_name
        named(graph, "REFERENCE_STRENGTH")[1]["inputs"]["value"] = params["strength"]
    assert named(graph, "FINAL_IMAGE")[1] == named(original, "FINAL_IMAGE")[1]
    return graph
