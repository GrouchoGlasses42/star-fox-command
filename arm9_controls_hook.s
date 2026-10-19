@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ 021e9d34 | 98 22 | movs   r2,#0x98
@ 021e9d36 | 8a 5e | ldrsh  r2,[r1,r2]
@ 021e9d38 | 02 80 | strh   r2,[r0,#0x0]
@ 021e9d3a | 9a 22 | movs   r2,#0x9a
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    
MovePlayerWithCPad:
    push    {r1-r5, lr}
    ldr     r4, bomb_steering_gate_addr
    bx      r4

MovePlayerWithCPad__read_cpad:

    @ Get the stick values
    ldr     r4, RTCom_Output
    ldrh    r4, [r4, #0]
    cmp     r4, #0
    bne     Read_CPAD

    pop     {r1-r5, lr} @ don't use the CPad if it's not touched
    b       MovePlayerWithCPad_End

Read_CPAD:
    @ Split stick Y and X components
    mov     r5, r4, lsl #16
    @ Sign extend X
    mov     r4, r4, lsl #24
    mov     r4, r4, asr #24
    rsb     r4, #0
    @ Change only the vertical ship input. Bomb targeting has its own input.
    mov     r5, r5, asr #24
    .if INVERT_STEERING
    nop
    .else
    rsb     r5, #0
    .endif

    add     r4, r4, r4, lsl #1 @ X * 3
    add     r5, r5, r5, lsl #1 @ Y * 3
    
    @ 0x98, 0x9A: Y, X, offsets
    ldrsh   r2, [r1, #0x98]
    add     r2, r5
    strh    r2, [r1, #0x98]

    ldrsh   r2, [r1, #0x9A]
    add     r2, r4
    strh    r2, [r1, #0x9A]
    
MovePlayerWithCPad__restore_registers:
    pop     {r1-r5, lr}

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
MovePlayerWithCPad_End: 
    @ replaced opcodes
    movs    r2, #0x98
    ldrsh   r2, [r1, r2]
    strh    r2, [r0, #0x0]
    movs    r2, #0x9a

    ldr     r3, returnaddr
    bx      r3

    returnaddr:     .long MOVE_RETURN_ADDR
    RTCom_Output:   .long 0x027ffdf0
    bomb_steering_gate_addr: .long (bomb_steering_gate - MovePlayerWithCPad) + 0x02000001


@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ Use the Circle Pad for the bomb target without routing it into ship steering.
@ Hold Y to open the target. Move the Circle Pad while Y is held. Release Y to
@ deploy the bomb. Only the Y button and Circle Pad control this action.
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ 022115be | 41 30 | adds r0,#0x41
@ 022115c0 | 00 78 | ldrb r0,[r0,#0x0]
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ Use the existing flight callback and its valid SuperState pointer. Thumb
@ code keeps the meter checks inside the three established safe code ranges.
.syntax unified
.arch armv5te
.thumb
.org 0x8c
.thumb_func
barrel_roll_func:
    adds    r0, #0x41
    ldrb    r0, [r0]             @ overwritten instructions
    push    {r0-r7, lr}
    ldr     r0, [r4, #0x30]
    ldr     r6, [r0]

    ldr     r1, physical_key_register
    ldrh    r7, [r1]
    mvns    r7, r7
    ldr     r2, ds_key_mirror_core
    ldrh    r2, [r2]
    mvns    r2, r2
    lsls    r2, r2, #21
    lsrs    r2, r2, #31         @ X -> bit 0
    movs    r1, #2
    ands    r1, r7              @ B -> bit 1
    orrs    r2, r1

    @ Match the held-input/release-to-rearm behavior. Once energy is spent,
    @ both speed buttons must be released. Also respect the game's exhaustion
    @ latch (0x10c) and per-ship maximum (0xc4), rather than a fixed threshold.
    ldr     r4, flight_control_state_addr
    ldr     r0, [r4]
    cmp     r2, #0
    bne     barrel_roll_func__check_meter
    movs    r0, #0
barrel_roll_func__check_meter:
    movs    r1, #0xff
    adds    r1, #0x0d
    ldrb    r1, [r6, r1]
    orrs    r0, r1
    movs    r3, r6
    adds    r3, #0xbc
    ldr     r1, [r3]
    ldr     r3, [r3, #8]
    cmp     r1, r3
    blt     barrel_roll_func__meter_checked
    movs    r0, #1
barrel_roll_func__meter_checked:
    str     r0, [r4]
    cmp     r0, #0
    beq     barrel_roll_func__speed_allowed
    movs    r2, #0              @ clear both flags when blocked
barrel_roll_func__speed_allowed:
    cmp     r2, #3
    bne     barrel_roll_func__write_speed
    movs    r2, #1              @ Boost takes priority over Brake
barrel_roll_func__write_speed:
    movs    r1, r2
    movs    r0, #1
    ands    r1, r0
    movs    r0, r6
    adds    r0, #0xff
    adds    r0, #0x0f
    strb    r1, [r0]            @ native held Boost (0x10e)
    lsrs    r2, r2, #1
    strb    r2, [r0, #1]        @ native held Brake (0x10f)
    b       barrel_roll_func__maneuvers

.org 0xf4
barrel_roll_func__maneuvers:
    ldr     r0, flight_frame_counter
    ldr     r0, [r0]
    str     r0, [r4, #0x0c]
    str     r6, [r4, #0x10]
    ldr     r5, [r4, #4]
    str     r7, [r4, #4]
    movs    r0, r7
    bics    r0, r5              @ new physical D-Pad presses only
    movs    r1, #0x40
    tst     r0, r1
    beq     barrel_roll_func__check_down
    ldr     r3, loop_func
    b       barrel_roll_func__call_maneuver
barrel_roll_func__check_down:
    movs    r1, #0x80
    tst     r0, r1
    beq     barrel_roll_func__buttons
    ldr     r3, uturn_func
barrel_roll_func__call_maneuver:
    movs    r0, r6
    movs    r1, #0
    blx     r3
barrel_roll_func__buttons:
    .if ROLL_ON_SHOULDERS
    movs    r0, #3
    lsls    r0, r0, #8          @ either L or R
    .else
    movs    r0, #1
    .endif
    tst     r7, r0
    bne     barrel_roll_func__start_rolling
    tst     r5, r0
    beq     barrel_roll_func__exit
    movs    r0, #0
    str     r0, [r4, #8]
    movs    r1, r6
    adds    r1, #0xff
    adds    r1, #0x14
    strb    r0, [r1]            @ stop when all roll buttons are released
    b       barrel_roll_func__exit

.org 0x14c
barrel_roll_func__start_rolling:
    movs    r3, r6
    adds    r3, #0xbc
    ldr     r1, [r3]
    ldr     r2, [r3, #8]
    cmp     r1, r2
    blt     barrel_roll_func__check_roll_block
    movs    r0, #1
    str     r0, [r4, #8]
barrel_roll_func__check_roll_block:
    ldr     r0, [r4, #8]
    cmp     r0, #0
    bne     barrel_roll_func__exit
    ldr     r3, flight_cpad_output
    movs    r1, #0
    ldrsb   r0, [r3, r1]
    cmp     r0, #0
    ldr     r0, [sp, #32]
    blt     barrel_roll_func__roll_left
    adds    r0, #0x28
    b       barrel_roll_func__save_return
barrel_roll_func__roll_left:
    adds    r0, #4
barrel_roll_func__save_return:
    str     r0, [sp, #32]
barrel_roll_func__exit:
    pop     {r0-r7, pc}

.align 2
physical_key_register:   .long 0x04000130
flight_control_state_addr: .long bomb_shared_state + 0x02000000
flight_cpad_output:      .long 0x027ffdf0
loop_func:               .long LOOP_FUNC_ADDR + 1
uturn_func:              .long UTURN_FUNC_ADDR + 1
ds_key_mirror_core:      .long 0x027fffa8
flight_frame_counter:    .long 0x027ffc3c

@ Keep the protected secure-area service entry outside generated code.
.org 0x1c4
.include "arm9_bomb_hook.s"
