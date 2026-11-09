#include "ui_assets.h"
#include "ui_pages.h"
#include "display.h"
static int glyph(int x,int y,unsigned id)
{
    unsigned i,j;const UiGlyph *g=&ui_glyphs[id];
    for(j=0;j<g->height;j++){for(i=0;i<g->width;i++){
        if(g->rows[j]&(0x8000u>>i)){display_pixel(x+(int)i,y+(int)j,1u);}
    }}return x+(int)g->width;
}
static int number(int x,int y,int32_t value)
{
    char digits[8];unsigned n=0;
    if(value<0){x=glyph(x,y,UI_MINUS);value=-value;}
    do{digits[n++]=(char)(value%10);value/=10;}while(value);
    while(n){x=glyph(x,y,ui_digits[(unsigned)digits[--n]]);}return x;
}
static void text(int x,int y,const UiText *t)
{
    unsigned i;int token;
    for(i=0;i<t->length;i++){
        token=t->tokens[i];
        x=token<0?number(x,y,ui_get_variable((unsigned)(-token-1))):glyph(x,y,(unsigned)token);
    }
}
void ui_draw(void)
{
    unsigned i,x,y,bit;int dialog;const UiPage *p;const UiElement *e;const UiDialog *d;
    display_clear();p=&ui_pages[ui_current_page()];
    for(i=0;i<p->count;i++){
        e=&ui_elements[p->first+i];
        if(e->kind==0){text(e->x,e->y,&ui_texts[e->ref]);}
        else{for(y=0;y<(unsigned)e->h;y++){for(x=0;x<(unsigned)e->w;x++){
            bit=y*e->w+x;
            display_pixel(e->x+(int)x,e->y+(int)y,(uint8_t)((ui_images[e->ref][bit/8u]>>(7u-bit%8u))&1u));
        }}}
    }
    dialog=ui_current_dialog();if(dialog<0){return;}d=&ui_dialogs[dialog];
    for(y=0;y<(unsigned)d->h;y++){for(x=0;x<(unsigned)d->w;x++){
        display_pixel(d->x+(int)x,d->y+(int)y,(uint8_t)(x==0||y==0||x==(unsigned)d->w-1u||y==(unsigned)d->h-1u));
    }}
    text(d->x+4,d->y+4,&ui_texts[d->title]);
    if(d->number){number(d->x+4,d->y+18,ui_input_value());}
    text(d->x+4,d->y+d->h-13,&ui_texts[UI_DIALOG_FOOTER]);
}

