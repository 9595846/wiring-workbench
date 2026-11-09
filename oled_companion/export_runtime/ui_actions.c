#include "ui_assets.h"
#include "ui_pages.h"
static const unsigned variable_count=UI_VAR_COUNT;
static int32_t values[UI_VAR_STORAGE];
static unsigned page;
static int dialog;
static int32_t input;
static int32_t clamp(int32_t v,int32_t lo,int32_t hi)
{ return v<lo?lo:(v>hi?hi:v); }
void ui_init(void)
{
    unsigned i;
    for(i=0;i<variable_count;i++){values[i]=ui_initial[i];}
    page=UI_START_PAGE;dialog=-1;input=0;
}
int32_t ui_get_variable(unsigned index){return index<variable_count?values[index]:0;}
int ui_set_variable(unsigned index,int32_t value)
{
    if(index>=variable_count){return 0;}
    values[index]=clamp(value,-999999,999999);return 1;
}
unsigned ui_current_page(void){return page;}
int ui_current_dialog(void){return dialog;}
int32_t ui_input_value(void){return input;}
static void apply(UiAction a)
{
    const UiDialog *d;
    switch(a.kind){
    case 1:dialog=-1;break;
    case 2:
        dialog=a.target;d=&ui_dialogs[dialog];
        input=clamp(values[d->variable],d->minimum,d->maximum);break;
    case 3:page=(unsigned)a.target;dialog=-1;break;
    case 4:values[a.target]=clamp(a.value,-999999,999999);break;
    case 5:values[a.target]=clamp(values[a.target]+a.value,-999999,999999);break;
    default:break;
    }
}
void ui_event(unsigned event)
{
    const UiDialog *d;
    UiAction a;
    if(event>=6u){return;}
    if(dialog>=0){
        d=&ui_dialogs[dialog];
        if(d->number&&(event==UI_LEFT||event==UI_RIGHT)){
            input=clamp(input+(event==UI_RIGHT?d->step:-d->step),d->minimum,d->maximum);return;
        }
        if(event!=UI_KEY1&&event!=UI_KEY2){return;}
        if(event==UI_KEY1&&d->number){values[d->variable]=clamp(input,d->minimum,d->maximum);}
        a=event==UI_KEY1?d->confirm:d->cancel;dialog=-1;apply(a);return;
    }
    apply(ui_bindings[page][event]);
}
