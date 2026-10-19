@ Included in arm9_controls_hook.s. Skip the BIOS entries between code blocks.

@ The ARM entry has saved r1-r5 and lr. Restore ship input during bomb aiming.
.thumb_func
bomb_steering_gate:
    ldr     r4, bomb_gate_state
    ldr     r5, [r4, #0x14]
    cmp     r5, #0
    beq     bomb_steering_gate__normal
    movs    r5, r1
    adds    r5, #0x98
    ldrh    r2, [r4, #0x28]
    strh    r2, [r5]
    ldrh    r2, [r4, #0x2a]
    strh    r2, [r5, #2]
    ldr     r3, bomb_gate_skip_cpad
    bx      r3
bomb_steering_gate__normal:
    movs    r5, r1
    adds    r5, #0x98
    ldrh    r2, [r5]
    strh    r2, [r4, #0x28]
    ldrh    r2, [r5, #2]
    strh    r2, [r4, #0x2a]
    ldr     r3, bomb_gate_read_cpad
    bx      r3
.align 2
bomb_gate_state: .long bomb_shared_state + 0x02000000
bomb_gate_skip_cpad: .long MovePlayerWithCPad__restore_registers + 0x02000000
bomb_gate_read_cpad: .long MovePlayerWithCPad__read_cpad + 0x02000000

.org 0x230
.thumb_func
bomb_touch_sample:
    push    {r3-r7, lr}
    movs    r4, r0
    ldr     r3, bomb_real_sampler
    blx     r3
    ldr     r5, bomb_sample_state
    ldr     r0, [r5, #0x10]
    cmp     r0, #0
    beq     bomb_touch_sample__reset_jump
    ldr     r1, bomb_frame_counter
    ldr     r1, [r1]
    ldr     r2, [r5, #0x0c]
    subs    r1, r1, r2
    cmp     r1, #8
    bhi     bomb_touch_sample__reset_jump
    ldr     r0, bomb_y_register
    ldrh    r0, [r0]
    lsls    r0, r0, #20
    lsrs    r0, r0, #31
    movs    r7, #1
    eors    r7, r0              @ physical Y, active high
    ldr     r3, [r5, #0x14]
    movs    r0, r7
    orrs    r0, r3
    beq     bomb_touch_sample__exit
    b       bomb_touch_sample__check_mode
bomb_touch_sample__reset_jump:
    b       bomb_touch_sample__reset
bomb_touch_sample__exit:
    pop     {r3-r7, pc}
.align 2
bomb_real_sampler: .long TOUCH_SAMPLE_FUNC_ADDR + 1
bomb_frame_counter: .long 0x027ffc3c
bomb_y_register: .long 0x027fffa8
bomb_sample_state: .long bomb_shared_state + 0x02000000

.org 0x29c
bomb_touch_sample__check_mode:
    @ Decode the regional Thumb BL to the mode accessor in the U-turn handler.
    ldr     r3, bomb_mode_uturn
    ldrh    r0, [r3, #0x10]
    ldrh    r1, [r3, #0x12]
    lsls    r0, r0, #21
    asrs    r0, r0, #9
    lsls    r1, r1, #21
    lsrs    r1, r1, #20
    adds    r0, r0, r1
    adds    r3, #0x14
    adds    r3, r3, r0
    movs    r0, #1
    orrs    r3, r0
    blx     r3
    ldr     r0, [r0, #8]
    cmp     r0, #1              @ linear stages disable bombs
    beq     bomb_touch_sample__mode_disabled
    ldr     r3, [r5, #0x14]
    cmp     r3, #0
    beq     bomb_touch_sample__start
    cmp     r3, #3
    beq     bomb_touch_sample__release_jump
    cmp     r3, #1
    bne     bomb_touch_sample__update_cursor
    cmp     r7, #0
    bne     bomb_touch_sample__update_cursor
    movs    r0, #1
    str     r0, [r5, #0x1c]     @ finish a short tap before release
    b       bomb_touch_sample__update_cursor
bomb_touch_sample__mode_disabled:
    b       bomb_touch_sample__reset
bomb_touch_sample__release_jump:
    b       bomb_touch_sample__release
.align 2
bomb_mode_uturn: .long UTURN_FUNC_ADDR

.org 0x2f4
bomb_touch_sample__start:
    movs    r3, #1
    str     r3, [r5, #0x14]
    movs    r0, #0
    str     r0, [r5, #0x18]
    str     r0, [r5, #0x1c]
    movs    r0, #128
    lsls    r0, r0, #8
    str     r0, [r5, #0x20]
    movs    r0, #96
    lsls    r0, r0, #8
    str     r0, [r5, #0x24]
bomb_touch_sample__update_cursor:
    ldr     r0, bomb_cpad_register
    movs    r1, #0
    ldrsb   r2, [r0, r1]
    movs    r1, #1
    ldrsb   r3, [r0, r1]
    lsls    r2, r2, #3
    lsls    r3, r3, #3
    ldr     r0, [r5, #0x20]
    adds    r0, r0, r2
    movs    r1, #48
    lsls    r1, r1, #8
    cmp     r0, r1
    bge     bomb_touch_sample__x_min
    movs    r0, r1
bomb_touch_sample__x_min:
    movs    r1, #208
    lsls    r1, r1, #8
    cmp     r0, r1
    ble     bomb_touch_sample__x_max
    movs    r0, r1
bomb_touch_sample__x_max:
    str     r0, [r5, #0x20]
    ldr     r0, [r5, #0x24]
    subs    r0, r0, r3
    movs    r1, #40
    lsls    r1, r1, #8
    cmp     r0, r1
    bge     bomb_touch_sample__y_min
    movs    r0, r1
bomb_touch_sample__y_min:
    movs    r1, #176
    lsls    r1, r1, #8
    cmp     r0, r1
    ble     bomb_touch_sample__y_max
    movs    r0, r1
bomb_touch_sample__y_max:
    str     r0, [r5, #0x24]
    ldr     r3, [r5, #0x14]
    cmp     r3, #1
    beq     bomb_touch_sample__icon
    b       bomb_touch_sample__target
.align 2
bomb_cpad_register: .long 0x027ffdf0

.org 0x36c
bomb_touch_sample__icon:
    ldr     r0, [r5, #0x18]
    adds    r0, #1
    cmp     r0, #6              @ hold the icon for six touch samples
    blt     bomb_touch_sample__save_timer
    movs    r1, #2
    str     r1, [r5, #0x14]
    movs    r0, #0
bomb_touch_sample__save_timer:
    str     r0, [r5, #0x18]
    movs    r0, #224
    strh    r0, [r4]
    movs    r0, #56
    strh    r0, [r4, #2]
    movs    r0, #1
    strh    r0, [r4, #4]
    movs    r0, #0
    strh    r0, [r4, #6]
    b       bomb_touch_sample__exit
bomb_touch_sample__target:
    ldr     r0, [r5, #0x20]
    asrs    r0, r0, #8
    strh    r0, [r4]
    ldr     r0, [r5, #0x24]
    asrs    r0, r0, #8
    strh    r0, [r4, #2]
    movs    r0, #1
    strh    r0, [r4, #4]
    movs    r0, #0
    strh    r0, [r4, #6]
    ldr     r0, [r5, #0x1c]
    cmp     r0, #0
    bne     bomb_touch_sample__confirm
    cmp     r7, #0
    beq     bomb_touch_sample__confirm
    movs    r0, #2
    b       bomb_touch_sample__save_phase
bomb_touch_sample__confirm:
    movs    r0, #3
bomb_touch_sample__save_phase:
    str     r0, [r5, #0x14]
    b       bomb_touch_sample__exit

.org 0x3e4
bomb_touch_sample__reset:
    @ Keep a real touch unless a synthetic drag needs a release.
    ldr     r0, [r5, #0x14]
    cmp     r0, #0
    beq     bomb_touch_sample__clear
bomb_touch_sample__release:
    ldr     r0, [r5, #0x20]
    asrs    r0, r0, #8
    strh    r0, [r4]
    ldr     r0, [r5, #0x24]
    asrs    r0, r0, #8
    strh    r0, [r4, #2]
    movs    r0, #0
    strh    r0, [r4, #4]
    strh    r0, [r4, #6]
bomb_touch_sample__clear:
    movs    r0, #0
    str     r0, [r5, #0x14]
    str     r0, [r5, #0x18]
    str     r0, [r5, #0x1c]
    b       bomb_touch_sample__exit

.org 0x44c
bomb_shared_state:
    .long 0                    @ speed exhaustion latch
    .long 0                    @ previous physical buttons
    .long 0                    @ barrel-roll exhaustion latch
    .long 0                    @ last flight frame
    .long 0                    @ current ship
    .long 0                    @ bomb phase: idle, icon, target, release
    .long 0                    @ icon timer
    .long 0                    @ pending short-tap confirmation
    .long 0x8000               @ target X, 8.8 fixed point
    .long 0x6000               @ target Y, 8.8 fixed point
    .short 0, 0                @ saved ship Y/X input

.org 0x4a0
