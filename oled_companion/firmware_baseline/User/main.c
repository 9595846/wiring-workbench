/* Set OLED_ONLY_TEST to 0 to restore the complete five-page application. */
#define OLED_ONLY_TEST 0
#if OLED_ONLY_TEST && !defined(DEFUSE_HOST_TEST)
#include "platform.h"
#include "display.h"
#include "ui_pages.h"
int main(void)
{
    platform_init();
    display_init();
    ui_init();
    ui_draw();
    for(;;){display_task(millis());}
}
#else
#include "platform.h"
#include "controls.h"
#include "display.h"
#include "imu.h"
#include "check_i2c.h"
#include "ui_text.h"
#include "ui_assets.h"
#include "ui_pages.h"
#include <stdio.h>
#include <string.h>

static Imu imu;
static unsigned page,last_key,servo_on,pulse=1500u,light_ok;
static uint16_t raw,filtered;
static uint32_t samples,servo_at,light_at;
static int encoder_count;
static char input[64];static unsigned used,discard;

static void stop_servo(void){servo_on=0u;servo_set(0u,pulse);}
static void change_page(unsigned p){stop_servo();ui_init();page=p;}
static void start_servo(uint32_t now){pulse=1500u;servo_at=now;servo_on=1u;servo_set(1u,pulse);}
static void servo_task(uint32_t now)
{if(servo_on&&(uint32_t)(now-servo_at)>=15000u){stop_servo();console_write("SERVO OFF AUTO_TIMEOUT\r\n");}}
static void set_pulse(unsigned p,uint32_t now)
{pulse=p;servo_at=now;servo_set(1u,pulse);}
static int fresh(uint32_t now){return imu.online&&samples&&(uint32_t)(now-imu.last_good)<300u;}
static void status(uint32_t now)
{
    char b[256];
    sprintf(b,"STATUS PAGE=%u OLED=%u MPU_ID=%02X MPU=%d SAMPLES=%lu AGE_MS=%lu ERR=%lu TX_DROP=%u\r\n",
        page+1u,display_online(),imu.id,fresh(now),(unsigned long)samples,
        (unsigned long)(samples?now-imu.last_good:0u),(unsigned long)imu.errors,console_dropped());console_write(b);
    sprintf(b,"DATA AX=%d AY=%d AZ=%d GX=%d GY=%d GZ=%d LIGHT_OK=%u RAW=%u FILTER=%u ENC=%d KEY=%u SERVO=%u PULSE_US=%u\r\n",
        imu.a[0],imu.a[1],imu.a[2],imu.g[0],imu.g[1],imu.g[2],
        light_ok&&((uint32_t)(now-light_at)<300u),raw,filtered,encoder_count,last_key,servo_on,pulse);console_write(b);
}
static void command(char *s,uint32_t now)
{
    unsigned i,p;
    for(i=0;s[i];i++){if(s[i]>='a'&&s[i]<='z'){s[i]=(char)(s[i]-'a'+'A');}}
    if(!strcmp(s,"HELP")){console_write("HELP STATUS PAGE 1..5 BEEP LED2 ON/OFF ENC ZERO IMU RETRY\r\nSERVO ON | SERVO OFF | SERVO US 1400..1600 (exactly four digits)\r\nServo: no horn first; independent supply/common GND; 15s idle auto-off.\r\n");}
    else if(!strcmp(s,"STATUS")){status(now);}
    else if(strlen(s)==6u&&!strncmp(s,"PAGE ",5u)&&s[5]>='1'&&s[5]<='5'){change_page((unsigned)(s[5]-'1'));console_write("OK PAGE; SERVO OFF\r\n");}
    else if(!strcmp(s,"BEEP")){beep(now);console_write("OK BEEP 80MS\r\n");}
    else if(!strcmp(s,"LED2 ON")){led2_set(1u);console_write("OK LED2 ON\r\n");}
    else if(!strcmp(s,"LED2 OFF")){led2_set(0u);console_write("OK LED2 OFF\r\n");}
    else if(!strcmp(s,"ENC ZERO")){encoder_count=0;console_write("OK ENC ZERO\r\n");}
    else if(!strcmp(s,"IMU RETRY")){stop_servo();samples=0u;imu_init(&imu);console_write("IMU INIT DONE; SEND STATUS\r\n");}
    else if(!strcmp(s,"SERVO OFF")){stop_servo();console_write("OK SERVO OFF\r\n");}
    else if(!strcmp(s,"SERVO ON")){page=3u;start_servo(now);console_write("OK SERVO ON 1500US; 15S IDLE TIMEOUT\r\n");}
    else if(!strncmp(s,"SERVO US ",9u)){
        p=0u;if(strlen(s)!=13u){console_write("ERR PULSE FORMAT\r\n");return;}
        for(i=9u;i<13u;i++){if(s[i]<'0'||s[i]>'9'){console_write("ERR PULSE FORMAT\r\n");return;}p=p*10u+(unsigned)(s[i]-'0');}
        if(p<1400u||p>1600u){console_write("ERR RANGE 1400..1600\r\n");}
        else if(!servo_on){console_write("ERR SEND SERVO ON FIRST\r\n");}
        else{set_pulse(p,now);console_write("OK PULSE\r\n");}
    }else{console_write("ERR UNKNOWN COMMAND; SEND HELP\r\n");}
}
static void rx_byte(uint8_t c,uint32_t now)
{
    if(c=='\r'||c=='\n'){
        if(discard){discard=0u;used=0u;return;}
        if(used){input[used]=0;command(input,now);}used=0u;return;
    }
    if(discard){return;}
    if(c==8u||c==127u){if(used){used--;}return;}
    if(c<32u||c>126u){discard=1u;used=0u;console_write("ERR ASCII ONLY; RESEND AFTER ENTER\r\n");return;}
    if(used>=sizeof(input)-1u){discard=1u;used=0u;console_write("ERR INPUT TOO LONG; RESEND AFTER ENTER\r\n");return;}
    input[used++]=(char)c;
}
static void handle_keys(unsigned keys,uint32_t now)
{
    static const unsigned pins[4]={12u,15u,8u,9u};unsigned i;char b[48];
    for(i=0;i<4u;i++){if(keys&(1u<<i)){last_key=i+1u;sprintf(b,"KEY K%u PB%u\r\n",i+1u,pins[i]);console_write(b);}}
    if(keys&8u){change_page((page+1u)%5u);return;}
    if(page==4u){
        int dialog=ui_current_dialog();
        if(keys&2u){stop_servo();ui_event(UI_KEY2);return;}
        if(keys&1u){
            if(dialog<0){stop_servo();ui_event(UI_KEY1);return;}
            ui_event(UI_KEY1);
#ifdef UI_VAR_NAME_pulse_us
            if(ui_dialogs[dialog].number && ui_dialogs[dialog].variable==UI_VAR_NAME_pulse_us){
                int32_t requested=ui_get_variable(UI_VAR_NAME_pulse_us);
                if(requested>=1400 && requested<=1600){servo_on=1u;set_pulse((unsigned)requested,now);}
                else{stop_servo();}
            }
#endif
        }else if(keys&4u){ui_event(UI_KEY3);}
        return;
    }
    if(page==3u){
        if(keys&2u){stop_servo();return;}
        if(keys&1u){if(servo_on){stop_servo();}else{start_servo(now);}}
        if(keys&4u){beep(now);}
    }
}
static void rotate(int delta,uint32_t now)
{
    int p;if(!delta){return;}
    encoder_count+=delta;if(encoder_count>9999){encoder_count=9999;}if(encoder_count< -9999){encoder_count=-9999;}
    if(page==4u){
        unsigned steps=(unsigned)(delta<0?-(long)delta:delta);
        if(steps>32u){steps=32u;}
        while(steps--){ui_event(delta>0?UI_RIGHT:UI_LEFT);}
        return;
    }
    if(page==3u&&servo_on){p=(int)pulse+delta*10;if(p<1400){p=1400;}if(p>1600){p=1600;}set_pulse((unsigned)p,now);}
}
static void draw(uint32_t now)
{
    char b[64];
    if(page==4u){
#ifdef UI_VAR_NAME_output_us
        ui_set_variable(UI_VAR_NAME_output_us,servo_on?(int32_t)pulse:0);
#endif
        ui_draw();return;
    }
    display_clear();
    if(page==0u){
        display_text(0,0,UI_TITLE);display_text(0,16,UI_INPUT);
        sprintf(b,"K%u ENC:%d",last_key,encoder_count);display_text(0,32,b);
        display_text(0,48,UI_NEXT);
    }else if(page==1u){
        display_text(0,0,UI_LIGHT);
        sprintf(b,"RAW:%u AVG:%u",raw,filtered);display_text(0,16,b);
        display_text(0,32,light_ok&&((uint32_t)(now-light_at)<300u)?UI_COVER:UI_ADC_BAD);
        display_text(0,48,UI_NEXT);
    }else if(page==2u){
        display_text(0,0,fresh(now)?UI_IMU_OK:UI_IMU_BAD);
        sprintf(b,"AX%6d AY%6d",imu.a[0],imu.a[1]);display_text(0,16,b);
        sprintf(b,"AZ%6d ID:%02X",imu.a[2],imu.id);display_text(0,32,b);
        sprintf(b,"N:%lu E:%lu",(unsigned long)(samples%100000u),(unsigned long)(imu.errors%100000u));display_text(0,48,b);
    }else{
        display_text(0,0,servo_on?UI_SERVO_ON:UI_SERVO_OFF);
        sprintf(b,"PWM:%uus",pulse);display_text(0,16,b);
        display_text(0,32,UI_SERVO_KEYS);display_text(0,48,UI_SERVO_KNOB);
    }
}
#ifndef DEFUSE_HOST_TEST
int main(void)
{
    uint32_t sample_at=0u,draw_at=0u;unsigned light_seen=0u;
    platform_init();controls_init();display_init();ui_init();light_init();imu_init(&imu);
    console_write("DEFUSE BOX BASE V1.2 SERVO UI READY; UART=115200 8N1\r\nMPU PB6/PB7; OLED PB10/PB11; LIGHT PA1; SERVO PA8 OFF\r\nKEY1 PB12 KEY2 PB15 KEY3 PB8 KEY4 PB9; SEND HELP\r\n");
    for(;;){
        uint32_t now=millis();uint8_t c;unsigned n,keys;uint16_t value;
        if(console_error()){used=0u;discard=1u;console_write("ERR RX OVERFLOW; ENTER THEN RESEND\r\n");}
        for(n=0u;n<32u&&console_read(&c);n++){rx_byte(c,millis());}
        now=millis();keys=buttons_task(now);handle_keys(keys,now);rotate(encoder_delta(),now);
        now=millis();servo_task(now);outputs_task(now);
        if((uint32_t)(now-sample_at)>=20u){sample_at=now;
            if(imu_sample(&imu,now)){samples++;}
            if(light_read(&value)){raw=value;filtered=light_seen?(uint16_t)(((uint32_t)filtered*7u+value)/8u):value;light_seen=1u;light_ok=1u;light_at=millis();}
        }
        now=millis();if((uint32_t)(now-draw_at)>=100u){draw_at=now;draw(now);}display_task(now);
    }
}
#endif

#endif /* OLED_ONLY_TEST */
