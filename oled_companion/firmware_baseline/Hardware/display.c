#ifndef MAZE_HOST_VIEW
#include "stm32f10x.h"
#include "platform.h"
#endif
#include "display.h"
#include "font.h"
#include "zh12.h"
#include <string.h>
static uint8_t frame[1024];
#ifndef MAZE_HOST_VIEW
#define SCL GPIO_Pin_10
#define SDA GPIO_Pin_11
static uint8_t sent[1024],online,address=0x3Cu;
static uint32_t retry;static unsigned chunk;
static void data(int high){if(high){GPIOB->BSRR=SDA;}else{GPIOB->BRR=SDA;}delay_us(2u);}
static void low(void){GPIOB->BRR=SCL;delay_us(2u);}
static int high(void){uint32_t begin=millis();GPIOB->BSRR=SCL;while(!(GPIOB->IDR&SCL)){if((uint32_t)(millis()-begin)>=2u){return 0;}}delay_us(2u);return 1;}
static int byte(uint8_t v)
{unsigned i;int ack;for(i=0u;i<8u;i++){data((v&128u)!=0u);if(!high()){return 0;}low();v<<=1;}data(1);if(!high()){return 0;}ack=(GPIOB->IDR&SDA)==0u;low();return ack;}
static int write(const uint8_t *p,unsigned n)
{
    unsigned i;int ok;
    data(1);ok=high()&&((GPIOB->IDR&SDA)!=0u);
    if(ok){data(0);low();ok=byte((uint8_t)(address<<1));}
    for(i=0u;ok&&i<n;i++){ok=byte(p[i]);}
    low();data(0);if(!high()){ok=0;}data(1);
    return ok&&((GPIOB->IDR&SDA)!=0u);
}
void display_init(void)
{
    GPIO_InitTypeDef g;RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB,ENABLE);
    GPIOB->BSRR=SCL|SDA;g.GPIO_Pin=SCL|SDA;g.GPIO_Speed=GPIO_Speed_2MHz;g.GPIO_Mode=GPIO_Mode_Out_OD;GPIO_Init(GPIOB,&g);
    memset(frame,0,sizeof(frame));memset(sent,0xFF,sizeof(sent));online=0u;retry=0u;chunk=0u;
}
uint8_t display_online(void){return online;}
#else
static unsigned clipped_text;
void display_init(void){memset(frame,0,sizeof(frame));clipped_text=0u;}
uint8_t display_online(void){return 1u;}
const uint8_t *display_framebuffer(void){return frame;}
unsigned display_clipped_text(void){return clipped_text;}
#endif
void display_clear(void){memset(frame,0,sizeof(frame));
#ifdef MAZE_HOST_VIEW
clipped_text=0u;
#endif
}
void display_pixel(int x,int y,uint8_t on)
{uint8_t *p;if(x<0||x>=128||y<0||y>=64){return;}p=&frame[(unsigned)(y/8)*128u+(unsigned)x];if(on){*p|=(uint8_t)(1u<<(y%8));}else{*p&=(uint8_t)~(1u<<(y%8));}}
void display_box(int x,int y,int w,int h,uint8_t fill)
{int i,j;for(j=0;j<h;j++){for(i=0;i<w;i++){if(fill||i==0||j==0||i==w-1||j==h-1){display_pixel(x+i,y+j,1u);}}}}
static uint16_t next_code(const unsigned char **p)
{
    const unsigned char *s=*p;uint16_t v;
    if(*s<128u){*p=s+1;return *s;}
    if(s[0]>=0xE0u&&s[0]<=0xEFu&&s[1]&&s[2]&&(s[1]&0xC0u)==0x80u&&(s[2]&0xC0u)==0x80u){
        v=(uint16_t)(((s[0]&15u)<<12)|((s[1]&63u)<<6)|(s[2]&63u));
        if(v>=0x800u&&(v<0xD800u||v>0xDFFFu)){*p=s+3;return v;}
    }
    *p=s+1;return '?';
}
unsigned display_text_width(const char *s)
{const unsigned char *p=(const unsigned char *)s;unsigned width=0u;while(*p){width+=next_code(&p)<128u?6u:12u;}return width;}
void display_text(unsigned x,unsigned y,const char *s)
{
    const unsigned char *p=(const unsigned char *)s;
    while(*p){uint16_t code=next_code(&p);unsigned i,j,width=code<128u?6u:12u;
        if(x+width>128u||y+(code<128u?7u:12u)>64u){
#ifdef MAZE_HOST_VIEW
            clipped_text++;
#endif
            return;
        }
        if(code>=128u){
            const Zh12 *glyph=0;
            for(i=0u;i<sizeof(zh12)/sizeof(zh12[0]);i++){if(zh12[i].code==code){glyph=&zh12[i];break;}}
            if(glyph){for(j=0u;j<12u;j++){for(i=0u;i<12u;i++){if(glyph->rows[j]&(0x8000u>>i)){display_pixel((int)(x+i),(int)(y+j),1u);}}}}
            else{display_box((int)x,(int)y,11,11,0u);}
        }else{char c=(char)code;if(c>='a'&&c<='z'){c=(char)(c-'a'+'A');}for(i=0u;i<5u;i++){
        uint8_t v=0u;if(c>='A'&&c<='Z'){v=g_letters[c-'A'][i];}else if(c>='0'&&c<='9'){v=g_digits[c-'0'][i];}
        else if(c==':'){v=i==2u?0x24u:0u;}else if(c=='/'){v=(uint8_t)(1u<<(6u-i));}else if(c=='-'){v=8u;}else if(c=='='){v=0x14u;}
        else if(c=='.'){v=i==2u?0x40u:0u;}
        for(j=0u;j<7u;j++){if(v&(1u<<j)){display_pixel((int)(x+i),(int)(y+j),1u);}}
        }}x+=width;
    }
}
#ifndef MAZE_HOST_VIEW
void display_task(uint32_t now)
{
    static const uint8_t init[]={0,0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0,0x40,0x8D,0x14,0x20,0x02,0xA1,0xC8,0xDA,0x12,0x81,0x7F,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF};
    unsigned attempt;
    if(!online){if((int32_t)(now-retry)<0){return;}retry=now+2000u;
        address=0x3Cu;if(!write(init,sizeof(init))){address=0x3Du;if(!write(init,sizeof(init))){return;}}
        online=1u;memset(sent,0xFF,sizeof(sent));
    }
    for(attempt=0u;attempt<64u;attempt++){
        unsigned offset=chunk*16u,col=offset%128u;uint8_t command[4],payload[17];chunk=(chunk+1u)%64u;
        if(!memcmp(frame+offset,sent+offset,16u)){continue;}
        command[0]=0u;command[1]=(uint8_t)(0xB0u+offset/128u);command[2]=(uint8_t)(col&15u);command[3]=(uint8_t)(0x10u|(col>>4));
        payload[0]=0x40u;memcpy(payload+1,frame+offset,16u);
        if(!write(command,4u)||!write(payload,17u)){online=0u;retry=now+2000u;return;}
        memcpy(sent+offset,frame+offset,16u);return;
    }
}
#else
void display_task(uint32_t now){(void)now;}
#endif
