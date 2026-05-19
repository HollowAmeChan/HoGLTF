import json


HOGLTF_NODE_GROUP_NAME = "HoGLTF"
HOGLTF_NODE_GROUP_PROPERTY = "hogltf_node_group"
HOGLTF_CONTRACT_GROUP_PROPERTY = "HoGLTFContract"


def find_hogltf_node(blender_material):
    node_tree = getattr(blender_material, "node_tree", None)
    if node_tree is None:
        return None

    return _find_hogltf_node_in_tree(node_tree, set())


def material_has_hogltf_node(blender_material):
    return find_hogltf_node(blender_material) is not None


def should_export_material_contract(scene_props, material_props, blender_material):
    if not scene_props.enabled:
        return False
    if not scene_props.export_material_contracts:
        return False
    return material_props.export_contract or material_has_hogltf_node(blender_material)


def build_material_contract(extension_name, scene_props, blender_material):
    material_props = blender_material.hogltf
    contract = {
        "schema": extension_name,
        "schemaVersion": 1,
        "source": {
            "tool": "HoGLTF",
            "blenderMaterial": blender_material.name,
        },
        "target": {
            "shaderFamily": _target_shader_family(scene_props, material_props),
        },
        "principled": {},
        "toon": {},
        "unity": {},
        "extras": {},
    }

    hogltf_node = read_hogltf_node_inputs(blender_material)
    if hogltf_node is not None:
        contract["hogltf"] = hogltf_node

    contract.update(_parse_contract_json(material_props.contract_json, blender_material.name))

    if scene_props.write_debug_fields:
        contract.setdefault("extras", {})["blenderCustomProperties"] = {
            key: blender_material[key]
            for key in blender_material.keys()
            if isinstance(blender_material[key], (str, int, float, bool))
        }

    return contract


def read_hogltf_node_inputs(blender_material):
    node = find_hogltf_node(blender_material)
    if node is None:
        return None

    inputs = {}
    sockets = []
    for socket in node.inputs:
        if not getattr(socket, "enabled", True):
            continue

        socket_value = _socket_default_value(socket)
        inputs[socket.name] = socket_value
        sockets.append({
            "name": socket.name,
            "identifier": getattr(socket, "identifier", socket.name),
            "type": getattr(socket, "bl_socket_idname", getattr(socket, "type", "")),
            "linked": bool(getattr(socket, "is_linked", False)),
            "value": socket_value,
            "link": _socket_link_info(socket),
        })

    return {
        "node": node.name,
        "nodeLabel": node.label,
        "nodeGroup": _node_group_name(node),
        "inputs": inputs,
        "sockets": sockets,
    }


def _find_hogltf_node_in_tree(node_tree, visited):
    tree_id = id(node_tree)
    if tree_id in visited:
        return None
    visited.add(tree_id)

    for node in node_tree.nodes:
        if _is_hogltf_group_node(node):
            return node

    for node in node_tree.nodes:
        child_tree = _node_group_tree(node)
        if child_tree is None:
            continue
        found = _find_hogltf_node_in_tree(child_tree, visited)
        if found is not None:
            return found

    return None


def _is_hogltf_group_node(node):
    group_tree = _node_group_tree(node)
    if group_tree is None:
        return False

    for owner in (node, group_tree):
        marker = _custom_property_value(owner, HOGLTF_NODE_GROUP_PROPERTY)
        if marker is not None:
            return _is_truthy_marker(marker)
        contract_marker = _custom_property_value(owner, HOGLTF_CONTRACT_GROUP_PROPERTY)
        if contract_marker is not None:
            return True

    return _matches_hogltf_name(getattr(group_tree, "name", ""))


def _node_group_tree(node):
    if getattr(node, "type", "") == "GROUP":
        return getattr(node, "node_tree", None)

    if getattr(node, "bl_idname", "") == "ShaderNodeGroup":
        return getattr(node, "node_tree", None)

    return None


def _node_group_name(node):
    group_tree = _node_group_tree(node)
    return group_tree.name if group_tree is not None else ""


def _matches_hogltf_name(name):
    if name.startswith("HoLilToon") or name == "HoLilPBR":
        return True

    if name == HOGLTF_NODE_GROUP_NAME:
        return True

    prefix = f"{HOGLTF_NODE_GROUP_NAME}."
    if not name.startswith(prefix):
        return False

    suffix = name[len(prefix):]
    return len(suffix) == 3 and suffix.isdigit()


def _custom_property_value(data_block, property_name):
    try:
        return data_block.get(property_name)
    except AttributeError:
        return None


def _is_truthy_marker(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _socket_default_value(socket):
    if not hasattr(socket, "default_value"):
        return None
    return _json_value(socket.default_value)


def _socket_link_info(socket):
    if not getattr(socket, "is_linked", False):
        return None

    links = getattr(socket, "links", [])
    if len(links) == 0:
        return None

    link = links[0]
    from_node = link.from_node
    info = {
        "fromNode": getattr(from_node, "name", ""),
        "fromNodeType": getattr(from_node, "bl_idname", getattr(from_node, "type", "")),
        "fromSocket": getattr(link.from_socket, "name", ""),
    }

    image = getattr(from_node, "image", None)
    if image is not None:
        info["image"] = {
            "name": image.name,
            "filepath": getattr(image, "filepath", ""),
            "source": getattr(image, "source", ""),
            "colorspace": getattr(getattr(image, "colorspace_settings", None), "name", ""),
        }

    return info


def _json_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    if value is None:
        return None

    try:
        return [_json_value(item) for item in value]
    except TypeError:
        return str(value)


def _target_shader_family(scene_props, material_props):
    if material_props.target_shader_family == "inherit":
        return scene_props.target_shader_family
    return material_props.target_shader_family


def _parse_contract_json(raw_json, material_name):
    if raw_json.strip() == "":
        return {}

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        print(f"HoGLTF: material '{material_name}' has invalid contract JSON: {exc}")
        return {}

    if not isinstance(parsed, dict):
        print(f"HoGLTF: material '{material_name}' contract JSON must be a JSON object.")
        return {}

    return parsed
