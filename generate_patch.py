#!/bin/python
from pathlib import Path
import base64
import hashlib
import subprocess
import re
import struct
from collections import defaultdict, namedtuple

tmp_folder_name = "tmp_ndstools"

asm_exe_path = "arm-none-eabi-as"
objcopy_exe_path = "arm-none-eabi-objcopy"
objdump_exe_path = "arm-none-eabi-objdump"

prebuilt_arm7_path = Path(__file__).resolve().parent / "arm7_rtcom_patch/known_good_cpad_transport.b64"
prebuilt_arm7_sha256 = "bf7895010672f5db1a4a860231b5e3b958c65ec871bab288b4b6a9487c086daf"
prebuilt_arm7_size = 0x7A8
prebuilt_update_rtcom_offset = 0x418

ControlVariant = namedtuple('ControlVariant', 'name directory inverted shoot_on_a')
VARIANTS = (
    ControlVariant("3DS - Normal - L/R", "3ds_normal_lr", False, False),
    ControlVariant("3DS - Inverted - L/R", "3ds_inverted_lr", True, False),
    ControlVariant("3DS - Normal - A", "3ds_normal_a", False, True),
    ControlVariant("3DS - Inverted - A", "3ds_inverted_a", True, True),
)
DEFAULT_VARIANT = VARIANTS[0]


RomInfo = namedtuple(
    'RomInfo',
    'arm7_ipc_send_msg, arm7_set_ipc_channel_handler, arm7_rtc_region_start, arm7_vblank_irq_end_address, arm7_rtc_init_function_call, arm9_code_position, arm9_barrel_roll_hook, arm9_shooting_keys_addr, arm9_crackers_dpad_hook, arm9_crackers_dpad_hook_return, arm9_loop_func, arm9_uturn_func, arm9_touch_sample_hook, arm9_touch_sample_func, description')
roms_info = {
    "ASFP-F0E8BD5C": RomInfo(0x037FE9EC, 0x037FEAB8, 0x027F6798, 0x037FBAB4, 0x037F84E0, 0x02000000, 0x022113C2, 0x021CCCF0, 0x021E9434, 0x021E943D, 0x021EE528, 0x021EE550, 0x0203BFAE, 0x0203C068, "Europe v1.0"),
    "ASFJ-70977801": RomInfo(0x037FE9EC, 0x037FEAB8, 0x027F6798, 0x037FBAB4, 0x037F84E0, 0x02000000, 0x022114A6, 0x021CD164, 0x021E9C18, 0x021E9C21, 0x021EED0C, 0x021EED34, 0x0203BF5A, 0x0203C014, "Japan v1.0"),
    "ASFE-F22E6A7D": RomInfo(0x037FE9EC, 0x037FEAB8, 0x027F6798, 0x037FBAB4, 0x037F84E0, 0x02000000, 0x022115BE, 0x021CD250, 0x021E9D34, 0x021E9D3D, 0x021EEE28, 0x021EEE50, 0x0203BF5A, 0x0203C014, "USA v1.0"),
}


def find_function_offset_in_asm_listing(asm_code, func_name):
    asm_func_regexp = r"([a-f0-9]{8}) .+" + func_name + "[^-+].+"
    regexp_func = re.search(asm_func_regexp, asm_code, re.IGNORECASE)
    if regexp_func:
        addr = int(regexp_func.group(1), 16)
    else:
        raise Exception(f"Can't find the function '{func_name}' in the output file")
    return addr


def assemble_arm7_rtcom_patch(rom_signature):
    rom_info = roms_info[rom_signature]
    expected_addresses = (0x037FE9EC, 0x037FEAB8, 0x027F6798, 0x037FBAB4, 0x037F84E0)
    if tuple(rom_info[:5]) != expected_addresses:
        raise ValueError(f"The known-good ARM7 payload is not compatible with {rom_signature}")

    encoded_payload = "".join(prebuilt_arm7_path.read_text().split())
    arm7_patch_bytes = base64.b64decode(encoded_payload, validate=True)
    payload_hash = hashlib.sha256(arm7_patch_bytes).hexdigest()
    if len(arm7_patch_bytes) != prebuilt_arm7_size or payload_hash != prebuilt_arm7_sha256:
        raise ValueError("The known-good ARM7 payload failed validation")

    return prebuilt_update_rtcom_offset, arm7_patch_bytes


def assemble_arm9_patch(rom_signature, asm_filename, extra_defines=()):
    rom_info = roms_info[rom_signature]

    arm9_defines_for_assembler = [
        ("MOVE_RETURN_ADDR", rom_info.arm9_crackers_dpad_hook_return),
        ("LOOP_FUNC_ADDR", rom_info.arm9_loop_func),
        ("UTURN_FUNC_ADDR", rom_info.arm9_uturn_func),
        ("TOUCH_SAMPLE_FUNC_ADDR", rom_info.arm9_touch_sample_func),
        *extra_defines,
    ]
    asm_defines = sum([["--defsym", f"{name}=0x{value:08X}"] for name, value in arm9_defines_for_assembler], [])

    patch_name = asm_filename.upper().split('/')[-1].split('.')[0]
    subprocess.check_output([asm_exe_path, asm_filename, '-o', f'{tmp_folder_name}/{patch_name}.out', *asm_defines])
    subprocess.check_output([objcopy_exe_path, '-Obinary',
                            f'{tmp_folder_name}/{patch_name}.out', f'{tmp_folder_name}/{patch_name}.bin'])

    asm_code = subprocess.check_output([objdump_exe_path, '-d', f'{tmp_folder_name}/{patch_name}.out'], text=True)

    return bytearray(open(f"{tmp_folder_name}/{patch_name}.bin", 'rb').read()), asm_code


def generate_action_replay_code(rom_signature, variant=DEFAULT_VARIANT):
    def ar_code__bulk_write(bin: bytearray, address: int):
        write_size = len(bin)
        padded_bin = bytes(bin)
        if write_size % 8 != 0:
            padded_bin += b'\x00' * (8 - write_size % 8)
        ar_code = f"E{address:07X} {write_size:08X}\n"
        for words in struct.iter_unpack("<II", padded_bin):
            ar_code += f"{words[0]:08X} {words[1]:08X}\n"
        return ar_code

    def instr__arm_b(from_addr, target, link=False, exchange=False):
        offset = target - (from_addr + 8)
        if exchange:  # blx
            instr_type = 0xFA000000 if (offset & 0x2) == 0 else 0xFB000000
            return instr_type | ((offset >> 2) & 0xFFFFFF)
        else:
            instr_type = 0xEB000000 if link else 0xEA000000
            return instr_type | ((offset >> 2) & 0xFFFFFF)

    def instr__thumb_bl(src, target, exchange_instruction_set=False):
        base = (src + 4)
        bits_to_exchange = 0b11
        if exchange_instruction_set:
            target = (target & ~0x2) | (base & 0x2)
            bits_to_exchange = 0b01
        offset = target - base
        branch_instr_1 = 0xF000 | ((offset >> 12) & 0x7FF)
        branch_instr_2 = 0xE800 | ((offset >> 1) & 0x7FF) | (bits_to_exchange << 11)
        return branch_instr_1, branch_instr_2

    def instr__thumb_bx__8byte(src, target, ldr_reg_num):
        ldr_instr = 0x4800 | (ldr_reg_num << 8)
        bxr_instr = 0x4700 | (ldr_reg_num << 3)

        ac_code = f"1{src:07X} {ldr_instr:08X}\n"
        ac_code += f"1{src+2:07X} {bxr_instr:08X}\n"
        ac_code += f"1{src+4:07X} {target & 0xFFFF:08X}\n"
        ac_code += f"1{src+6:07X} {(target >> 16) & 0xFFFF:08X}\n"

        return ac_code

    rom_info = roms_info[rom_signature]
    ar_code = ""

    ####################################################################################
    # Arm7 Patch
    arm7_code_start_address = rom_info.arm7_rtc_region_start
    vblank_handler_end = rom_info.arm7_vblank_irq_end_address
    update_rtcom_func_offset, arm7_patch_bytes = assemble_arm7_rtcom_patch(rom_signature)
    branch_to_rtcom_update_instruction = instr__arm_b(vblank_handler_end,
                                                      arm7_code_start_address + update_rtcom_func_offset)

    ar_code += f"""
        # wait until the arm7's code has been fully uploaded
        5{vblank_handler_end:07X} {0xe12fff1e:08X}  # if equal to "bx lr"

            0{rom_info.arm7_rtc_init_function_call:07X} 00000000                # prevent call to init the RTC on Arm7
            {ar_code__bulk_write(arm7_patch_bytes, arm7_code_start_address)}    # write the Arm7 + Arm11 code

            0{vblank_handler_end:07X} {branch_to_rtcom_update_instruction:08X}  # Hook the VBlank IRQ Handler
        D0000000 00000000
    """

    ####################################################################################
    # Arm9 patch
    code_exec_address = rom_info.arm9_code_position
    code_binary, code_asm_text = assemble_arm9_patch(
        rom_signature, "arm9_controls_hook.s",
        (("INVERT_STEERING", int(variant.inverted)),
         ("ROLL_ON_SHOULDERS", int(variant.shoot_on_a))),
    )
    if len(code_binary) > 0x4A0:
        raise ValueError("The ARM9 patch exceeds the tested safe code area")
    protected_ranges = (
        (0x84, 0x8C), (0xF0, 0xF4), (0x144, 0x14C), (0x1BC, 0x1C4),
        (0x22C, 0x230), (0x294, 0x29C), (0x2EC, 0x2F4),
        (0x368, 0x36C), (0x3E0, 0x3E4), (0x446, 0x44C),
    )
    if any(
        start < len(code_binary)
        and code_binary[start:min(end, len(code_binary))] != bytes(min(end, len(code_binary)) - start)
        for start, end in protected_ranges
    ):
        raise ValueError("The ARM9 layout overlaps a protected BIOS service entry")
    safe_ranges = (
        (0, 0x84), (0x8C, 0xF0), (0xF4, 0x144), (0x14C, 0x1BC),
        (0x1C4, 0x22C), (0x230, 0x294), (0x29C, 0x2EC),
        (0x2F4, 0x368), (0x36C, 0x3E0), (0x3E4, 0x446), (0x44C, 0x4A0),
    )
    code_writes = "".join(
        ar_code__bulk_write(code_binary[start:end], code_exec_address + start)
        for start, end in safe_ranges if end > start
    )

    # Player Movement
    player_move_hook_addr = rom_info.arm9_crackers_dpad_hook
    player_move_orig_instr = 0x2298
    player_move_offset = find_function_offset_in_asm_listing(code_asm_text, 'MovePlayerWithCPad')

    start_rolling_hook_addr = rom_info.arm9_barrel_roll_hook
    start_rolling_orig_instr = 0x3041
    start_rolling_offset = find_function_offset_in_asm_listing(code_asm_text, 'barrel_roll_func')

    start_rolling_branch_instr = instr__thumb_bl(
        start_rolling_hook_addr, code_exec_address + start_rolling_offset)
    touch_sample_offset = find_function_offset_in_asm_listing(code_asm_text, 'bomb_touch_sample')
    touch_sample_hook_addr = rom_info.arm9_touch_sample_hook
    touch_sample_branch_instr = instr__thumb_bl(
        touch_sample_hook_addr, code_exec_address + touch_sample_offset)
    shooting_keys = 0x0001 if variant.shoot_on_a else 0x03F0

    ar_code += f"""
        # wait for some time, just to be sure (0x27FFC3C is a frame counter)
        427FFC3C 00000100
            52000000 E7FFDEFF
                {code_writes}
        D2000000 00000000

        427FFC3C 00000200
            9{touch_sample_hook_addr:07X} 0000F000
                1{touch_sample_hook_addr:07X} {touch_sample_branch_instr[0]:08X}
                1{touch_sample_hook_addr+2:07X} {touch_sample_branch_instr[1]:08X}
        D2000000 00000000

        427FFC3C 00000200
            9{player_move_hook_addr:07X} {player_move_orig_instr:08X}
                {instr__thumb_bx__8byte(player_move_hook_addr, code_exec_address+player_move_offset, 2)}
        D2000000 00000000

        427FFC3C 00000200
            9{start_rolling_hook_addr:07X} {start_rolling_orig_instr:08X}
                1{start_rolling_hook_addr+0:07X} {start_rolling_branch_instr[0]:08X}
                1{start_rolling_hook_addr+2:07X} {start_rolling_branch_instr[1]:08X}
        D2000000 00000000

        # Select the firing buttons separately from the barrel-roll input.
        427FFC3C 00000200
            9{rom_info.arm9_shooting_keys_addr:07X} 00000FF3
                1{rom_info.arm9_shooting_keys_addr:07X} {shooting_keys:08X}
        D2000000 00000000

    """

    formatted_cheatcode = ""
    for line in ar_code.splitlines():
        mb_nonempty_line = line.split('#')[0].strip()
        if len(mb_nonempty_line) > 0:
            formatted_cheatcode += mb_nonempty_line + '\n'

    return formatted_cheatcode


def generate_action_replay_codes_for_all_rom_versions():
    ac_folder_name = "action_replay_codes"
    Path(ac_folder_name).mkdir(exist_ok=True)

    cheat_codes = defaultdict(list)
    for rom_id, info in roms_info.items():
        filename = f"{rom_id} ({info.description})"

        for variant in VARIANTS:
            code_text = generate_action_replay_code(rom_id, variant)
            output_directory = Path(ac_folder_name) / variant.directory
            output_directory.mkdir(exist_ok=True)
            (output_directory / f"{filename}.txt").write_text(code_text)
            cheat_codes[rom_id].append({
                'code': code_text,
                'name': variant.name,
                'enabled': variant == DEFAULT_VARIANT,
            })

    usrcheat_dat_file = generate_usrcheat_dat_file_with_ar_codes(cheat_codes)
    with open(f'{ac_folder_name}/usrcheat.dat', 'wb') as f:
        f.write(usrcheat_dat_file)


def generate_usrcheat_dat_file_with_ar_codes(patches: dict):
    def make_ar_file_header():
        main_header = bytearray(b'\0' * 0x100)
        main_header[0:0xC] = b'R4 CheatCode'
        main_header[0xD] = 1
        db_name = b"Star Fox Command CPad Patch"
        struct.pack_into(f'{len(db_name)}s', main_header, 0x10, db_name)
        struct.pack_into('<I', main_header, 0x4C, 0x594153d5)
        main_header[0x50] = 1
        return main_header

    def make_ar_game_header(game_name, n_code):
        game_name = game_name.encode()
        game_header = game_name + b'\0' * (4 - len(game_name) % 4)
        game_attribute_header = bytearray(0x24)
        game_attribute_header[0] = n_code
        game_attribute_header[8] = 1
        game_header += game_attribute_header
        return game_header

    def get_ar_code_values_from_text(codes):
        ar_code_values = []
        for line in codes.splitlines():
            columns = line.split()
            if len(columns) != 2:
                continue
            ar_code_values.append(int(columns[0], 16))
            ar_code_values.append(int(columns[1], 16))
        return ar_code_values

    def make_ar_code_record(code_name, code_description, ar_code_values, enabled=False):
        # Code Header
        ar_code_name = code_name.encode()
        ar_code_description = code_description.encode()
        ar_code_header = ar_code_name + b'\0'
        ar_code_header += ar_code_description
        ar_code_header += b'\0' * (4 - len(ar_code_header) % 4)

        # AR Code Record
        ar_code = struct.pack(f"<{len(ar_code_values)}I", *ar_code_values)
        ar_code_size = len(ar_code)
        ar_code_header += struct.pack("<I", ar_code_size // 4)
        ar_code_size_with_header = ar_code_size + len(ar_code_header)

        header_attributes = ar_code_size_with_header // 4
        if enabled:
            header_attributes |= 0x01000000
        ar_code_header = struct.pack("<I", header_attributes) + ar_code_header

        ar_code_record = ar_code_header + ar_code
        return ar_code_record

    n_games = len(patches)

    # Game Position Table
    game_pos_table = bytearray(0x10 * n_games)

    game_codes = defaultdict(list)
    for i, (rom_id, roms_info) in enumerate(patches.items()):
        gamecode, crc32_str = rom_id.split('-')
        struct.pack_into('<4sI', game_pos_table, 0x10 * i, gamecode.encode(), int(crc32_str, 16))

        for rom_code in roms_info:
            ar_code_record = make_ar_code_record(rom_code['name'], "",
                                                 get_ar_code_values_from_text(rom_code['code']),
                                                 rom_code.get('enabled', False))
            game_codes[rom_id].append(ar_code_record)

    # Make it Whole
    usrcheat_dat_file = bytearray()
    usrcheat_dat_file += make_ar_file_header()
    usrcheat_dat_file += game_pos_table + bytes(0x10)

    for i, (rom_id, rom_codes) in enumerate(game_codes.items()):
        struct.pack_into('<I', usrcheat_dat_file, 0x100 + i * 0x10 + 8, len(usrcheat_dat_file))
        usrcheat_dat_file += make_ar_game_header(rom_id, n_code=len(rom_codes))
        for rom_code in rom_codes:
            usrcheat_dat_file += rom_code

    return usrcheat_dat_file


def main():
    tmp_folder_path = Path(tmp_folder_name)
    tmp_folder_existed = tmp_folder_path.exists()
    if not tmp_folder_existed:
        tmp_folder_path.mkdir()

    generate_action_replay_codes_for_all_rom_versions()

    if not tmp_folder_existed:
        import shutil
        shutil.rmtree(tmp_folder_name)


if __name__ == "__main__":
    main()
