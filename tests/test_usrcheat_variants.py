"""Validate variant names, database selection, and database migration."""

from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from generate_patch import VARIANTS, generate_usrcheat_dat_file_with_ar_codes, roms_info
from update_usrcheat import (
    NAMES, OLD_NAME, attribute_offset, find_records, game_blocks,
    required_record, update_database,
)


def code_words(record):
    name_end = record.index(0, 4)
    description_end = record.index(0, name_end + 1)
    count_position = (description_end + 4) & ~3
    count = struct.unpack_from("<I", record, count_position)[0]
    if count_position + 4 + count * 4 != len(record):
        raise ValueError("Invalid cheat record extent")
    return struct.unpack_from(f"<{count}I", record, count_position + 4)


class CheatDatabaseTest(unittest.TestCase):
    def test_generated_database_matches_all_twelve_text_files(self):
        patch = (ROOT / "action_replay_codes/usrcheat.dat").read_bytes()
        _, blocks = game_blocks(patch)
        self.assertEqual(set(blocks), set(roms_info))
        self.assertEqual(NAMES, (
            "3DS - Normal - L/R", "3DS - Inverted - L/R",
            "3DS - Normal - A", "3DS - Inverted - A",
        ))
        for game_id, block in blocks.items():
            self.assertEqual(struct.unpack_from("<I", block, attribute_offset(block))[0], 4)
            self.assertEqual(find_records(block, OLD_NAME), [])
            for index, variant in enumerate(VARIANTS):
                with self.subTest(game=game_id, variant=variant.name):
                    record = required_record(block, variant.name)
                    enabled = bool(struct.unpack_from("<I", record)[0] & 0x01000000)
                    self.assertEqual(enabled, index == 0)
                    filename = f"{game_id} ({roms_info[game_id].description}).txt"
                    lines = (ROOT / "action_replay_codes" / variant.directory / filename).read_text().splitlines()
                    self.assertEqual(len(lines), 429)
                    self.assertTrue(all(re.fullmatch(r"[0-9A-F]{8} [0-9A-F]{8}", line) for line in lines))
                    expected = tuple(int(word, 16) for line in lines for word in line.split())
                    self.assertEqual(code_words(record), expected)
        self.assertEqual(len(list((ROOT / "action_replay_codes").rglob("*.txt"))), 12)

    def test_migration_preserves_other_cheats_and_is_repeatable(self):
        fixture = {
            "TEST-11223344": [{"name": "Other game", "code": "12345678 90ABCDEF"}],
            **{game_id: [
                {"name": "Before", "code": "12345678 90ABCDEF", "enabled": True},
                {"name": OLD_NAME, "code": "11111111 22222222", "enabled": True},
                {"name": "After", "code": "33333333 44444444"},
            ] for game_id in roms_info},
        }
        original = generate_usrcheat_dat_file_with_ar_codes(fixture)
        patch = (ROOT / "action_replay_codes/usrcheat.dat").read_bytes()
        updated, changed = update_database(original, patch)
        self.assertEqual(set(changed), set(roms_info))
        old_entries, old_blocks = game_blocks(original)
        new_entries, new_blocks = game_blocks(updated)
        self.assertEqual([game for game, _ in old_entries], [game for game, _ in new_entries])
        self.assertEqual(old_blocks["TEST-11223344"], new_blocks["TEST-11223344"])
        for game_id in roms_info:
            before, after = old_blocks[game_id], new_blocks[game_id]
            self.assertEqual(struct.unpack_from("<I", after, attribute_offset(after))[0], 6)
            for name in ("Before", "After"):
                self.assertEqual(required_record(before, name), required_record(after, name))
            self.assertEqual(find_records(after, OLD_NAME), [])
        repeated, changed = update_database(updated, patch)
        self.assertEqual(repeated, updated)
        self.assertEqual(changed, [])

    def test_migration_preserves_distinct_records_with_duplicate_game_ids(self):
        fixture = {
            "TEST-11223344": [{"name": "First record", "code": "12345678 90ABCDEF"}],
            "COPY-55667788": [{"name": "Second record", "code": "11111111 22222222"}],
            **{game_id: [{"name": OLD_NAME, "code": "33333333 44444444"}]
               for game_id in roms_info},
        }
        original = generate_usrcheat_dat_file_with_ar_codes(fixture)
        original[0x110:0x118] = original[0x100:0x108]
        patch = (ROOT / "action_replay_codes/usrcheat.dat").read_bytes()
        updated, changed = update_database(original, patch)
        self.assertEqual(set(changed), set(roms_info))
        old_index, _ = game_blocks(original)
        new_index, _ = game_blocks(updated)
        for i in (0, 1):
            self.assertEqual(old_index[i][0], new_index[i][0])
            self.assertEqual(original[old_index[i][1]:old_index[i + 1][1]],
                             updated[new_index[i][1]:new_index[i + 1][1]])


if __name__ == "__main__":
    unittest.main()
