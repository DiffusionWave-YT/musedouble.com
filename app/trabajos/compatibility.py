def compatibility(graph, info):
    """Admin-safe compatibility summary: no URLs, tokens, prompts or private paths."""
    missing = set()
    invalid = []
    for node in graph.values():
        class_name = node["class_type"]
        if class_name not in info:
            missing.add(class_name)
            continue
        schema = info[class_name].get("input", {})
        fields = {**schema.get("required", {}), **schema.get("optional", {})}
        for name, value in node["inputs"].items():
            if (node.get("_meta", {}).get("title") or node.get("title")) == "LOAD_IMAGE" and name == "image":
                continue  # Replaced by /upload/image before submission, never a required static file.
            spec = fields.get(name)
            if spec and isinstance(spec[0], list) and isinstance(value, (str, int, float)) and value not in spec[0]:
                invalid.append({"node": node.get("_meta", {}).get("title") or class_name,
                                "input": name, "message": "La opción configurada no está disponible en este servidor."})
    return {"compatible": not missing and not invalid, "missing_nodes": sorted(missing), "invalid_inputs": invalid}
