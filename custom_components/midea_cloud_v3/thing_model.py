"""Parser for Midea IoT Thing-Model (midea-iot-spec-v1) JSON definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PropertySpec:
    """Normalized specification of a thing-model property."""

    module: str
    code: str
    key: str
    title: str
    data_type: str
    op: tuple[str, ...]
    minimum: float | None = None
    maximum: float | None = None
    precision: float | None = None
    unit: str | None = None
    value_to_code: dict[Any, str] = field(default_factory=dict)
    code_to_value: dict[str, Any] = field(default_factory=dict)
    value_to_label: dict[Any, str] = field(default_factory=dict)
    label_to_value: dict[str, Any] = field(default_factory=dict)

    @property
    def readable(self) -> bool:
        return "read" in self.op

    @property
    def writable(self) -> bool:
        return "write" in self.op


@dataclass(frozen=True, slots=True)
class ActionSpec:
    """Normalized specification of a thing-model action."""

    module: str
    code: str
    key: str
    title: str
    input_keys: tuple[str, ...] = ()


@dataclass(slots=True)
class ParsedThingModel:
    """Parsed thing-model instance."""

    spid: str
    version: str
    category: str
    title: str
    modules: tuple[str, ...]
    properties: dict[str, PropertySpec] = field(default_factory=dict)
    actions: dict[str, ActionSpec] = field(default_factory=dict)

    def has_module(self, module_code: str) -> bool:
        return module_code in self.modules

    def module_properties(self, module_code: str) -> dict[str, PropertySpec]:
        return {
            spec.code: spec
            for spec in self.properties.values()
            if spec.module == module_code
        }


def _to_float(val: Any) -> float | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def parse_thing_model(
    spid: str,
    spec_json: dict[str, Any],
    *,
    version: str = "",
) -> ParsedThingModel:
    """Parse a Midea midea-iot-spec-v1 JSON document into a ParsedThingModel."""
    metadata = spec_json.get("metadata") or {}
    category = str(metadata.get("category") or "")
    title = str(spec_json.get("title") or "")
    ver = version or str(metadata.get("version") or "")

    raw_modules = spec_json.get("modules") or {}
    module_names: list[str] = []
    properties: dict[str, PropertySpec] = {}
    actions: dict[str, ActionSpec] = {}

    for m_code, m_obj in raw_modules.items():
        if not isinstance(m_obj, dict):
            continue
        module_names.append(m_code)

        for p_code, p_obj in (m_obj.get("properties") or {}).items():
            if not isinstance(p_obj, dict):
                continue
            key = f"{m_code}.{p_code}"
            op = tuple(str(x) for x in (p_obj.get("op") or ()))

            val_to_code: dict[Any, str] = {}
            code_to_val: dict[str, Any] = {}
            val_to_label: dict[Any, str] = {}
            label_to_val: dict[str, Any] = {}

            for item in p_obj.get("enum") or []:
                if not isinstance(item, dict) or "value" not in item:
                    continue
                val = item["value"]
                e_code = str(item.get("code") if item.get("code") is not None else val)
                desc = str(item.get("description") or e_code)
                val_to_code[val] = e_code
                code_to_val[e_code] = val
                val_to_label[val] = desc
                label_to_val[desc] = val

            properties[key] = PropertySpec(
                module=m_code,
                code=p_code,
                key=key,
                title=str(p_obj.get("title") or p_code),
                data_type=str(p_obj.get("type") or ""),
                op=op,
                minimum=_to_float(p_obj.get("minimum")),
                maximum=_to_float(p_obj.get("maximum")),
                precision=_to_float(p_obj.get("precision")),
                unit=p_obj.get("unit"),
                value_to_code=val_to_code,
                code_to_value=code_to_val,
                value_to_label=val_to_label,
                label_to_value=label_to_val,
            )

        for a_code, a_obj in (m_obj.get("actions") or {}).items():
            if not isinstance(a_obj, dict):
                continue
            a_key = f"{m_code}.{a_code}"
            raw_in = a_obj.get("input") or {}
            in_keys = tuple(raw_in.keys()) if isinstance(raw_in, dict) else ()
            actions[a_key] = ActionSpec(
                module=m_code,
                code=a_code,
                key=a_key,
                title=str(a_obj.get("title") or a_code),
                input_keys=in_keys,
            )

    return ParsedThingModel(
        spid=str(spid),
        version=ver,
        category=category,
        title=title,
        modules=tuple(module_names),
        properties=properties,
        actions=actions,
    )
