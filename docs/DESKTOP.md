# Windows 桌面版

双击 `WiringWorkbench.exe` 打开接线工作台。请保留旁边的 `_internal` 文件夹；整个 `WiringWorkbench` 文件夹可以移动到其他可写目录，不要只复制 EXE。

已内置 Python 与 Node.js，无需手动启动终端或浏览器。使用系统 Microsoft Edge WebView2 Runtime；若缺少，请从微软官方网站安装：https://developer.microsoft.com/microsoft-edge/webview2/

项目、恢复点和全局模块保存在软件旁边 `data/projects/` 与 `data/module_library/`。升级时保留整个 `data/`，不要用旧版本覆盖用户数据。建议放在个人可写目录，不要放到 Program Files。

网页工作台的已有数据不会自动搬迁。可在网页导出 JSON，再在桌面版“导入 JSON”并保存；也可在关闭两端后备份并复制项目目录。示例位于 `_internal/examples/`。

PNG/SVG/JSON 等导出由保存对话框选择位置。关闭窗口会提醒保存，退出后本机服务停止。桌面版不修改原 Keil 工程、不访问下载器或实体硬件。

MCP stdio 服务继续使用源码工程中的 `mcp_server.py` 和原接入方式；本版 EXE 不冒充 MCP 服务，也不会自动更改 MCP 配置。两者默认数据目录不同，请用 JSON 导入/导出，避免把两个目录当成自动同步。

## 从源码构建

2026-11-09 验证：完整源码回归通过；实际运行生成的 EXE 后，内置 Node、模型检查、保存/重新读取、SVG 生成及 HTTP API 自测通过。原生窗口已成功显示，并实际点击保存后看到“版本 1 · 已保存”。桌面 PNG/SVG 保存对话框与全部鼠标编辑流程尚未完整验收；未编译或烧录固件。

在 Windows 上安装 Python、Node.js，然后执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe tools/build_desktop.py
```

输出：`dist/WiringWorkbench/WiringWorkbench.exe`。完整自动测试仍使用 `tools/run_tests.py`；打包后的后端自测可运行 EXE 的 `--self-test 报告路径.json`，该自测不等于 GUI 或实物验收。
