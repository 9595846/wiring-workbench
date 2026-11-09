#ifndef MAZE_DISPLAY_H
#define MAZE_DISPLAY_H
#include <stdint.h>
void display_init(void);
void display_task(uint32_t now);
uint8_t display_online(void);
void display_clear(void);
void display_pixel(int x,int y,uint8_t on);
void display_text(unsigned x,unsigned y,const char *s);
void display_box(int x,int y,int w,int h,uint8_t fill);
unsigned display_text_width(const char *s);
#ifdef MAZE_HOST_VIEW
const uint8_t *display_framebuffer(void);
unsigned display_clipped_text(void);
#endif
#endif
