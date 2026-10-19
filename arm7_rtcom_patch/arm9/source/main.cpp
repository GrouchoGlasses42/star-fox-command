#define ARM9

#include <stdio.h>

#include "sys/_stdint.h"
#include <nds.h>

#define RTCOM_DATA_OUTPUT 0x0C7FFDF0

void visualizeCPad(u16 cpadX, u16 cpadY) {
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glOrtho(-128, 128, -96, 96, 0.1, 100);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();

    // not a real gl function and will likely change
    glPolyFmt(POLY_ALPHA(31) | POLY_CULL_NONE);

    glPushMatrix();
    glScalef32(128 * 4096, 128 * 4096, 4096);

    *(vu32 *)0x040004A8 = 0;
    // draw the obj
    glBegin(GL_QUAD);
    glColor3b(255, 255, 255);
    glVertex3v16(-2048, -2048, inttov16(-3));
    glVertex3v16(2048, -2048, inttov16(-3));
    glVertex3v16(2048, 2048, inttov16(-3));
    glVertex3v16(-2048, 2048, inttov16(-3));
    glEnd();

    glBegin(GL_TRIANGLE);
    glColor3b(255, 0, 0);
    glVertex3v16(0, 0, inttov16(-2));
    glVertex3v16(cpadX - 2048, cpadY - 2048, inttov16(-2));
    glVertex3v16(0, 0, inttov16(-2));

    glEnd();

    glPopMatrix(1);
    glPushMatrix();
    glTranslatef32(0, -80 * 4096, 4096);
    glScalef32(128 * 4096, 16 * 4096, 4096);

    glBegin(GL_QUAD);
    glColor3b(255, 0, 0);
    glVertex3v16(-2048, 2048, inttov16(-2));
    glVertex3v16(-2048, -2048, inttov16(-2));
    glVertex3v16(cpadX - 2048, -2048, inttov16(-2));
    glVertex3v16(cpadX - 2048, 2048, inttov16(-2));
    glEnd();

    glPopMatrix(1);
    glPushMatrix();
    glTranslatef32(100 * 4096, 0, 4096);
    glScalef32(16 * 4096, 128 * 4096, 4096);

    glBegin(GL_QUAD);
    glColor3b(255, 0, 0);
    glVertex3v16(-2048, cpadY - 2048, inttov16(-2));
    glVertex3v16(-2048, -2048, inttov16(-2));
    glVertex3v16(2048, -2048, inttov16(-2));
    glVertex3v16(2048, cpadY - 2048, inttov16(-2));
    glEnd();

    glPopMatrix(1);
    glFlush(0);
}

int main() {
    consoleDemoInit(); // setup the sub screen for printing

    // set mode 0, enable BG0 and set it to 3D
    videoSetMode(MODE_0_3D);

    // initialize gl
    glInit();

    // setup the rear plane
    glClearColor(0, 0, 0, 31); // BG must be opaque for AA to work
    glClearPolyID(63);         // BG must have a unique polygon ID for AA to work
    glClearDepth(0x7FFF);

    while (true) {
        glViewport(0, 0, 255, 191);

        u32 cpad = *(vu32 *)RTCOM_DATA_OUTPUT;
        u16 cpadX = (s8)(cpad & 0xFF) << 4;
        u16 cpadY = (s8)((cpad >> 8) & 0xFF) << 4;
        cpadX += 0x800, cpadY += 0x800;
        visualizeCPad(cpadX, cpadY);
        iprintf("\x1b[%d;0H\t CPAD: %+05d, %+05d", 2, (cpadX - 0x800) >> 4, (cpadY - 0x800) >> 4);

        scanKeys();
        if (keysHeld() & KEY_B) {
            printf("\x1b[13;0HButton B is down    \n");
        } else {
            printf("\x1b[13;0HButton B is NOT down\n");
        }

        u8 *date_time = (u8 *)(RTCOM_DATA_OUTPUT - 8);
        u8 year = date_time[0], month = date_time[1], day = date_time[2];
        u8 dow = date_time[3];
        u8 hour = date_time[4], minute = date_time[5], second = date_time[6];
        iprintf("\x1b[%d;0H\x1b[2K Date: %02x; %02x; %02x; %02x\n", 11, year, month, day, dow);
        iprintf("\x1b[%d;0H\x1b[2K Time: %02x; %02x; %02x\n", 12, hour, minute, second);

        swiWaitForVBlank();
    }

    return 0;
}
