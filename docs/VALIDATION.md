# 验证记录

2026-11-08。电脑测试与实物验收分开记录。

本次发布已在仅含上传白名单文件的独立目录中，使用新建虚拟环境运行完整测试通过；不依赖原 Keil 工程或旁边的 OLED/vendor 目录。环境为 Windows、Python 3.14.6、Node.js 24.18.0、MCP SDK 1.30.0。依赖通过 `requirements.txt` 安装。

从仓库根目录运行 `python -X utf8 tools/run_tests.py`，失败返回非零退出码。

| 测试 | 覆盖范围 |
| --- | --- |
| 6 个 `*.test.mjs` 文件 | 网络/端点、导入、检查、布线锁定/整理、Keil 证据绑定、显示投影与整网选择 |
| `test_global_library.py`：5 项 | 模板版本、旧项目不变、冲突、并发 |
| `test_keil_scan.py`：7 项 | 标准库/HAL、宏/条件编译、目标范围、XML、只读文件比较 |
| `test_project_store.py`：7 项 | 原子编辑、恢复、修订号、路径/格式拒绝、显示模式 |
| `test_storage.py`：1 项 | HTTP 授权、保存/读取、冲突与路径检查 |
| `test_mcp.py` | 实际 stdio 调用 12 个工具，HTTP 共用保存、恢复、SVG |

本机浏览器已验证 GND 三针整网高亮、信号网独立选择、原供电网展开、关闭高亮、保存重开、SVG 导出清除选中状态。截图见 `docs/assets/network-highlight.jpg`。真实图纸与恢复点逐字段比较，仅新增显示模式，模块、引脚、导线与代码绑定保持不变。

公开示例移除本机路径和代码绑定；用户项目/恢复点、全局模板、配置备份、虚拟环境与临时预览不上传。Keil 测试改用最小扫描夹具，该夹具不是可编译固件。

未由这些测试验证：Keil 编译、ST-Link 下载、实体板运行、供电容量、真实电平、针序或机构安全。GitHub Actions 状态以仓库 Actions 页面为准。
