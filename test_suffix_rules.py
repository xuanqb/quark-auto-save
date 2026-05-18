#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

import quark_auto_save as qas


class SuffixRuleTests(unittest.TestCase):
    def setUp(self):
        self.original_config = qas.CONFIG_DATA.copy()
        qas.CONFIG_DATA = {
            "magic_regex": qas.MAGIC_REGEX,
            "suffix_rules": [],
        }

    def tearDown(self):
        qas.CONFIG_DATA = self.original_config

    def test_normalize_suffix_rules(self):
        rules = qas.normalize_suffix_rules(
            [
                {"from": "7Z", "to": " mp4 "},
                {"from": "", "to": ""},
                {"from": ".Tar.Gz", "to": ".MP4"},
            ],
            strict=True,
        )
        self.assertEqual(
            rules,
            [
                {"from": ".7z", "to": ".mp4"},
                {"from": ".tar.gz", "to": ".mp4"},
            ],
        )

    def test_normalize_suffix_rules_strict_validation(self):
        with self.assertRaises(ValueError):
            qas.normalize_suffix_rules([{"from": ".7z", "to": ""}], strict=True)

    def test_task_disabled_returns_no_effective_rules(self):
        qas.CONFIG_DATA["suffix_rules"] = [{"from": ".7z", "to": ".mp4"}]
        task = {
            "enable_suffix_replacement": False,
            "suffix_rules": [{"from": ".mkv", "to": ".mp4"}],
        }
        self.assertEqual(qas.get_effective_suffix_rules(task), [])

    def test_effective_rules_merge_with_override(self):
        qas.CONFIG_DATA["suffix_rules"] = [
            {"from": ".7z", "to": ".mp4"},
            {"from": ".mkv", "to": ".avi"},
        ]
        task = {
            "enable_suffix_replacement": True,
            "suffix_rules": [
                {"from": ".mkv", "to": ".mp4"},
                {"from": ".ts", "to": ".mp4"},
            ],
        }
        self.assertEqual(
            qas.get_effective_suffix_rules(task),
            [
                {"from": ".7z", "to": ".mp4"},
                {"from": ".mkv", "to": ".mp4"},
                {"from": ".ts", "to": ".mp4"},
            ],
        )

    def test_apply_suffix_rules_case_insensitive_and_longest_first(self):
        rules = [
            {"from": ".gz", "to": ".zip"},
            {"from": ".tar.gz", "to": ".mp4"},
        ]
        self.assertEqual(qas.apply_suffix_rules("video.TAR.GZ", rules), "video.mp4")

    def test_build_target_name_applies_all_rules_for_file(self):
        qas.CONFIG_DATA["suffix_rules"] = [{"from": ".7z", "to": ".mp4"}]
        task = {
            "taskname": "测试任务",
            "pattern": r"^第(\d+)\.(7z)$",
            "replace": r"S01E\1.\2",
            "enable_suffix_replacement": True,
            "suffix_rules": [],
        }
        self.assertEqual(
            qas.build_target_name(task, "第01.7z", is_dir=False),
            "S01E01.mp4",
        )

    def test_build_target_name_skips_suffix_rules_for_directory(self):
        qas.CONFIG_DATA["suffix_rules"] = [{"from": ".7z", "to": ".mp4"}]
        task = {
            "taskname": "测试任务",
            "pattern": r"^资料\.(7z)$",
            "replace": r"目录.\1",
            "enable_suffix_replacement": True,
            "suffix_rules": [],
        }
        self.assertEqual(
            qas.build_target_name(task, "资料.7z", is_dir=True),
            "目录.7z",
        )

    def test_normalize_config_data_adds_defaults(self):
        config = qas.normalize_config_data({"tasklist": [{"taskname": "A"}]})
        self.assertEqual(config["suffix_rules"], [])
        self.assertFalse(config["tasklist"][0]["enable_suffix_replacement"])
        self.assertEqual(config["tasklist"][0]["suffix_rules"], [])

    def test_filename_rules_format_hyphen_date(self):
        self.assertEqual(
            qas.apply_filename_rules("2026-05-18 第1期上.mp4"),
            "20260518 第1期上.mp4",
        )

    def test_filename_rules_format_single_digit_hyphen_date(self):
        self.assertEqual(
            qas.apply_filename_rules("2026-5-8 第1期上.mp4"),
            "20260508 第1期上.mp4",
        )


if __name__ == "__main__":
    unittest.main()
