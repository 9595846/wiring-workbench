# 电子项目工作台套装

双击 `WorkbenchSuite.exe`，分别选择接线工作台或 OLED 工作台。两个程序独立运行，关闭其中一个或关闭启动器，不会关闭另一个。

启动器新增专属背景、原创电路/OLED 图标、按钮悬停/按下与键盘焦点效果。桌面“电子项目工作台”快捷方式指向此启动器。

“一键关闭套装”会在确认后向本套装目录内的两款软件发送正常关闭请求。请先保存内容，并处理软件弹出的退出提示；没有未退出窗口时，启动器一并退出。取消退出或仍有窗口时保留启动器，不强制结束任何进程，也不关闭原目录中的独立版本。标题栏关闭按钮仍只关闭启动器。

背景由内置 image_gen 生成；图标为可编辑 SVG 设计并生成多尺寸 ICO。素材、生成提示词和实现说明保存在源码 `assets/launcher/`，打包资源位于 `_launcher/assets/launcher/`。

## 目录与数据

```text
WorkbenchSuite.exe              总启动器
_launcher/                      启动器运行资源
WiringWorkbench/                接线软件与独立 data/ 数据
OLEDWorkbench/                  OLED 软件与只读适配资源
oled_workspace/                 OLED 资源、设计 drafts/、请求、导出
licenses/                       随附运行时许可
```

请移动、复制整个套装，不要只拿 EXE。放在个人可写目录，支持中文路径。已内置 Python 和 Node.js，使用系统 WebView2 Runtime；未在其他电脑完整验收。

首次构建只复制当时已保存的项目和设计，不包含未保存编辑。之后套装版与原来分开的软件不会自动同步数据，原目录保持不变。升级前备份接线 `WiringWorkbench/data/` 和 OLED `oled_workspace/`；构建器不会覆盖已经存在的用户数据文件。

## 按需联动

接线图选择 OLED 模块，在右侧读取设计列表并绑定。点击“打开 OLED 编辑器”，会打开本套装里的 OLED 软件；保存设计后回接线端刷新预览。只读取已保存版本，不自动覆盖两端的编辑。

套装内使用相对路径配置，移动整个目录后联动仍指向套装内部。两端不共用项目文件格式、缓存或端口，各自监听系统分配的本机端口；各自退出时停止自己的服务。

OLED 内置的 `firmware_baseline` 仅是显示、字库和适配指纹校验所需的少量只读参考文件，不是一份可编译工程。仍使用你原来的 Keil 工程接入导出设计，软件不会编译、烧录或修改该工程。

MCP 配置不自动更改。原 MCP 仍访问原工作区；需要访问套装数据时须另行明确配置，不把原工作区和套装副本当成自动同步。

## 2026-11-09 验证

- 两端原有回归通过；相对联动路径另有测试覆盖。
- 整套复制到含中文及空格的新目录，实际运行两个 EXE 自测通过；OLED 渲染资源、适配指纹与内置 Node 可用，联动配置指向移动后的套装内部，已保存项目哈希不变。
- 总启动器实际打开两款软件；关闭启动器后，两款软件窗口均继续运行。
- 本机 WebView2 环境已验证，未在另一台电脑验收。未编译、烧录或修改原 Keil 工程。

## 从本仓库构建

主仓库为 https://github.com/9595846/wiring-workbench ，OLED 独立编辑器项目说明见 https://github.com/9595846/oled-ui-workbench 。`oled_companion/` 保存本套装使用的 OLED 配套源码与少量只读资源，不需要另一个本机工作区才能构建。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-desktop.txt
.\.venv\Scripts\python.exe tools/build_suite.py
```

输出为 `dist/WorkbenchSuite/`。可用 `--output 自选目录` 指定位置；若目标软件正在运行，请先保存并退出。构建过程先使用 build 暂存目录，用户数据仅补充不存在的文件，不覆盖已有文件。未指定许可证的源码不因公开而自动授权任意分发。

公开仓库不包含个人设计、项目历史、快捷方式、虚拟环境或本机配置，也不提交生成的 EXE/ZIP。仓库提供源码和构建方法；本机软件包是另外生成的交付文件。
