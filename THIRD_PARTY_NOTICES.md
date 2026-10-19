# Third-Party Notices

## Patch Sources

This project uses work from these projects and authors:

- [shocoman's Analog Controls for NDS Games on 3DS](https://github.com/shocoman/Analog-Controls-for-NDS-Games-on-3DS): Circle Pad controls, the patch generator, and the ARM7 and ARM11 runtime code.
- [Gericom's Rtc3DS](https://github.com/Gericom/Rtc3DS): runtime communication code used by the upstream project.
- [cracker's original Star Fox Command patch](https://gbatemp.net/threads/starfox-command-u-d-pad-hack.118663/page-7): the original game-control patch and hook research.

Third-party code remains the work of its original authors.
The shocoman repository does not state a licence at the time of this review.
This notice does not grant a licence to third-party code.

## Runtime Data

`arm7_rtcom_patch/known_good_cpad_transport.b64` contains a compiled patch runtime.
The decoded file has 1,960 bytes.
Its SHA-256 value is:

```text
bf7895010672f5db1a4a860231b5e3b958c65ec871bab288b4b6a9487c086daf
```

This runtime is the same as the ARM7 payload in project commit `0531b75`.
It is patch code, not a Nintendo firmware image.
The Action Replay files and the supplied cheat database contain the patch code.

The runtime uses short instruction patterns to find functions in system memory.
The game hooks also contain the few instructions that each hook replaces.
These sequences let the patch use the code already on the console.

## Excluded Files

This repository does not supply Nintendo ROM images or firmware images.
It does not supply game graphics, game music, encryption keys, or saved games.
Tests can use a game overlay from a local path.
The overlay data is not part of the tests or the repository.
