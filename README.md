# Star Fox Command Circle Pad Patch

This repository contains a Circle Pad patch for **Star Fox Command**.
The patch operates on a Nintendo 3DS.
It uses RTCom and a TwlBg runtime patch.
These components send Circle Pad input to the game.

## Controls

| Input | Action |
|---|---|
| Circle Pad | Flight control |
| X button | Boost |
| B button | Brake |
| A button | Barrel roll |
| D-Pad Up | Loop |
| D-Pad Down | U-turn |

The A button also confirms a menu selection.
The B button also cancels a menu selection.
Only D-Pad Up and D-Pad Down start the two flight maneuvers.
Circle Pad input does not start these maneuvers.

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
2. Select the text file for your ROM version.
3. Import the text file into your cheat database.
4. Start TWiLight Menu.
5. Enable `Revised CPad Patch` for the game.
6. Make sure that all other Star Fox control patches are off.

If you do not use another cheat database, use the supplied `usrcheat.dat` file.

## Build Procedure

Before you build the patch, install these tools:

- devkitARM
- devkitPro
- GNU Make
- Python 3

Add the command locations to `PATH`.

To build the patch, complete these steps:

1. Open a terminal in the repository root directory.
2. Run this command:

   ```sh
   python3 generate_patch.py
   ```

The script builds the three regional Action Replay text files.
It also builds `action_replay_codes/usrcheat.dat`.

## Repository Contents

- `arm9_controls_hook.s` contains the ARM9 movement and button hooks.
- `arm7_rtcom_patch/` contains the ARM7 and ARM11 runtime sources.
- `generate_patch.py` builds the Action Replay files.
- `action_replay_codes/` contains the regional codes and the cheat database.

## Credits

- The Circle Pad and RTCom implementation is based on [shocoman's project](https://github.com/shocoman/Analog-Controls-for-NDS-Games-on-3DS).
- The game-control hooks are based on [cracker's original Star Fox Command patch](https://gbatemp.net/threads/starfox-command-u-d-pad-hack.118663/page-7).

## Disclaimer

This project is independent and unofficial.
This project is not affiliated with Nintendo.
Nintendo does not create, approve, endorse, or support this project.
Nintendo owns the Nintendo trademarks.
The owners of other trademarks retain ownership of their trademarks.
