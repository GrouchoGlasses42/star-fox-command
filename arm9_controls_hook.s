@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ 021e9d34 | 98 22 | movs   r2,#0x98
@ 021e9d36 | 8a 5e | ldrsh  r2,[r1,r2]
@ 021e9d38 | 02 80 | strh   r2,[r0,#0x0]
@ 021e9d3a | 9a 22 | movs   r2,#0x9a
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    
MovePlayerWithCPad:
    push    {r1-r5, lr}

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
    @ Sign extend Y & negate
    mov     r5, r5, asr #24
    rsb     r5, #0

    mov     r3, r4 @ X * 3
    lsl     r4, #1
    add     r4, r3
    mov     r3, r5 @ Y * 3
    lsl     r5, #1
    add     r5, r3
    
    @ 0x98, 0x9A: Y, X, offsets
    ldrsh   r2, [r1, #0x98]
    add     r2, r5
    strh    r2, [r1, #0x98]

    ldrsh   r2, [r1, #0x9A]
    add     r2, r4
    strh    r2, [r1, #0x9A]
    
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


@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ Replace the raw touch sample while the Y-button bomb control is active.
@ First Y press: touch the bomb icon and move the target to the radar center.
@ Second Y press, or 120 target frames: release the touch and detonate the bomb.
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
bomb_touch_sample:
    push    {r4-r8, lr}
    mov     r4, r0                  @ raw touch sample output

    @ Preserve the real stylus sample before deciding whether to replace it.
    ldr     r3, touch_sample_func
    blx     r3

    @ The barrel-roll hook records the last frame that flight code ran.
    @ Accept the current or previous frame to allow for input-update order.
    ldr     r0, frame_counter
    ldr     r1, [r0]
    ldr     r0, bomb_flight_frame
    sub     r1, r1, r0
    cmp     r1, #1
    bhi     bomb_touch_sample__outside_flight

    @ Convert the active-low Y bit to 0 or 1 and detect a new press.
    ldr     r0, ds_key_mirror
    ldrh    r0, [r0]
    mvn     r0, r0
    and     r0, r0, #0x800
    mov     r0, r0, lsr #11
    ldr     r1, bomb_y_held
    str     r0, bomb_y_held
    eor     r2, r0, r1
    and     r2, r2, r0

    ldr     r3, bomb_state
    cmp     r2, #0
    beq     bomb_touch_sample__continue
    cmp     r3, #0
    bne     bomb_touch_sample__release

    @ Start a new bomb drag at the bomb icon.
    mov     r3, #1
    str     r3, bomb_state
    mov     r0, #0
    str     r0, bomb_timer
    mov     r0, #0x8000             @ 128 in 8.8 fixed point
    str     r0, bomb_cursor_x
    mov     r0, #0x6000             @ 96 in 8.8 fixed point
    str     r0, bomb_cursor_y

bomb_touch_sample__continue:
    cmp     r3, #1
    beq     bomb_touch_sample__icon
    cmp     r3, #2
    beq     bomb_touch_sample__target
    b       bomb_touch_sample__exit

bomb_touch_sample__icon:
    ldr     r0, bomb_timer
    add     r0, r0, #1
    cmp     r0, #6                  @ about 100 ms at 60 frames per second
    movge   r1, #2
    strge   r1, bomb_state
    movge   r0, #0
    str     r0, bomb_timer

    mov     r0, #224                @ bomb icon
    strh    r0, [r4, #0]
    mov     r0, #56
    strh    r0, [r4, #2]
    mov     r0, #1                  @ stylus down
    strh    r0, [r4, #4]
    mov     r0, #0                  @ valid sample
    strh    r0, [r4, #6]
    b       bomb_touch_sample__exit

bomb_touch_sample__target:
    ldr     r0, bomb_timer
    add     r0, r0, #1
    cmp     r0, #120                @ about two seconds
    bge     bomb_touch_sample__release
    str     r0, bomb_timer

    @ Move an 8.8 fixed-point cursor with the C-Stick.
    ldr     r0, RTCom_Output
    ldrsh   r2, [r0, #6]            @ C-Stick X
    ldrsh   r3, [r0, #8]            @ C-Stick Y

    ldr     r0, bomb_cursor_x
    add     r0, r0, r2, lsl #3
    mov     r1, #0x3000             @ x minimum: 48
    cmp     r0, r1
    movlt   r0, r1
    mov     r1, #0xd000             @ x maximum: 208
    cmp     r0, r1
    movgt   r0, r1
    str     r0, bomb_cursor_x
    mov     r0, r0, asr #8
    strh    r0, [r4, #0]

    ldr     r0, bomb_cursor_y
    sub     r0, r0, r3, lsl #3
    mov     r1, #0x2800             @ y minimum: 40
    cmp     r0, r1
    movlt   r0, r1
    mov     r1, #0xb000             @ y maximum: 176
    cmp     r0, r1
    movgt   r0, r1
    str     r0, bomb_cursor_y
    mov     r0, r0, asr #8
    strh    r0, [r4, #2]

    mov     r0, #1                  @ stylus down
    strh    r0, [r4, #4]
    mov     r0, #0                  @ valid sample
    strh    r0, [r4, #6]
    b       bomb_touch_sample__exit

bomb_touch_sample__release:
    mov     r0, #0
    str     r0, bomb_state
    str     r0, bomb_timer
    strh    r0, [r4, #4]            @ stylus up
    strh    r0, [r4, #6]
    b       bomb_touch_sample__exit

bomb_touch_sample__outside_flight:
    mov     r0, #0
    str     r0, bomb_state
    str     r0, bomb_timer
    str     r0, bomb_y_held

bomb_touch_sample__exit:
    pop     {r4-r8, pc}

.align 2
touch_sample_func:      .long TOUCH_SAMPLE_FUNC_ADDR + 1
frame_counter:          .long 0x027ffc3c
ds_key_mirror:          .long 0x027fffa8
bomb_flight_frame:      .long 0
bomb_y_held:            .long 0
bomb_state:             .long 0
bomb_timer:             .long 0
bomb_cursor_x:          .long 0x00008000
bomb_cursor_y:          .long 0x00006000


@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ 022115be | 41 30 | adds r0,#0x41
@ 022115c0 | 00 78 | ldrb r0,[r0,#0x0]
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ activate barrel roll when A is held
barrel_roll_func:
    ldrb    r0, [r0, #0x41] @ overwritten opcode
    push    {r0-r7}

    @ Mark this frame as active flight code for the Y-button bomb hook.
    ldr     r0, frame_counter
    ldr     r0, [r0]
    str     r0, bomb_flight_frame

    @ get SuperState
    ldr     r0, [r4, #0x30]
    ldr     r6, [r0]

    @ Trigger the touchscreen maneuvers from the physical DPad.  KEYINPUT is
    @ deliberately used here instead of RTCom_Output, so the Circle Pad can
    @ never trigger either action.
    push    {lr}
    mov     r1, #0x4000000
    ldr     r0, [r1, #0x130]
    mvn     r0, r0
    and     r0, r0, #0xc0       @ Up (bit 6), Down (bit 7)
    ldr     r1, dpad_maneuver_buttons_held
    bic     r2, r0, r1          @ newly pressed buttons
    str     r0, dpad_maneuver_buttons_held

    tst     r2, #0x40
    bne     barrel_roll_func__loop
    tst     r2, #0x80
    bne     barrel_roll_func__uturn
    b       barrel_roll_func__maneuver_done

barrel_roll_func__loop:
    mov     r0, r6
    mov     r1, #0
    ldr     r3, loop_func
    blx     r3
    b       barrel_roll_func__maneuver_done

barrel_roll_func__uturn:
    mov     r0, r6
    mov     r1, #0
    ldr     r3, uturn_func
    blx     r3

barrel_roll_func__maneuver_done:
    pop     {lr}

    @ check if roll_btn is currently pressed
    mov     r1, #0x4000000
    ldr     r1, [r1, #0x130]
    mvn     r7, r1
    tst     r7, #0x1
    moveq   r1, #0
    movne   r1, #1
    
    @ old A state
    ldr     r3, is_roll_btn_held 

    @ is_released = is_held_old & (is_held_now ^ is_held_old) ; r3 = r3 & (r1 ^ r3)
    eor     r2, r1, r3
    and     r3, r2

    str     r1, is_roll_btn_held
    str     r3, is_roll_btn_released

    @ A is held
    cmp     r1, #0
    bne     barrel_roll_func__start_rolling
    @ A has been released
    cmp     r3, #0
    mov     r0, #0
    strne   r0, is_blocked
    bne     barrel_roll_func__stop_rolling
    b       barrel_roll_func__exit

barrel_roll_func__stop_rolling:
    mov     r2, #0
    strb    r2, [r6, #0x113]
    b       barrel_roll_func__exit

barrel_roll_func__start_rolling:
    @ check if we have enough energy to initiate the barrel roll
    ldr     r1, [r6, #0xbc] @ energy wasted currently
    ldr     r2, [r6, #0xc4] @ max energy
    cmp     r1, r2
    mov     r1, #1
    strge   r1, is_blocked

    ldr     r0, is_blocked
    cmp     r0, #0
    bne     barrel_roll_func__exit

    ldr     r4, RTCom_Output
    ldrsb   r4, [r4, #0]
    cmp     r4, #0
    addge   lr, #0x28
    addlt   lr, #0x4

barrel_roll_func__exit:
    pop     {r0-r7}
    bx      lr


is_roll_btn_held:       .long 0
is_roll_btn_released:   .long 0
is_blocked:             .long 0
dpad_maneuver_buttons_held: .long 0
loop_func:               .long LOOP_FUNC_ADDR + 1
uturn_func:              .long UTURN_FUNC_ADDR + 1

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@ source: https://web.archive.org/web/20110604163902/http://crackerscrap.com/docs/sfchacktut.html
@ 0x021EE4CC
boostbrake_func:
    ;@ Start of brake, boost handler
    push    {r0-r12,lr}
    mov     r1,#0x4000000
    ldr     r1,[r1,#0x130]		;@ read key register

    ;@ X is exposed through the DS-specific key mirror as bit 10. Replace the
    ;@ active-low A bit with it so the original X/B handler logic can be kept.
    ldr     r0,=0x027fffa8
    ldrh    r0,[r0]
    and     r0,r0,#0x400
    bic     r1,r1,#0x1
    orr     r1,r1,r0,lsr #10

    ;@ code to reset ability to brake or boost after x and/or b are released
    and     r0,r1,#0x3			;@ mask out everything but x, b
    eors    r0,#0x3				;@ toggle first two bits
    moveq   r0,#0x1				;@ if neither x nor b pressed reset flag to allow braking and boosting
    streq   r0,canuseboost
    ;@ code end
    ldr     r0,canuseboost
    cmp     r0,#0x0
    beq     noboost

    add     r4,#0x100			;@ increase pointer address
    mov     r0,#0x49000			;@ max boost used value - 0 = full meter
    ldr     r2,[r4,#-0x44]		;@ load current boost used value
    cmp     r2,r0				;@ compare the value to the max boost used
    movge   r0,#0x0				;@ no boost left
    movlt   r0,#0x1				;@ boost left
    str     r0,canuseboost		;@ save the flag to disable boost or brake
    bge     noboost

    ands    r0,r1,#0x3			;@ x + b pressed?
    streqb  r0,[r4,#0xf]		;@ turn brake flag off
    beq     onlyboost			;@ only boost

    and     r0,r1,#0x2			;@ b pressed? - brake
    lsr     r0,#0x1				;@ shift r0 one bit to the right - quick way of dividing by 2	
    eor     r0,#0x1				;@ invert value since 0 = button down, 1 = button up
    strb    r0,[r4,#0xf]		;@ store brake flag
onlyboost:
    ands    r0,r1,#0x1			;@ x - boost
    eor     r0,#0x1
    strb    r0,[r4,#0xe]       ;@ store boost flag
noboost:
    pop     {r0-r12,lr}
    ;@ patch 4 overwritten opcodes from 0x21ee4cc-0x21ee4d3
    ldrb    r3,[r4,r0]
    add     r0,#0x3
    add     r2,r4,r0
    mov     r1,#0xff
    ;@ patch end
    ldr     r0,bbreturn
    bx      r0

    bbreturn:       .long BOOSTBRAKE_RETURN_ADDR
    canuseboost:    .long 0x1
;@ End of brake, boost handler
