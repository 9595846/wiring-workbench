# 接线与 OLED 工作台 Windows 试用版

适用于 Windows 10/11 x64。下载 ZIP 后完整解压，双击 `WorkbenchSuite.exe`。无需另外安装 Python 或 Node.js；需要系统 Microsoft Edge WebView2 Runtime。

- 接线工作台：模块接线、整网高亮、保存与导出、Keil 只读核对。
- OLED 工作台：128×64 文字、图片、弹窗与交互预览，导出待审阅 C 文件。
- 两端独立保存，可按需联动。本公开包不包含作者个人项目、草稿、请求和历史。
- 使用方法见包内 `START_HERE.md`；接线示例在 `examples/`。

附件的 SHA256SUMS.txt 可用于核对 ZIP 完整性，PowerShell 示例：`Get-FileHash .\WorkbenchSuite-v0.1.0-preview.1-windows-x64.zip -Algorithm SHA256`。

## 验证与限制

发布流程先在 GitHub Windows runner 运行回归测试，再构建 EXE，复制到含中文和空格的独立目录，并从 PATH 移除 Python/Node 后执行 EXE 自测。检查接线保存/读取、SVG 和 HTTP，以及 OLED 保存/读取、冲突拒绝、128×64 PNG、弹窗确认与 C 导出。验证摘要在包内 `VALIDATION.json`。

这不是完整原生窗口鼠标操作测试，也不是另一台实体电脑的人工验收。未进行本版 Keil 编译、烧录或实体 OLED 验收；界面预览不等于硬件已经接入。应用未进行代码签名，Windows 可能显示发布者未知。

请完整保留子目录，升级前备份数据。问题反馈：https://github.com/9595846/wiring-workbench/issues/new/choose 。

第三方运行时许可随包附带；应用源码尚未另行设置开源许可证。
