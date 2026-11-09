"""Illustrated suite launcher; closing apps always uses their normal close flow."""
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import suite_control

ROOT=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]/'deliverables/WorkbenchSuite'
ASSETS=Path(__file__).resolve().parent/'assets/launcher'

class Action(tk.Canvas):
    def __init__(self,parent,title,subtitle,command,kind='wire',primary=False,compact=False):
        self.w,self.h=456,56 if compact else 86
        super().__init__(parent,width=self.w,height=self.h,bg='#f6eddf',highlightthickness=0,takefocus=True,cursor='hand2')
        self.title,self.subtitle,self.command,self.kind=title,subtitle,command,kind
        self.primary,self.compact,self.hover,self.pressed,self.focused=primary,compact,False,False,False
        self.bind('<Enter>',lambda e:self.change(hover=True));self.bind('<Leave>',lambda e:self.change(hover=False,pressed=False))
        self.bind('<ButtonPress-1>',lambda e:self.change(pressed=True))
        self.bind('<ButtonRelease-1>',self.release)
        self.bind('<FocusIn>',lambda e:self.change(focused=True));self.bind('<FocusOut>',lambda e:self.change(focused=False))
        self.bind('<Return>',lambda e:self.command());self.bind('<space>',lambda e:self.command())
        self.draw()
    def change(self,**changes):
        for k,v in changes.items():setattr(self,k,v)
        self.draw()
    def release(self,e):
        invoke=self.pressed and 0<=e.x<self.w and 0<=e.y<self.h
        self.change(pressed=False)
        if invoke:self.focus_set();self.command()
    def draw(self):
        self.delete('all');shift=1 if self.pressed else 0
        fill=('#19392f' if self.pressed else '#2e5b49' if self.hover else '#23483d') if self.primary else ('#e6ded0' if self.pressed else '#fffdf7' if self.hover else '#faf5eb')
        ink='#fff9ec' if self.primary else '#754a36' if self.compact else '#23483d'
        border='#b98e54' if self.focused else '#d9c9b2'
        self.create_polygon(12,1,self.w-12,1,self.w-1,12,self.w-1,self.h-12,self.w-12,self.h-1,12,self.h-1,1,self.h-12,1,12,smooth=True,fill=fill,outline=border,width=2 if self.focused else 1)
        y=self.h/2+shift
        if self.kind=='wire':
            self.create_line(28,y-12,40,y-12,40,y+12,54,y+12,fill=ink,width=2)
            self.create_line(40,y-12,54,y-12,fill=ink,width=2)
            for x,z in [(28,y-12),(54,y-12),(54,y+12)]:self.create_oval(x-3,z-3,x+3,z+3,fill=fill,outline=ink,width=2)
        elif self.kind=='oled':
            self.create_rectangle(26,y-14,58,y+12,outline=ink,width=2)
            self.create_line(32,y+4,37,y-4,42,y+1,48,y-7,53,y-2,fill=ink,width=2)
        else:
            self.create_arc(28,y-10,49,y+11,start=40,extent=280,style='arc',outline=ink,width=2)
            self.create_line(39,y-13,39,y-1,fill=ink,width=2)
        self.create_text(77,y-(10 if self.subtitle else 0),text=self.title,anchor='w',fill=ink,font=('Microsoft YaHei',-20 if not self.compact else -17,'bold'))
        if self.subtitle:self.create_text(77,y+16,text=self.subtitle,anchor='w',fill='#c8d8cc' if self.primary else '#7d8071',font=('Microsoft YaHei',-12))
        self.create_text(self.w-28,y,text='→' if not self.compact else '⏻',fill=ink,font=('Segoe UI',-22))

def main():
    if sys.platform=='win32':
        import ctypes
        try:ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except (OSError,AttributeError):pass
    window=tk.Tk();window.title('电子项目工作台');window.geometry('1000x640');window.resizable(False,False)
    window.iconbitmap(str(ASSETS/'workbench.ico'))
    canvas=tk.Canvas(window,width=1000,height=640,highlightthickness=0,bg='#f5f0e6');canvas.pack(fill='both',expand=True)
    background=ImageTk.PhotoImage(Image.open(ASSETS/'background.png').resize((1000,640),Image.Resampling.LANCZOS))
    canvas.create_image(0,0,image=background,anchor='nw')
    mark=ImageTk.PhotoImage(Image.open(ASSETS/'workbench.png').resize((34,34),Image.Resampling.LANCZOS))
    canvas.create_image(63,46,image=mark,anchor='nw')
    canvas.create_text(111,63,text='WORKBENCH  /  SUITE',anchor='w',font=('Segoe UI',-12,'bold'),fill='#536a55')
    canvas.create_text(62,138,text='电子项目工作台',anchor='w',font=('Microsoft YaHei',-38,'bold'),fill='#23483d')
    canvas.create_text(65,188,text='把接线与屏幕创意，放在同一张工作桌。',anchor='w',font=('Microsoft YaHei',-15),fill='#6c7564')
    canvas.create_text(65,214,text='独立运行   /   分开保存   /   按需联动',anchor='w',font=('Microsoft YaHei',-12),fill='#8a826e')
    status=canvas.create_text(65,583,text='选择一个工作台开始。关闭此窗口不影响已打开的软件。',anchor='nw',width=450,font=('Microsoft YaHei',-12),fill='#6d7564')
    def launch(relative):
        path=ROOT/relative
        if not path.is_file():messagebox.showerror('找不到软件','请保留完整套装目录：\n'+str(path),parent=window);return
        subprocess.Popen([str(path)],cwd=str(path.parent))
        canvas.itemconfigure(status,text='已打开工作台。两款软件可同时使用，各自保存数据。')
    closing=False
    def close_all():
        nonlocal closing
        if closing:return
        if not messagebox.askokcancel('一键关闭本套装','将请求关闭本套装内的接线与 OLED 工作台。\n请先保存内容，并处理各软件的退出提示。\n不会强制结束进程，也不会关闭原来的独立版本。',parent=window):return
        result=suite_control.request_close(ROOT)
        if result['requested']<result['found']:
            canvas.itemconfigure(status,text='部分关闭请求未送达，请手动关闭对应窗口。');return
        closing=True;started=time.monotonic()
        def wait():
            nonlocal closing
            remaining=suite_control.windows(ROOT)
            if not remaining:window.destroy();return
            if time.monotonic()-started>20:
                closing=False;canvas.itemconfigure(status,text='仍有软件未退出。请处理保存/退出提示，或取消后继续编辑。');return
            canvas.itemconfigure(status,text='已发送关闭请求，等待处理两个工作台的保存/退出提示…')
            window.after(400,wait)
        window.after(400,wait)
    for y,title,subtitle,path,kind,primary in [
        (258,'接线工作台','模块与针脚 · 电气检查 · 连线设计','WiringWorkbench/WiringWorkbench.exe','wire',True),
        (360,'OLED 工作台','文字与图片 · 页面交互 · 界面预览','OLEDWorkbench/OLEDWorkbench.exe','oled',False)]:
        b=Action(window,title,subtitle,lambda p=path:launch(p),kind,primary);canvas.create_window(64,y,window=b,anchor='nw')
    close=Action(window,'一键关闭套装','',close_all,'power',compact=True);canvas.create_window(64,481,window=close,anchor='nw')
    canvas.create_text(66,553,text='正常退出，不强制结束；有未保存内容时请先保存。',anchor='w',font=('Microsoft YaHei',-11),fill='#8d7b65')
    window.mainloop()

if __name__=='__main__':main()
