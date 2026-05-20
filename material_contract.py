import json


HOGLTF_NODE_GROUP_NAME = "HoGLTF"
HOGLTF_NODE_GROUP_PROPERTY = "hogltf_node_group"
HOGLTF_CONTRACT_GROUP_PROPERTY = "HoGLTFContract"
ALPHA_MODE_NAMES = {
    0: "Opaque",
    1: "Cutout",
    2: "Dither",
    3: "Transparent",
}
RENDERING_MODE_BY_ALPHA_MODE = {
    0: "Opaque",
    1: "Cutout",
    2: "Cutout",
    3: "Transparent",
}
TRANSPARENT_MODE_NAMES = {
    0: "Normal",
    1: "OnePass",
    2: "TwoPass",
}
TARGET_SHADER_VARIANT_NAMES = {
    0: "auto",
    1: "standard",
    2: "lite",
    3: "tessellation",
    4: "refraction",
    5: "gem",
    6: "fur",
    7: "furOnly",
    8: "multi",
    9: "fakeShadow",
}


def find_hogltf_node(blender_material):
    node_tree = getattr(blender_material, "node_tree", None)
    if node_tree is None:
        return None

    active_node = _find_active_output_hogltf_node(node_tree)
    if active_node is not None:
        return active_node

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
        _apply_hogltf_node_summary(contract, hogltf_node)

    _deep_update(contract, _parse_contract_json(material_props.contract_json, blender_material.name))

    if scene_props.write_debug_fields:
        contract.setdefault("extras", {})["blenderCustomProperties"] = {
            key: blender_material[key]
            for key in blender_material.keys()
            if isinstance(blender_material[key], (str, int, float, bool))
        }

    return contract


def _apply_hogltf_node_summary(contract, hogltf_node):
    node_group = hogltf_node.get("nodeGroup", "")
    node_group_variant = hogltf_node.get("nodeGroupVariant", "")
    target = contract.setdefault("target", {})
    inferred_family = _shader_family_from_node_group(node_group)
    if inferred_family is not None:
        target["shaderFamily"] = inferred_family

    variant = node_group_variant or _shader_variant_from_node_group(node_group)
    variant_socket = _int_socket_value(hogltf_node, "TargetShaderVariant")
    if (variant is None or variant == "max") and variant_socket is not None:
        variant = TARGET_SHADER_VARIANT_NAMES.get(variant_socket, str(variant_socket))
    if variant is not None:
        target.setdefault("shaderVariant", variant)

    alpha_mode = _int_socket_value(hogltf_node, "AlphaMode")
    if alpha_mode is not None:
        target.setdefault("renderingMode", RENDERING_MODE_BY_ALPHA_MODE.get(alpha_mode, str(alpha_mode)))

    transparent_mode = _int_socket_value(hogltf_node, "TransparentMode")
    if transparent_mode is not None:
        target.setdefault("transparentMode", TRANSPARENT_MODE_NAMES.get(transparent_mode, str(transparent_mode)))

    use_outline = _number_socket_value(hogltf_node, "UseOutline")
    if use_outline is not None:
        target.setdefault("outline", use_outline > 0.0)

    for flag_name, target_name in (
        ("UseLite", "lite"),
        ("UseTessellation", "tessellation"),
        ("UseMulti", "multi"),
        ("UseRefraction", "refraction"),
        ("UseGem", "gem"),
        ("UseFur", "fur"),
    ):
        value = _number_socket_value(hogltf_node, flag_name)
        if value is not None:
            target.setdefault(target_name, value > 0.0)

    _apply_principled_summary(contract, hogltf_node)
    _apply_toon_summary(contract, hogltf_node)
    _apply_unity_summary(contract, hogltf_node)


def _apply_principled_summary(contract, hogltf_node):
    principled = contract.setdefault("principled", {})

    base_color = _socket_value(hogltf_node, "BaseColor")
    if base_color is not None:
        principled.setdefault("baseColor", {})["factor"] = base_color

    base_texture = _socket_texture_info(hogltf_node, "BaseTex")
    if base_texture is not None:
        principled.setdefault("baseColor", {})["texture"] = base_texture

    metallic = _number_socket_value(hogltf_node, "Metallic")
    if metallic is not None:
        principled.setdefault("metallic", {})["factor"] = metallic

    roughness = _number_socket_value(hogltf_node, "Roughness")
    if roughness is not None:
        principled.setdefault("roughness", {})["factor"] = roughness

    alpha = _number_socket_value(hogltf_node, "Alpha")
    if alpha is not None:
        principled["alpha"] = alpha

    alpha_mode = _int_socket_value(hogltf_node, "AlphaMode")
    if alpha_mode is not None:
        principled["alphaMode"] = ALPHA_MODE_NAMES.get(alpha_mode, str(alpha_mode))

    normal_texture = _first_socket_texture_info(hogltf_node, ("NormalTex", "NormalMap", "BumpMap"))
    if normal_texture is not None:
        principled.setdefault("normal", {})["texture"] = normal_texture

    normal_scale = _first_number_socket_value(hogltf_node, ("NormalScale", "BumpScale"))
    if normal_scale is not None:
        principled.setdefault("normal", {})["scale"] = normal_scale

    emission_color = _first_socket_value(hogltf_node, ("EmissionColor", "Emission"))
    if emission_color is not None:
        principled.setdefault("emission", {})["color"] = emission_color

    emission_strength = _number_socket_value(hogltf_node, "EmissionStrength")
    if emission_strength is not None:
        principled.setdefault("emission", {})["strength"] = emission_strength

    occlusion_texture = _first_socket_texture_info(hogltf_node, ("OcclusionTex", "OcclusionMap", "AOTex", "AOMap"))
    if occlusion_texture is not None:
        principled.setdefault("geometry", {})["occlusion"] = {"texture": occlusion_texture}

    height_texture = _first_socket_texture_info(hogltf_node, ("HeightTex", "HeightMap", "ParallaxMap"))
    if height_texture is not None:
        principled.setdefault("geometry", {})["height"] = {"texture": height_texture}


def _apply_toon_summary(contract, hogltf_node):
    node_group = hogltf_node.get("nodeGroup", "")
    toon = contract.setdefault("toon", {})
    if node_group.startswith("HoLilToon"):
        toon.setdefault("enabled", True)
        variant = hogltf_node.get("nodeGroupVariant") or _shader_variant_from_node_group(node_group)
        if variant is not None:
            toon.setdefault("variant", variant)

    use_shadow = _number_socket_value(hogltf_node, "UseShadow")
    shadow_texture = _socket_texture_info(hogltf_node, "ShadowTex")
    shadow_color = _socket_value(hogltf_node, "ShadowColor")
    if use_shadow is not None or shadow_texture is not None or shadow_color is not None:
        shadow = toon.setdefault("shadow", {})
        if use_shadow is not None:
            shadow["enabled"] = use_shadow > 0.0
        if shadow_texture is not None:
            shadow["texture"] = shadow_texture
        if shadow_color is not None:
            shadow["color"] = shadow_color

    use_rim = _first_number_socket_value(hogltf_node, ("UseRim", "RimEnabled"))
    rim_color = _socket_value(hogltf_node, "RimColor")
    if use_rim is not None or rim_color is not None:
        rim = toon.setdefault("rim", {})
        if use_rim is not None:
            rim["enabled"] = use_rim > 0.0
        if rim_color is not None:
            rim["color"] = rim_color

    use_outline = _first_number_socket_value(hogltf_node, ("UseOutline", "OutlineEnabled"))
    outline_color = _socket_value(hogltf_node, "OutlineColor")
    outline_width = _first_number_socket_value(hogltf_node, ("OutlineWidth", "OutlineWidthMaskStrength"))
    if use_outline is not None or outline_color is not None or outline_width is not None:
        outline = toon.setdefault("outline", {})
        if use_outline is not None:
            outline["enabled"] = use_outline > 0.0
        if outline_color is not None:
            outline["color"] = outline_color
        if outline_width is not None:
            outline["width"] = outline_width


def _apply_unity_summary(contract, hogltf_node):
    unity = contract.setdefault("unity", {})

    cull_mode = _int_socket_value(hogltf_node, "CullMode")
    if cull_mode is not None:
        unity["cullMode"] = cull_mode
        unity["doubleSided"] = cull_mode == 0

    render_queue = _int_socket_value(hogltf_node, "RenderQueue")
    if render_queue is not None:
        unity["renderQueue"] = render_queue


def _shader_family_from_node_group(node_group):
    if node_group.startswith("HoLilToon"):
        return "lilToon"
    if node_group == "HoLilPBR":
        return "lilPBR"
    return None


def _shader_variant_from_node_group(node_group):
    variants = {
        "HoLilToonMax": "max",
        "HoLilToonStandard": "standard",
        "HoLilToonLite": "lite",
        "HoLilToonTessellation": "tessellation",
        "HoLilToonRefraction": "refraction",
        "HoLilToonGem": "gem",
        "HoLilToonFur": "fur",
        "HoLilToonFurOnly": "furOnly",
        "HoLilToonMulti": "multi",
        "HoLilToonFakeShadow": "fakeShadow",
        "HoLilPBR": "pbr",
    }
    return variants.get(node_group)


def _socket_value(hogltf_node, name):
    inputs = hogltf_node.get("inputs", {})
    if name in inputs:
        return inputs[name]
    socket = _socket_by_name(hogltf_node, name)
    if socket is None:
        return None
    return socket.get("value")


def _first_socket_value(hogltf_node, names):
    for name in names:
        value = _socket_value(hogltf_node, name)
        if value is not None:
            return value
    return None


def _number_socket_value(hogltf_node, name):
    value = _socket_value(hogltf_node, name)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _first_number_socket_value(hogltf_node, names):
    for name in names:
        value = _number_socket_value(hogltf_node, name)
        if value is not None:
            return value
    return None


def _int_socket_value(hogltf_node, name):
    value = _number_socket_value(hogltf_node, name)
    if value is None:
        return None
    return int(round(value))


def _socket_by_name(hogltf_node, name):
    for socket in hogltf_node.get("sockets", []):
        if socket.get("name") == name or socket.get("identifier") == name:
            return socket
    return None


def _socket_texture_info(hogltf_node, name):
    socket = _socket_by_name(hogltf_node, name)
    if socket is None:
        return None

    link = socket.get("link")
    if not isinstance(link, dict):
        return None

    image = link.get("image")
    if not isinstance(image, dict):
        return None

    return {
        "socket": name,
        "image": {
            "name": image.get("name", ""),
            "filepath": image.get("filepath", ""),
            "source": image.get("source", ""),
            "colorspace": image.get("colorspace", ""),
        },
    }


def _first_socket_texture_info(hogltf_node, names):
    for name in names:
        texture = _socket_texture_info(hogltf_node, name)
        if texture is not None:
            return texture
    return None


def _deep_update(target, source):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def read_hogltf_node_inputs(blender_material):
    node = find_hogltf_node(blender_material)
    if node is None:
        return None
    group_tree = _node_group_tree(node)

    inputs = {}
    sockets = []
    for socket in node.inputs:
        if not getattr(socket, "enabled", True):
            continue

        socket_value = _socket_effective_value(socket)
        socket_metadata = _socket_metadata(socket, group_tree)
        socket_description = _socket_description(socket, group_tree)
        inputs[socket.name] = socket_value
        sockets.append({
            "name": socket.name,
            "identifier": getattr(socket, "identifier", socket.name),
            "type": getattr(socket, "bl_socket_idname", getattr(socket, "type", "")),
            "description": socket_description,
            "metadata": socket_metadata,
            "priority": socket_metadata.get("priority", ""),
            "target": socket_metadata.get("target", ""),
            "group": socket_metadata.get("group", ""),
            "role": socket_metadata.get("role", ""),
            "blend": socket_metadata.get("blend", ""),
            "min": _json_value(_socket_attr(socket, group_tree, "min_value")),
            "max": _json_value(_socket_attr(socket, group_tree, "max_value")),
            "linked": bool(getattr(socket, "is_linked", False)),
            "value": socket_value,
            "link": _socket_link_info(socket),
        })

    return {
        "node": node.name,
        "nodeLabel": node.label,
        "nodeGroup": _node_group_name(node),
        "nodeGroupContract": _custom_property_value(group_tree, HOGLTF_CONTRACT_GROUP_PROPERTY) if group_tree is not None else None,
        "nodeGroupVariant": _custom_property_value(group_tree, "HoLilToonVariant") if group_tree is not None else "",
        "inputs": inputs,
        "sockets": sockets,
    }


def _find_active_output_hogltf_node(node_tree):
    for node in node_tree.nodes:
        if getattr(node, "type", "") != "OUTPUT_MATERIAL":
            continue
        if not getattr(node, "is_active_output", True):
            continue

        surface = node.inputs.get("Surface")
        if surface is None or not getattr(surface, "is_linked", False):
            continue

        found = _find_hogltf_node_upstream(surface, set())
        if found is not None:
            return found

    return None


def _find_hogltf_node_upstream(socket, visited):
    for link in getattr(socket, "links", []):
        from_node = link.from_node
        node_id = id(from_node)
        if node_id in visited:
            continue
        visited.add(node_id)

        if _is_hogltf_group_node(from_node):
            return from_node

        for input_socket in getattr(from_node, "inputs", []):
            if not getattr(input_socket, "is_linked", False):
                continue
            found = _find_hogltf_node_upstream(input_socket, visited)
            if found is not None:
                return found

    return None


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


def _socket_effective_value(socket):
    linked_value = _socket_linked_constant_value(socket)
    if linked_value is not None:
        return linked_value
    return _socket_default_value(socket)


def _socket_default_value(socket):
    if not hasattr(socket, "default_value"):
        return None
    return _json_value(socket.default_value)


def _socket_linked_constant_value(socket):
    if not getattr(socket, "is_linked", False):
        return None

    links = getattr(socket, "links", [])
    if len(links) == 0:
        return None

    return _link_constant_value(links[0])


def _link_constant_value(link):
    from_node = getattr(link, "from_node", None)
    if from_node is None:
        return None

    from_node_type = getattr(from_node, "bl_idname", getattr(from_node, "type", ""))
    if from_node_type == "ShaderNodeRGB":
        color_socket = getattr(from_node, "outputs", {}).get("Color")
        return _socket_default_value(color_socket)

    if from_node_type == "ShaderNodeValue":
        value_socket = getattr(from_node, "outputs", {}).get("Value")
        return _socket_default_value(value_socket)

    return None


def _socket_description(socket, group_tree):
    own_description = getattr(socket, "description", "")
    if isinstance(own_description, str) and own_description.strip() != "":
        return own_description

    interface_socket = _group_interface_socket(group_tree, socket)
    if interface_socket is None:
        return ""
    return getattr(interface_socket, "description", "") or ""


def _socket_metadata(socket, group_tree):
    description = _socket_description(socket, group_tree)
    metadata = {}
    if not isinstance(description, str) or description.strip() == "":
        return metadata

    for part in description.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        if key == "":
            continue
        metadata[key] = value.strip()
    return metadata


def _socket_attr(socket, group_tree, attr_name):
    value = getattr(socket, attr_name, None)
    if value is not None:
        return value

    interface_socket = _group_interface_socket(group_tree, socket)
    if interface_socket is None:
        return None
    return getattr(interface_socket, attr_name, None)


def _group_interface_socket(group_tree, socket):
    if group_tree is None:
        return None

    socket_name = getattr(socket, "name", "")
    socket_identifier = getattr(socket, "identifier", socket_name)
    interface = getattr(group_tree, "interface", None)
    if interface is None:
        return None

    for item in getattr(interface, "items_tree", []):
        if getattr(item, "item_type", "") != "SOCKET":
            continue
        if getattr(item, "in_out", "") != "INPUT":
            continue
        if getattr(item, "name", "") == socket_name or getattr(item, "identifier", "") == socket_identifier:
            return item

    return None


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

    constant_value = _link_constant_value(link)
    if constant_value is not None:
        info["value"] = constant_value
        info["valueSource"] = "constantNode"

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
