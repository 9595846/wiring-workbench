# Windows 试用版：从这里开始

这是接线与 OLED 工作台的试用套装，支持 Windows 10/11 x64。用于电脑上的接线设计、OLED 布局和交互预览，不需要连接开发板。MCP 是可选功能。

## 启动

1. 解压整个 ZIP 到个人可写目录，不要在压缩包里直接双击。
2. 保留所有子目录，双击 `WorkbenchSuite.exe`，选择接线或 OLED 工作台。
3. 如果提示缺少 WebView2，请从微软安装运行时：https://developer.microsoft.com/microsoft-edge/webview2/ 。Python 和 Node 已随套装提供。
4. Windows 可能提示未签名应用；本试用版没有代码签名。确认下载来自作者仓库并核对 SHA256，不要关闭系统防护。

## 首次体验

接线：导入根目录 `examples/stm32-oled-buzzer.json` → 点击 GND 网络 → 修改模块名称 → 保存 → 重新打开 → 导出 JSON 与 PNG/SVG。

OLED：新建项目 → 输入 `HELLO` → 调整坐标 → 保存 → 重新打开 → 导出 PNG。再尝试中文与弹窗；缺字和越界提示需要单独处理。

接线图与屏幕预览不等于实物验收。OLED 的 `firmware_baseline` 只是只读适配参考，不是一份可以直接编译的 Keil 工程。

## 数据与升级

- 接线数据：`WiringWorkbench/data/`。
- OLED 设计与导出：`oled_workspace/drafts/`、`oled_workspace/exports/`。
- 本包不包含作者的个人图纸、草稿、请求和历史。
- 升级前备份数据，优先用 JSON 导入/导出迁移；不要用旧包覆盖已经编辑的设计。
- 桌面版、源码网页版与原 MCP 配置不自动同步数据。

## 验证范围与反馈

具体构建环境、自测结果及未验证项见 Release 页面和随附验证记录。自动化自测不代表完整鼠标操作、另一台实体电脑或硬件验收。

反馈：https://github.com/9595846/wiring-workbench/issues/new/choose 。请附版本、启动方式、复现步骤和截图，移除个人路径及私有工程资料。

第三方运行时许可位于 `licenses/`。应用代码尚未另行指定开源许可证；本下载用于试用，不据此推定任意再分发授权。
