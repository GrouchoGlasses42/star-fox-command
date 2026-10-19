"""Run the generated regional flight hooks on an ARM emulator.

Requires the Python unicorn package. Set SFC_EU_OVERLAY2 to a locally extracted
European flight overlay to also exercise the game's real energy-update code.
"""

import os
from pathlib import Path
import struct
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_patch import VARIANTS, DEFAULT_VARIANT

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)


ROOT = Path(__file__).resolve().parents[1]
REGIONS = (
    ("ASFP-F0E8BD5C (Europe v1.0)", 0x022113C2, 0x021EE528, 0x021EE550),
    ("ASFJ-70977801 (Japan v1.0)", 0x022114A6, 0x021EED0C, 0x021EED34),
    ("ASFE-F22E6A7D (USA v1.0)", 0x022115BE, 0x021EEE28, 0x021EEE50),
)
REGISTERS = (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
)
SHIP = 0x02310000
STACK = 0x02330000
STOP = 0x02340000
BOMB_STATE = 0x0200044C


class Flight:
    def __init__(self, region=REGIONS[0], variant=DEFAULT_VARIANT):
        name, self.hook, self.loop, self.uturn = region
        self.touch_hook = 0x0203BFAE if name.startswith("ASFP") else 0x0203BF5A
        self.real_sampler = 0x0203C068 if name.startswith("ASFP") else 0x0203C014
        self.move_hook = {
            "ASFP": 0x021E9434, "ASFJ": 0x021E9C18, "ASFE": 0x021E9D34,
        }[name[:4]]
        self.mode_accessor = 0x0219AEF0
        self.real_touch = (17, 29, 1, 0)
        self.stop_addresses = set()
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(0x02000000, 0x00400000)
        self.uc.mem_map(0x027F0000, 0x10000)
        self.uc.mem_map(0x04000000, 0x1000)
        self.maneuvers = []
        self.uc.hook_add(UC_HOOK_CODE, self.on_instruction)
        self.return_pc = None
        self.native = False
        self.guard_ranges = (
            (0x84, 8), (0xF0, 4), (0x144, 8), (0x1BC, 8), (0x22C, 4),
            (0x294, 8), (0x2EC, 8), (0x368, 4), (0x3E0, 4), (0x446, 6),
        )
        for offset, length in self.guard_ranges:
            self.uc.mem_write(0x02000000 + offset, bytes([0xA5]) * length)
        rows = [tuple(int(x, 16) for x in row.split()) for row in
                (ROOT / "action_replay_codes" / variant.directory / f"{name}.txt").read_text().splitlines()]
        i = 0
        while i < len(rows):
            command, value = rows[i]
            if command >> 28 == 0xE:
                count = (value + 7) // 8
                payload = b"".join(struct.pack("<II", *pair) for pair in rows[i + 1:i + 1 + count])
                address = command & 0x0FFFFFFF
                if 0x02000000 <= address < 0x02001000:
                    self.uc.mem_write(address, payload[:value])
                i += count
            elif command >> 28 == 1:
                address = command & 0x0FFFFFFF
                if 0x02000000 <= address < 0x02400000:
                    self.uc.mem_write(address, struct.pack("<H", value))
            i += 1
        self.write32(0x02301030, 0x02302000)
        self.write32(0x02302000, SHIP)
        self.uc.mem_write(0x02320041, b"\x5a")
        self.write32(SHIP + 0xC4, 0x49000)
        self.write32(0x027FFC3C, 1000)
        offset = self.mode_accessor - (self.uturn + 0x14)
        self.uc.mem_write(self.uturn + 0x10, struct.pack(
            "<HH", 0xF000 | ((offset >> 12) & 0x7FF), 0xF800 | ((offset >> 1) & 0x7FF)))

    def write32(self, address, value):
        self.uc.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))

    def read32(self, address):
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def on_instruction(self, uc, address, size, data):
        if address == STOP or (not self.native and address in self.stop_addresses):
            self.return_pc = address
            uc.emu_stop()
        elif not self.native and address == self.real_sampler:
            uc.mem_write(uc.reg_read(UC_ARM_REG_R0), struct.pack("<4H", *self.real_touch))
            uc.reg_write(UC_ARM_REG_R0, 0)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif not self.native and address == self.mode_accessor:
            uc.reg_write(UC_ARM_REG_R0, STOP + 0x1000)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif not self.native and address in (self.loop, self.uturn):
            assert uc.reg_read(UC_ARM_REG_R0) == SHIP
            assert uc.reg_read(UC_ARM_REG_R1) == 0
            self.maneuvers.append(address)
            # The real functions may clobber caller-saved registers.
            for register in REGISTERS[:4]:
                uc.reg_write(register, 0xABCD)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif self.native and not 0x021DEE00 <= address < 0x02224740:
            r = [uc.reg_read(register) for register in REGISTERS[:4]]
            signed = lambda value: value if value < 0x80000000 else value - 0x100000000
            if address == 0x0200FF50:  # signed 64-bit multiplication
                a = r[0] | (r[1] << 32)
                b = r[2] | (r[3] << 32)
                result = (a * b) & 0xFFFFFFFFFFFFFFFF
                uc.reg_write(UC_ARM_REG_R0, result & 0xFFFFFFFF)
                uc.reg_write(UC_ARM_REG_R1, result >> 32)
            else:
                # Native configuration initialization and mode queries.
                assert address in (0x02056B98, 0x020128A0, 0x02059700), hex(address)
                uc.reg_write(UC_ARM_REG_R0, 0)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif self.native and address == 0x021FA2D4:  # native clamp helper
            a = uc.reg_read(UC_ARM_REG_R0)
            values = [uc.reg_read(register) for register in REGISTERS[1:4]]
            signed = lambda value: value if value < 0x80000000 else value - 0x100000000
            value, low, high = map(signed, values)
            self.write32(a, min(max(value, low), high))
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def frame(self, *, x=False, b=False, a=False, y=False, l=False, r=False,
              up=False, down=False, cpad=0):
        keys = (int(a) | (int(b) << 1) | (int(up) << 6) | (int(down) << 7)
                | (int(r) << 8) | (int(l) << 9))
        self.uc.mem_write(0x04000130, struct.pack("<H", (~keys) & 0xFFFF))
        self.uc.mem_write(0x027FFFA8, struct.pack("<H", 0xFFFF ^ (int(x) << 10) ^ (int(y) << 11)))
        self.uc.mem_write(0x027FFDF0, bytes([cpad & 0xFF, 0]))
        values = [0x02320000, 0x1111, 0x2222, 0x3333, 0x02301000, 0x5555, 0x6666, 0x7777]
        for register, value in zip(REGISTERS, values):
            self.uc.reg_write(register, value)
        self.uc.reg_write(UC_ARM_REG_SP, STACK)
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.write32(0x027FFC3C, self.read32(0x027FFC3C) + 1)
        self.stop_addresses = {self.hook + 4, self.hook + 8, self.hook + 0x2C}
        self.return_pc = None
        self.uc.emu_start(self.hook | 1, STOP, count=1000)
        assert self.return_pc is not None, "flight hook did not return"
        assert self.uc.reg_read(UC_ARM_REG_SP) == STACK
        assert [self.uc.reg_read(register) for register in REGISTERS] == [0x5A] + values[1:]
        for offset, length in self.guard_ranges:
            assert self.uc.mem_read(0x02000000 + offset, length) == bytes([0xA5]) * length
        return tuple(self.uc.mem_read(SHIP + 0x10E, 2))

    def bomb_sample(self, *, y=False, cpad_x=0, cpad_y=0, linear=False):
        self.uc.mem_write(0x027FFFA8, struct.pack("<H", 0xFFFF ^ (int(y) << 11)))
        self.uc.mem_write(0x027FFDF0, bytes([cpad_x & 0xFF, cpad_y & 0xFF]))
        self.write32(STOP + 0x1008, int(linear))
        self.uc.reg_write(UC_ARM_REG_R0, 0x02321000)
        self.uc.reg_write(UC_ARM_REG_SP, STACK)
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        saved = [self.uc.reg_read(register) for register in REGISTERS[4:]]
        self.return_pc = None
        self.stop_addresses = {self.touch_hook + 4}
        self.uc.emu_start(self.touch_hook | 1, STOP, count=1000)
        assert self.return_pc == self.touch_hook + 4, "touch hook did not return"
        assert self.uc.reg_read(UC_ARM_REG_SP) == STACK
        assert [self.uc.reg_read(register) for register in REGISTERS[4:]] == saved
        return struct.unpack("<4H", self.uc.mem_read(0x02321000, 8))

    def move(self, cpad_x, cpad_y, ship_y, ship_x):
        self.uc.mem_write(0x027FFDF0, bytes([cpad_x & 0xFF, cpad_y & 0xFF]))
        self.uc.mem_write(0x02320098, struct.pack("<hh", ship_y, ship_x))
        self.uc.reg_write(UC_ARM_REG_R0, 0x02323000)
        self.uc.reg_write(UC_ARM_REG_R1, 0x02320000)
        self.uc.reg_write(UC_ARM_REG_SP, STACK)
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.return_pc = None
        self.stop_addresses = {self.move_hook + 8}
        self.uc.emu_start(self.move_hook | 1, STOP, count=1000)
        assert self.return_pc == self.move_hook + 8, "movement hook did not return"
        assert self.uc.reg_read(UC_ARM_REG_SP) == STACK
        return struct.unpack("<hh", self.uc.mem_read(0x02320098, 4))

    def native_energy_frame(self):
        self.native = True
        self.return_pc = None
        self.uc.reg_write(UC_ARM_REG_R0, SHIP)
        self.uc.reg_write(UC_ARM_REG_SP, STACK)
        self.uc.reg_write(UC_ARM_REG_LR, STOP | 1)
        self.uc.emu_start(0x021EDBC5, STOP, count=4000)
        self.native = False
        assert self.uc.reg_read(UC_ARM_REG_PC) == STOP, "native energy update did not return"


class FlightControlsTest(unittest.TestCase):
    def test_all_four_variants_in_each_region(self):
        for region in REGIONS:
            for variant in VARIANTS:
                with self.subTest(region=region[0], variant=variant.name):
                    f = Flight(region, variant)
                    expected_y = 340 if variant.inverted else -140
                    self.assertEqual(f.move(80, 80, 100, 200), (expected_y, -40))
                    f.frame(a=True, cpad=50)
                    self.assertEqual(f.return_pc, f.hook + (4 if variant.shoot_on_a else 0x2C))
                    f.frame()
                    for shoulder in ("l", "r"):
                        f.frame(**{shoulder: True}, cpad=-50)
                        self.assertEqual(f.return_pc, f.hook + (8 if variant.shoot_on_a else 4))
                        f.frame()
                    # Releasing one shoulder must not stop the other shoulder's roll.
                    if variant.shoot_on_a:
                        f.frame(l=True, r=True)
                        f.frame(l=True)
                        self.assertEqual(f.return_pc, f.hook + 0x2C)
                        f.frame()
                        self.assertEqual(f.return_pc, f.hook + 4)
                    fire_mask_address = {
                        "ASFP": 0x021CCCF0, "ASFJ": 0x021CD164, "ASFE": 0x021CD250,
                    }[region[0][:4]]
                    mask = struct.unpack("<H", f.uc.mem_read(fire_mask_address, 2))[0]
                    self.assertEqual(mask, 1 if variant.shoot_on_a else 0x3F0)
                    for button in (1, 2, 0x100, 0x200, 0x400, 0x800):
                        fires = bool(mask & button)
                        self.assertEqual(fires, button == 1 if variant.shoot_on_a
                                         else button in (0x100, 0x200))
                    # The bomb target must always move right/up for right/up input.
                    f.move(0, 0, 100, 200)
                    for _ in range(6):
                        f.frame(y=True)
                        f.bomb_sample(y=True)
                    f.frame(y=True, x=True)
                    target = f.bomb_sample(y=True, cpad_x=80, cpad_y=80)
                    self.assertGreater(target[0], 128)
                    self.assertLess(target[1], 96)
                    self.assertEqual(f.move(80, 80, 12000, 12000), (100, 200))
                    f.frame()
                    f.bomb_sample()
                    f.frame()
                    self.assertEqual(f.bomb_sample()[2:], (0, 0))
                    self.assertEqual(f.frame(x=True), (1, 0))
                    f.write32(SHIP + 0xBC, f.read32(SHIP + 0xC4))
                    self.assertEqual(f.frame(x=True), (0, 0))
                    f.frame(y=True)
                    self.assertEqual(f.bomb_sample(y=True, linear=True), f.real_touch)

    def test_bomb_hold_aim_release_and_steering(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                f.frame()
                self.assertEqual(f.move(0, 0, 100, 200), (100, 200))
                for _ in range(6):
                    f.frame(y=True)
                    self.assertEqual(f.bomb_sample(y=True), (224, 56, 1, 0))
                f.frame(y=True)
                target = f.bomb_sample(y=True, cpad_x=80, cpad_y=80)
                self.assertGreater(target[0], 128)
                self.assertLess(target[1], 96)
                self.assertEqual(target[2:], (1, 0))
                self.assertEqual(f.move(80, 80, 12000, 12000), (100, 200))
                f.frame(y=False)
                self.assertEqual(f.bomb_sample()[2:], (1, 0))
                f.frame(y=False)
                self.assertEqual(f.bomb_sample()[2:], (0, 0))
                self.assertEqual(f.read32(BOMB_STATE + 0x14), 0)
                self.assertEqual(f.move(80, 80, 100, 200), (-140, -40))

    def test_bomb_disabled_in_menus_and_linear_stages(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                self.assertEqual(f.bomb_sample(y=True), f.real_touch)
                f.frame(y=True)
                self.assertEqual(f.bomb_sample(y=True, linear=True), f.real_touch)
                self.assertEqual(f.read32(BOMB_STATE + 0x14), 0)
                self.assertEqual(f.move(80, 80, 100, 200), (-140, -40))
                f.frame(y=True)
                f.bomb_sample(y=True)
                self.assertEqual(f.read32(BOMB_STATE + 0x14), 1)
                self.assertEqual(f.bomb_sample(y=True, linear=True)[2:], (0, 0))
                f.frame(y=True)
                f.bomb_sample(y=True)
                f.write32(0x027FFC3C, f.read32(0x027FFC3C) + 9)
                self.assertEqual(f.bomb_sample(y=True)[2:], (0, 0))
                self.assertEqual(f.read32(BOMB_STATE + 0x14), 0)

    def test_bomb_short_tap_and_cursor_limits(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                f.frame(y=True)
                f.bomb_sample(y=True)
                samples = []
                for _ in range(8):
                    f.frame()
                    samples.append(f.bomb_sample())
                self.assertIn((128, 96, 1, 0), samples)
                self.assertIn((128, 96, 0, 0), samples)
                self.assertEqual(f.read32(BOMB_STATE + 0x14), 0)
                for _ in range(100):
                    f.frame(y=True)
                    target = f.bomb_sample(y=True, cpad_x=127, cpad_y=-128)
                self.assertEqual(target, (208, 176, 1, 0))
                for _ in range(100):
                    f.frame(y=True)
                    target = f.bomb_sample(y=True, cpad_x=-128, cpad_y=127)
                self.assertEqual(target, (48, 40, 1, 0))

    def test_held_inputs_and_boost_priority(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                self.assertEqual(f.frame(), (0, 0))
                for _ in range(20):
                    self.assertEqual(f.frame(x=True), (1, 0))
                self.assertEqual(f.frame(), (0, 0))
                self.assertEqual(f.frame(b=True), (0, 1))
                self.assertEqual(f.frame(x=True, b=True), (1, 0))

    def test_meter_exhaustion_and_release_to_rearm(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                f.write32(SHIP + 0xC4, 0x20000)  # different ship capacity
                self.assertEqual(f.frame(x=True), (1, 0))
                f.write32(SHIP + 0xBC, 0x20000)
                self.assertEqual(f.frame(x=True), (0, 0))
                for _ in range(30):
                    self.assertEqual(f.frame(), (0, 0))
                    self.assertEqual(f.frame(x=True), (0, 0))
                f.write32(SHIP + 0xBC, 0x10000)
                self.assertEqual(f.frame(x=True), (0, 0))
                self.assertEqual(f.frame(x=True, b=True), (0, 0))
                self.assertEqual(f.frame(b=True), (0, 0))
                self.assertEqual(f.frame(), (0, 0))
                self.assertEqual(f.frame(b=True), (0, 1))

    def test_native_exhaustion_latch(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                f.uc.mem_write(SHIP + 0x10C, b"\x01")
                self.assertEqual(f.frame(x=True), (0, 0))
                self.assertEqual(f.frame(), (0, 0))
                f.uc.mem_write(SHIP + 0x10C, b"\x00")
                self.assertEqual(f.frame(x=True), (0, 0))
                f.frame()
                self.assertEqual(f.frame(x=True), (1, 0))

    def test_barrel_roll_and_dpad(self):
        for region in REGIONS:
            with self.subTest(region=region[0]):
                f = Flight(region)
                f.frame(a=True, cpad=50)
                self.assertEqual(f.return_pc, f.hook + 0x2C)
                f.frame(a=True, cpad=-50)
                self.assertEqual(f.return_pc, f.hook + 8)
                f.frame(a=True, up=True, x=True)
                f.frame(a=True, up=True, x=True)
                f.frame(down=True, b=True)
                self.assertEqual(f.maneuvers, [f.loop, f.uturn])
                self.assertEqual(f.return_pc, f.hook + 4)
                self.assertEqual(f.uc.mem_read(SHIP + 0x113, 1), b"\0")

    @unittest.skipUnless(os.environ.get("SFC_EU_OVERLAY2"), "local European overlay required")
    def test_actual_native_energy_update_depletes_meter(self):
        for brake, continuous in ((False, False), (False, True), (True, True)):
            with self.subTest(brake=brake, continuous=continuous):
                f = Flight()
                overlay = Path(os.environ["SFC_EU_OVERLAY2"]).read_bytes()
                self.assertEqual(len(overlay), 0x45940)
                hook_bytes = bytes(f.uc.mem_read(f.hook, 4))
                f.uc.mem_write(0x021DEE00, overlay)
                f.uc.mem_write(f.hook, hook_bytes)
                f.write32(0x02224984, 0x400)   # native recovery per update
                f.write32(0x02224988, 0x1000)  # native consumption per update
                f.write32(SHIP + 0xC4, 0x10000)
                observed_consumption = False
                for frame in range(100):
                    # Rapid taps and continuous holds must both stop at empty.
                    pressed = continuous or frame % 3 != 2
                    flags = f.frame(x=pressed and not brake, b=brake)
                    before = f.read32(SHIP + 0xBC)
                    f.native_energy_frame()
                    after = f.read32(SHIP + 0xBC)
                    if flags != (0, 0) and after > before:
                        observed_consumption = True
                    if after >= 0x10000 or f.uc.mem_read(SHIP + 0x10C, 1) == b"\x01":
                        self.assertEqual(f.frame(x=True, b=brake), (0, 0))
                        # Recovery while still held cannot rearm either action.
                        for _ in range(10):
                            f.native_energy_frame()
                            self.assertEqual(f.frame(x=True, b=brake), (0, 0))
                        break
                else:
                    self.fail("native meter did not reach exhaustion")
                self.assertTrue(observed_consumption)


if __name__ == "__main__":
    unittest.main()
