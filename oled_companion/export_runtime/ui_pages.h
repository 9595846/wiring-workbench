#ifndef OLED_UI_PAGES_H
#define OLED_UI_PAGES_H
#include <stdint.h>
/* Events map to debounced presses and individual rotary detents. */
enum { UI_KEY1, UI_KEY2, UI_KEY3, UI_KEY4, UI_LEFT, UI_RIGHT };
void ui_init(void);
void ui_draw(void);
void ui_event(unsigned event);
int32_t ui_get_variable(unsigned index);
int ui_set_variable(unsigned index, int32_t value);
unsigned ui_current_page(void);
int ui_current_dialog(void);
int32_t ui_input_value(void);
#endif
