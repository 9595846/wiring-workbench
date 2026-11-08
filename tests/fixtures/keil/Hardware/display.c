/* Static scanner fixture only; not standalone buildable firmware. */
#define OLED_SCL GPIO_Pin_10
#define OLED_SDA GPIO_Pin_11
void OLED_Init(void) {
    GPIO_InitTypeDef gpio;
    gpio.GPIO_Pin = OLED_SCL | OLED_SDA;
    gpio.GPIO_Mode = GPIO_Mode_Out_OD;
    GPIO_Init(GPIOB, &gpio);
}
