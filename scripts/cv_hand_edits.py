from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

DEFAULT_HAND_EDITS_PATH = Path("data/source/cv_hand_edits.yaml")

RESOLUTION_KEEP_MANUAL = "keep_manual"
RESOLUTION_ACCEPT_CV = "accept_cv"
VALID_RESOLUTIONS = {RESOLUTION_KEEP_MANUAL, RESOLUTION_ACCEPT_CV}


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    return value


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def values_conflict(old_value: Any, new_value: Any) -> bool:
    if not (_has_value(old_value) and _has_value(new_value)):
        return False
    return _normalize_value(old_value) != _normalize_value(new_value)


def conflict_key(conflict: dict) -> str:
    output = str(conflict.get("output") or "")
    field = str(conflict.get("field") or "")
    section = conflict.get("section")
    if section is not None and conflict.get("id"):
        return f"{output}|{section}|{conflict['id']}|{field}" if field else f"{output}|{section}|{conflict['id']}"
    if conflict.get("id"):
        return f"{output}|{conflict['id']}|{field}" if field else f"{output}|{conflict['id']}"
    if section is not None and conflict.get("index") is not None:
        idx = conflict["index"]
        return f"{output}|{section}|{idx}|{field}" if field else f"{output}|{section}|{idx}"
    if section is not None:
        return f"{output}|{section}"
    return output or "unknown"


def load_hand_edits(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def save_hand_edits(path: Path, registry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(registry, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _registry_branch(registry: dict, output: str) -> dict:
    branch = registry.setdefault(output, {})
    if not isinstance(branch, dict):
        branch = {}
        registry[output] = branch
    return branch


def is_hand_edited(registry: dict, output: str, locator: str, field: str = "") -> bool:
    branch = registry.get(output) or {}
    if not isinstance(branch, dict):
        return False
    node = branch.get(locator)
    if field:
        if isinstance(node, dict):
            return bool(node.get(field))
        return False
    return bool(node)


def mark_hand_edited(registry: dict, output: str, locator: str, field: str = "") -> None:
    branch = _registry_branch(registry, output)
    if field:
        entry = branch.setdefault(locator, {})
        if not isinstance(entry, dict):
            entry = {}
            branch[locator] = entry
        entry[field] = True
        return
    branch[locator] = True


def load_conflict_approvals(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    approvals: dict[str, str] = {}
    items = data.get("approvals") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return approvals
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or item.get("conflict_key") or "").strip()
        resolution = str(item.get("resolution") or "").strip()
        if key and resolution in VALID_RESOLUTIONS:
            approvals[key] = resolution
    return approvals


def annotate_conflicts(conflicts: list[dict], registry: dict) -> list[dict]:
    annotated: list[dict] = []
    for conflict in conflicts:
        item = dict(conflict)
        item["key"] = conflict_key(conflict)
        locator, field = _locator_from_conflict(conflict)
        item["hand_edited"] = is_hand_edited(registry, str(conflict.get("output") or ""), locator, field)
        annotated.append(item)
    return annotated


def _locator_from_conflict(conflict: dict) -> tuple[str, str]:
    output = str(conflict.get("output") or "")
    field = str(conflict.get("field") or "")
    if conflict.get("id") and conflict.get("section"):
        return f"{conflict['section']}|{conflict['id']}", field
    if conflict.get("id"):
        return str(conflict["id"]), field
    section = conflict.get("section")
    if section is not None and conflict.get("index") is not None:
        return f"{section}|{conflict['index']}", field
    if section is not None:
        return str(section), field
    return output, field


def split_conflicts(conflicts: list[dict], registry: dict) -> tuple[list[dict], list[dict]]:
    preserved: list[dict] = []
    pending: list[dict] = []
    for conflict in annotate_conflicts(conflicts, registry):
        if conflict.get("hand_edited"):
            preserved.append(conflict)
        else:
            pending.append(conflict)
    return preserved, pending


def merge_list_items(
    *,
    output_name: str,
    old_items: list[dict],
    new_items: list[dict],
    fields: tuple[str, ...],
    registry: dict,
    approvals: dict[str, str],
) -> tuple[list[dict], list[dict], list[dict], dict]:
    old_by_id = {str(item.get("id") or ""): dict(item) for item in old_items if item.get("id")}
    new_by_id = {str(item.get("id") or ""): dict(item) for item in new_items if item.get("id")}
    merged: list[dict] = []
    preserved_conflicts: list[dict] = []
    pending_conflicts: list[dict] = []

    for item_id, new_item in new_by_id.items():
        merged_item = dict(new_item)
        old_item = old_by_id.get(item_id)
        if not old_item:
            merged.append(merged_item)
            continue
        for field in fields:
            old_value = old_item.get(field)
            new_value = new_item.get(field)
            if not values_conflict(old_value, new_value):
                continue
            conflict = {
                "output": output_name,
                "kind": output_name.rstrip("s"),
                "id": item_id,
                "field": field,
                "old": old_value,
                "new": new_value,
            }
            key = conflict_key(conflict)
            locator = item_id
            hand_edited = is_hand_edited(registry, output_name, locator, field)
            conflict["key"] = key
            conflict["hand_edited"] = hand_edited
            resolution = approvals.get(key)

            if hand_edited or resolution == RESOLUTION_KEEP_MANUAL:
                merged_item[field] = old_value
                preserved_conflicts.append(conflict)
                if resolution == RESOLUTION_KEEP_MANUAL:
                    mark_hand_edited(registry, output_name, locator, field)
            elif resolution == RESOLUTION_ACCEPT_CV:
                merged_item[field] = new_value
                mark_hand_edited(registry, output_name, locator, field)
            else:
                merged_item[field] = old_value
                pending_conflicts.append(conflict)
        merged.append(merged_item)

    for item_id, old_item in old_by_id.items():
        if item_id not in new_by_id:
            merged.append(dict(old_item))

    merged.sort(key=lambda x: (str(x.get("date") or ""), int(x.get("year") or 0), str(x.get("title") or "")), reverse=True)
    return merged, preserved_conflicts, pending_conflicts, registry


def merge_nested_dict(
    *,
    output_name: str,
    old_data: dict,
    new_data: dict,
    registry: dict,
    approvals: dict[str, str],
    item_key: str = "name",
) -> tuple[dict, list[dict], list[dict], dict]:
    merged = {k: v for k, v in new_data.items()}
    preserved_conflicts: list[dict] = []
    pending_conflicts: list[dict] = []

    for section in sorted(set(old_data) | set(new_data)):
        old_section = old_data.get(section)
        new_section = new_data.get(section)
        if isinstance(old_section, list) and isinstance(new_section, list):
            if all(isinstance(x, dict) and x.get(item_key) for x in new_section):
                old_by_key = {
                    str(item.get(item_key) or "").lower(): item
                    for item in old_section
                    if isinstance(item, dict) and item.get(item_key)
                }
                out_list: list[dict] = []
                for new_item in new_section:
                    if not isinstance(new_item, dict):
                        out_list.append(new_item)
                        continue
                    merged_item = dict(new_item)
                    key_name = str(new_item.get(item_key) or "")
                    old_item = old_by_key.get(key_name.lower())
                    if old_item:
                        for field in sorted(set(old_item) | set(new_item)):
                            if field == "profile_url":
                                continue
                            old_value = old_item.get(field)
                            new_value = new_item.get(field)
                            if not values_conflict(old_value, new_value):
                                continue
                            conflict = {
                                "output": output_name,
                                "kind": "section_item_field",
                                "section": section,
                                "id": key_name,
                                "field": field,
                                "old": old_value,
                                "new": new_value,
                            }
                            ckey = conflict_key(conflict)
                            locator = f"{section}|{key_name}"
                            hand_edited = is_hand_edited(registry, output_name, locator, field)
                            conflict["key"] = ckey
                            conflict["hand_edited"] = hand_edited
                            resolution = approvals.get(ckey)
                            if hand_edited or resolution == RESOLUTION_KEEP_MANUAL:
                                merged_item[field] = old_value
                                preserved_conflicts.append(conflict)
                                if resolution == RESOLUTION_KEEP_MANUAL:
                                    mark_hand_edited(registry, output_name, locator, field)
                            elif resolution == RESOLUTION_ACCEPT_CV:
                                merged_item[field] = new_value
                                mark_hand_edited(registry, output_name, locator, field)
                            else:
                                merged_item[field] = old_value
                                pending_conflicts.append(conflict)
                    out_list.append(merged_item)
                merged[section] = out_list
                continue

            limit = min(len(old_section), len(new_section))
            out_list = []
            for idx in range(max(len(old_section), len(new_section))):
                if idx >= len(new_section):
                    out_list.append(old_section[idx])
                    continue
                if idx >= len(old_section):
                    out_list.append(new_section[idx])
                    continue
                old_item = old_section[idx]
                new_item = new_section[idx]
                if isinstance(old_item, dict) and isinstance(new_item, dict):
                    merged_item = dict(new_item)
                    for field in sorted(set(old_item) | set(new_item)):
                        old_value = old_item.get(field)
                        new_value = new_item.get(field)
                        if not values_conflict(old_value, new_value):
                            continue
                        conflict = {
                            "output": output_name,
                            "kind": "section_item_field",
                            "section": section,
                            "index": idx,
                            "field": field,
                            "old": old_value,
                            "new": new_value,
                        }
                        ckey = conflict_key(conflict)
                        locator = f"{section}|{idx}"
                        hand_edited = is_hand_edited(registry, output_name, locator, field)
                        conflict["key"] = ckey
                        conflict["hand_edited"] = hand_edited
                        resolution = approvals.get(ckey)
                        if hand_edited or resolution == RESOLUTION_KEEP_MANUAL:
                            merged_item[field] = old_value
                            preserved_conflicts.append(conflict)
                            if resolution == RESOLUTION_KEEP_MANUAL:
                                mark_hand_edited(registry, output_name, locator, field)
                        elif resolution == RESOLUTION_ACCEPT_CV:
                            merged_item[field] = new_value
                            mark_hand_edited(registry, output_name, locator, field)
                        else:
                            merged_item[field] = old_value
                            pending_conflicts.append(conflict)
                    out_list.append(merged_item)
                elif values_conflict(old_item, new_item):
                    conflict = {
                        "output": output_name,
                        "kind": "section_item",
                        "section": section,
                        "index": idx,
                        "old": old_item,
                        "new": new_item,
                    }
                    ckey = conflict_key(conflict)
                    locator = f"{section}|{idx}"
                    hand_edited = is_hand_edited(registry, output_name, locator)
                    conflict["key"] = ckey
                    conflict["hand_edited"] = hand_edited
                    resolution = approvals.get(ckey)
                    if hand_edited or resolution == RESOLUTION_KEEP_MANUAL:
                        out_list.append(old_item)
                        preserved_conflicts.append(conflict)
                        if resolution == RESOLUTION_KEEP_MANUAL:
                            mark_hand_edited(registry, output_name, locator)
                    elif resolution == RESOLUTION_ACCEPT_CV:
                        out_list.append(new_item)
                        mark_hand_edited(registry, output_name, locator)
                    else:
                        out_list.append(old_item)
                        pending_conflicts.append(conflict)
                else:
                    out_list.append(new_item)
            merged[section] = out_list
            continue

        if values_conflict(old_section, new_section):
            conflict = {
                "output": output_name,
                "kind": "section",
                "section": section,
                "old": old_section,
                "new": new_section,
            }
            ckey = conflict_key(conflict)
            locator = str(section)
            hand_edited = is_hand_edited(registry, output_name, locator)
            conflict["key"] = ckey
            conflict["hand_edited"] = hand_edited
            resolution = approvals.get(ckey)
            if hand_edited or resolution == RESOLUTION_KEEP_MANUAL:
                merged[section] = old_section
                preserved_conflicts.append(conflict)
                if resolution == RESOLUTION_KEEP_MANUAL:
                    mark_hand_edited(registry, output_name, locator)
            elif resolution == RESOLUTION_ACCEPT_CV:
                merged[section] = new_section
                mark_hand_edited(registry, output_name, locator)
            else:
                merged[section] = old_section
                pending_conflicts.append(conflict)

    return merged, preserved_conflicts, pending_conflicts, registry


def resolve_import_data(
    *,
    old_publications: list[dict],
    new_publications: list[dict],
    old_talks: list[dict],
    new_talks: list[dict],
    old_service: dict,
    new_service: dict,
    old_teaching: dict,
    new_teaching: dict,
    old_mentoring: dict,
    new_mentoring: dict,
    pub_fields: tuple[str, ...],
    talk_fields: tuple[str, ...],
    registry: dict,
    approvals: dict[str, str],
) -> dict:
    pubs, pub_preserved, pub_pending, registry = merge_list_items(
        output_name="publications",
        old_items=old_publications,
        new_items=new_publications,
        fields=pub_fields,
        registry=registry,
        approvals=approvals,
    )
    talks, talk_preserved, talk_pending, registry = merge_list_items(
        output_name="talks",
        old_items=old_talks,
        new_items=new_talks,
        fields=talk_fields,
        registry=registry,
        approvals=approvals,
    )
    service, service_preserved, service_pending, registry = merge_nested_dict(
        output_name="service",
        old_data=old_service,
        new_data=new_service,
        registry=registry,
        approvals=approvals,
    )
    teaching, teaching_preserved, teaching_pending, registry = merge_nested_dict(
        output_name="teaching",
        old_data=old_teaching,
        new_data=new_teaching,
        registry=registry,
        approvals=approvals,
    )
    mentoring, mentoring_preserved, mentoring_pending, registry = merge_nested_dict(
        output_name="mentoring",
        old_data=old_mentoring,
        new_data=new_mentoring,
        registry=registry,
        approvals=approvals,
        item_key="name",
    )

    preserved = pub_preserved + talk_preserved + service_preserved + teaching_preserved + mentoring_preserved
    pending = pub_pending + talk_pending + service_pending + teaching_pending + mentoring_pending
    return {
        "publications": pubs,
        "talks": talks,
        "service": service,
        "teaching": teaching,
        "mentoring": mentoring,
        "registry": registry,
        "preserved_conflicts": preserved,
        "pending_conflicts": pending,
    }


def format_conflict_for_review(conflict: dict) -> str:
    key = conflict.get("key") or conflict_key(conflict)
    field = conflict.get("field")
    field_part = f".{field}" if field else ""
    target = conflict.get("id") or conflict.get("section")
    if conflict.get("section") and conflict.get("id"):
        target = f"{conflict['section']} / {conflict['id']}"
    elif conflict.get("section") is not None and conflict.get("index") is not None:
        target = f"{conflict['section']}[{conflict['index']}]"
    hand_tag = " [hand-edited, kept]" if conflict.get("hand_edited") else ""
    old_str = json.dumps(conflict.get("old"), ensure_ascii=False)
    new_str = json.dumps(conflict.get("new"), ensure_ascii=False)
    return (
        f"- `{key}`{hand_tag}\n"
        f"  target: {conflict.get('output')}{field_part} → {target}\n"
        f"  manual: {old_str}\n"
        f"  cv:     {new_str}"
    )


def write_conflict_approvals_template(path: Path, pending: list[dict]) -> None:
    template = {
        "approvals": [
            {
                "key": conflict.get("key") or conflict_key(conflict),
                "resolution": RESOLUTION_KEEP_MANUAL,
                "note": "Use keep_manual to keep your YAML value, or accept_cv to take the CV parser value.",
            }
            for conflict in pending
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
