"""Tests for Midea Thing-Model parser."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

TM_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "custom_components"
    / "midea_cloud_v3"
    / "thing_model.py"
)
SPEC = importlib.util.spec_from_file_location("midea_thing_model", TM_PATH)
assert SPEC and SPEC.loader
tm = importlib.util.module_from_spec(SPEC)
sys.modules["midea_thing_model"] = tm
SPEC.loader.exec_module(tm)


class TestThingModelParser(unittest.TestCase):
    """Verify parsing of real Midea midea-iot-spec-v1 payloads."""

    def test_parse_electric_curtain(self) -> None:
        raw = {
            "title": "电动窗帘",
            "metadata": {"category": "electric-curtain", "version": "v6"},
            "modules": {
                "electricCurtain": {
                    "properties": {
                        "targetOpeningPercentage": {
                            "title": "目标打开百分比",
                            "type": "uint8",
                            "op": ["write"],
                            "minimum": 0,
                            "maximum": 100,
                            "precision": 1,
                            "unit": "percentage",
                        },
                        "currentOpeningPercentage": {
                            "title": "当前打开百分比",
                            "type": "uint8",
                            "op": ["read", "notify"],
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "motorSpeed": {
                            "title": "电机转速",
                            "type": "uint8",
                            "op": ["read", "write", "notify"],
                            "enum": [
                                {"code": "level1", "value": 1, "description": "1档"},
                                {"code": "level2", "value": 2, "description": "2档"},
                            ],
                        },
                    },
                    "actions": {
                        "open": {"title": "打开", "input": {}},
                        "close": {"title": "关闭", "input": {}},
                        "pause": {"title": "暂停", "input": {}},
                    },
                }
            },
        }
        parsed = tm.parse_thing_model("10004744", raw)
        self.assertTrue(parsed.has_module("electricCurtain"))
        self.assertIn("electricCurtain.open", parsed.actions)
        target = parsed.properties["electricCurtain.targetOpeningPercentage"]
        self.assertTrue(target.writable)
        self.assertFalse(target.readable)
        self.assertEqual(target.maximum, 100.0)
        speed = parsed.properties["electricCurtain.motorSpeed"]
        self.assertEqual(speed.label_to_value["2档"], 2)

    def test_parse_two_gang_wall_switch_and_light(self) -> None:
        raw = {
            "title": "智能开关二键",
            "metadata": {"category": "wall-switch", "version": "v10"},
            "modules": {
                "wallSwitch1": {
                    "properties": {"power": {"title": "开关", "type": "bool", "op": ["read", "write"]}}
                },
                "wallSwitch2": {
                    "properties": {"power": {"title": "开关", "type": "bool", "op": ["read", "write"]}}
                },
            },
        }
        parsed = tm.parse_thing_model("10003726", raw)
        self.assertEqual(parsed.modules, ("wallSwitch1", "wallSwitch2"))
        self.assertTrue(parsed.properties["wallSwitch1.power"].writable)
        self.assertTrue(parsed.properties["wallSwitch2.power"].writable)


if __name__ == "__main__":
    unittest.main()
