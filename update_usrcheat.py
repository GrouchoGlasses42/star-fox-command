#!/usr/bin/env python3
"""Install the four Star Fox control variants in an existing cheat database."""

import argparse
from pathlib import Path
import struct

from generate_patch import VARIANTS, roms_info


NAMES = tuple(variant.name for variant in VARIANTS)
OLD_NAME = "Revised CPad Patch"


def read_index(data):
    if data[:12] != b"R4 CheatCode":
        raise ValueError("Not an R4 cheat database")
    entries = []
    position = 0x100
    while position + 16 <= len(data):
        code, crc, offset, reserved = struct.unpack_from("<4sIII", data, position)
        if code == bytes(4) and crc == offset == reserved == 0:
            break
        entries.append((f"{code.decode('ascii')}-{crc:08X}", offset))
        position += 16
    else:
        raise ValueError("The database index has no terminator")
    offsets = [offset for _, offset in entries]
    if not offsets or offsets != sorted(set(offsets)) or offsets[0] < position + 16:
        raise ValueError("The database index is invalid")
    return entries


def game_blocks(data):
    entries = read_index(data)
    blocks = {}
    for i, (game_id, start) in enumerate(entries):
        end = entries[i + 1][1] if i + 1 < len(entries) else len(data)
        if not start < end <= len(data):
            raise ValueError(f"{game_id}: invalid game extent")
        if game_id in blocks and game_id in roms_info:
            raise ValueError(f"Duplicate game ID: {game_id}")
        blocks[game_id] = data[start:end]
    return entries, blocks


def attribute_offset(block):
    return (block.index(0) + 4) & ~3


def find_records(block, name):
    marker = name.encode() + b"\0"
    position = attribute_offset(block) + 0x24
    matches = []
    while True:
        found = block.find(marker, position)
        if found < 0:
            return matches
        start = found - 4
        if start >= 0 and start % 4 == 0:
            attributes = struct.unpack_from("<I", block, start)[0]
            end = start + 4 + (attributes & 0xFFFFFF) * 4
            if not attributes & 0xF0000000 and found + len(marker) <= end <= len(block):
                matches.append((start, end))
        position = found + len(marker)


def required_record(block, name):
    found = find_records(block, name)
    if len(found) != 1:
        raise ValueError(f"Expected one {name!r} record; found {len(found)}")
    start, end = found[0]
    return block[start:end]


def update_database(original, patch):
    entries, blocks = game_blocks(original)
    patch_entries, patch_blocks = game_blocks(patch)
    if len(patch_entries) != len(roms_info) or set(patch_blocks) != set(roms_info):
        raise ValueError("The patch database has unexpected game IDs")
    if not set(patch_blocks) <= set(blocks):
        raise ValueError("The target database does not contain all supported games")
    output = bytearray(original[:entries[0][1]])
    changed = []
    for index, (game_id, start) in enumerate(entries):
        # Some large databases contain duplicate IDs for unrelated games.
        # Copy each indexed extent, so distinct records remain intact.
        end = entries[index + 1][1] if index + 1 < len(entries) else len(original)
        block = original[start:end]
        if game_id in patch_blocks:
            source = patch_blocks[game_id]
            if struct.unpack_from("<I", source, attribute_offset(source))[0] != 4:
                raise ValueError(f"{game_id}: expected four patch records")
            replacements = [required_record(source, name) for name in NAMES]
            for i, record in enumerate(replacements):
                enabled = bool(struct.unpack_from("<I", record)[0] & 0x01000000)
                if enabled != (i == 0):
                    raise ValueError(f"{game_id}: unexpected default selection")
            old = find_records(block, OLD_NAME)
            current = [match for name in NAMES for match in find_records(block, name)]
            if len(old) == 1 and not current:
                remove = old
            elif not old and len(current) == 4 and all(len(find_records(block, name)) == 1 for name in NAMES):
                remove = current
            else:
                raise ValueError(f"{game_id}: expected the old patch or all four variants")
            remove.sort()
            rebuilt = bytearray(block[:remove[0][0]])
            rebuilt.extend(b"".join(replacements))
            previous = remove[0][0]
            for start, end in remove:
                rebuilt.extend(block[previous:start])
                previous = end
            rebuilt.extend(block[previous:])
            attributes_position = attribute_offset(block)
            attributes = struct.unpack_from("<I", block, attributes_position)[0]
            count = (attributes & 0xFFFFFF) + 4 - len(remove)
            struct.pack_into("<I", rebuilt, attributes_position,
                             (attributes & 0xFF000000) | count)
            if rebuilt != block:
                changed.append(game_id)
            block = bytes(rebuilt)
        struct.pack_into("<I", output, 0x100 + index * 16 + 8, len(output))
        output.extend(block)
    return bytes(output), changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--patch", type=Path,
                        default=Path(__file__).resolve().parent / "action_replay_codes/usrcheat.dat")
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    original = args.database.read_bytes()
    updated, changed = update_database(original, args.patch.read_bytes())
    if updated != original:
        # Refuse to overwrite a previous backup.
        with args.backup.open("xb") as backup:
            backup.write(original)
        args.database.write_bytes(updated)
    print(f"Updated {len(changed)} games; {len(read_index(updated))} games total")


if __name__ == "__main__":
    main()
