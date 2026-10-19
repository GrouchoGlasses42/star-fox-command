# Star Fox Command Circle Pad Patch

This repository contains a Circle Pad patch for **Star Fox Command**.
The patch operates on a Nintendo 3DS.
It uses RTCom and a TwlBg runtime patch.
These components send Circle Pad input to the game.

## Controls

Select one patch from this table.
Enable only one control patch at a time.

| Patch | Ship steering | Fire | Barrel roll |
|---|---|---|---|
| [3DS - Normal - L/R](./action_replay_codes/3ds_normal_lr) | Normal | L or R | A |
| [3DS - Inverted - L/R](./action_replay_codes/3ds_inverted_lr) | Inverted | L or R | A |
| [3DS - Normal - A](./action_replay_codes/3ds_normal_a) | Normal | A | L or R |
| [3DS - Inverted - A](./action_replay_codes/3ds_inverted_a) | Inverted | A | L or R |

The supplied database selects `3DS - Normal - L/R` by default.
This patch uses the previous control layout.

With normal steering, move the Circle Pad up to move the ship up.
With inverted steering, move the Circle Pad up to move the ship down.
Inverted steering changes only the vertical ship input.
Horizontal ship input is the same in all four patches.

These controls are the same in all four patches:

| Input | Action |
|---|---|
| Circle Pad | Flight control |
| X button | Boost |
| B button | Brake |
| Y button | Hold to aim a Smart Bomb |
| Circle Pad while Y is held | Move the Smart Bomb target |
| D-Pad Up | Loop |
| D-Pad Down | U-turn |

The A button also confirms a menu selection.
The B button also cancels a menu selection.
Only D-Pad Up and D-Pad Down start the two flight maneuvers.
Circle Pad input does not start these maneuvers.

Hold the Y button to select a Smart Bomb.
Move the Circle Pad to set the target position.
The Circle Pad does not steer the ship while the Y button is held.
Release the Y button to deploy the Smart Bomb.
Bomb target input is always normal, including with an inverted steering patch.
Move the Circle Pad up to move the bomb target up.
Use the fire button for the selected patch to fire while you aim a bomb.
The Smart Bomb controls are inactive when the game disables Smart Bombs.

Hold X to boost or B to brake.
Both actions use the ship's energy meter.
If the meter is empty, release X and B before you use these actions again.

## Supported ROM Versions

Use the patch only with these Nintendo DS ROM versions:

| Region | Game ID and header CRC |
|---|---|
| Europe version 1.0 | `ASFP-F0E8BD5C` |
| Japan version 1.0 | `ASFJ-70977801` |
| USA version 1.0 | `ASFE-F22E6A7D` |

This repository does not contain a ROM file.

## Installation

Before you install the patch, complete these steps:

1. Install TWPatcher on the Nintendo 3DS.
2. Enable RTCom in TWPatcher.

Then, install the Action Replay code:

1. Open the [`action_replay_codes`](./action_replay_codes) directory.
2. Open the directory for the required patch.
3. Select the text file for your ROM version.
4. Import the text file into your cheat database.
5. Start TWiLight Menu.
6. Enable the selected patch for the game.
7. Make sure that all other Star Fox control patches are off.

If you do not use another cheat database, use the supplied `usrcheat.dat` file.
This file contains all four patches for each supported ROM version.
To change the patch, turn off the current patch before you select another one.
Restart the game after you change the patch.

## Build Procedure

Before you build the patch, install these tools:

- devkitARM
- devkitPro
- Python 3

Add the command locations to `PATH`.

To build the patch, complete these steps:

1. Open a terminal in the repository root directory.
2. Run this command:

   ```sh
   python3 generate_patch.py
   ```

The script builds four patches for each of the three ROM versions.
It writes 12 Action Replay text files to the patch directories.
It also builds `action_replay_codes/usrcheat.dat`.

## Repository Contents

- `arm9_controls_hook.s` contains the ARM9 movement and button hooks.
- `arm9_bomb_hook.s` contains the Y button and Circle Pad bomb controls.
- `arm7_rtcom_patch/` contains the ARM7 and ARM11 runtime sources.
- `generate_patch.py` builds the Action Replay files.
- `update_usrcheat.py` replaces the previous patch in an existing cheat database.
- `action_replay_codes/` contains the regional codes and the cheat database.

## Credits

- The Circle Pad and RTCom implementation is based on [shocoman's project](https://github.com/shocoman/Analog-Controls-for-NDS-Games-on-3DS).
- The runtime code also uses work from [Gericom's Rtc3DS project](https://github.com/Gericom/Rtc3DS).
- The game-control hooks are based on [cracker's original Star Fox Command patch](https://gbatemp.net/threads/starfox-command-u-d-pad-hack.118663/page-7).

See [Third-Party Notices](./THIRD_PARTY_NOTICES.md) for source information.

## Disclaimer

This project is independent and unofficial.
This project is not affiliated with Nintendo.
Nintendo does not create, approve, endorse, or support this project.
Nintendo owns the Nintendo trademarks.
The owners of other trademarks retain ownership of their trademarks.
This repository does not include Nintendo ROM images, firmware images, game assets, or encryption keys.
