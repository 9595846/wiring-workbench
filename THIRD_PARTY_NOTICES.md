# 第三方依赖

- Python MCP SDK：通过 `requirements.txt` 安装，源代码 <https://github.com/modelcontextprotocol/python-sdk>，MIT 许可证。本仓库不捆绑 SDK 或第三方 vendor 目录；分发依赖时须遵守各自许可证。
- Python 与 Node.js：外部运行环境，不包含安装程序。
- 网页使用原生 DOM/SVG/CSS，没有打包外部前端框架或图片库。
- 界面图为本工具的示例截图，不是器件厂商针序图。

传递依赖及许可证以安装包提供的文件为准。仓库不包含 STM32 库、Keil 编译器、用户固件或设备驱动。

桌面版另外使用 pywebview（BSD-3-Clause）、pythonnet/clr_loader（各自许可证随构建产物附带），由 PyInstaller 打包。桌面分发目录包含 Python 与 Node.js 运行时，相应许可证置于 `licenses/`；系统 WebView2 不捆绑在本版中。源码仓库不提交运行时二进制。
