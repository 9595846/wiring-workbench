#ifndef DEFUSE_CONTROLS_H
#define DEFUSE_CONTROLS_H
#include <stdint.h>
void controls_init(void);
unsigned buttons_task(uint32_t now);
int encoder_delta(void);
int light_init(void);
int light_read(uint16_t *value);
void beep(uint32_t now);
void led2_set(unsigned on);
void outputs_task(uint32_t now);
void servo_set(unsigned enabled, unsigned pulse);
#endif
