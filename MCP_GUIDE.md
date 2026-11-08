# 接线工作台 MCP 使用说明

## 当前能力

本地 stdio 服务，使用官方 Python MCP SDK。网页和 MCP 共用 projects 目录与修订号，通过跨进程锁、原子替换和自动恢复点保护写入。工具不访问串口、不驱动硬件、不编译、不烧录或修改 Keil；全局模块库目前只提供读取。

| 工具 | 作用 |
| --- | --- |
| list_projects | 列出已保存项目与 revision |
| read_project | 读取完整项目，包括对象 ID、针脚 ID 和项目模板快照 |
| create_project | 使用全局模板快照创建新项目 |
| get_edit_help | 获取支持的编辑操作格式 |
| edit_project | 最多 50 项原子编辑，失败不保存 |
| update_project | 校验后替换完整项目内容 |
| check_project | 调用与网页相同的静态连接检查 |
| preview_project | 生成本地 SVG 简图和检查结果 |
| create_restore_point | 手动保留当前已保存内容 |
| list_restore_points | 列出项目恢复点 |
| restore_project | 恢复旧内容为新修订号，保留之后的记录 |
| read_global_library | 读取全局模板及版本摘要 |

编辑操作包括：添加常用/自定义模块、移动模块、更新针脚属性、接线、修改导线、锁定/整理线路、添加网络标记与标注、删除对象。删除带关联线的模块或连接点需要明确 cascade=true。复杂修改也能用完整 package 更新，提交前会进行同一份模型校验。

## 连接参数

参数模板见 MCP_CONFIG.example.json。将两个路径改为你的仓库绝对路径，再填入 MCP 客户端对应配置；本仓库不会自动修改客户端全局设置。

```json
{
  "command": "C:/path/to/wiring-workbench/.venv/Scripts/python.exe",
  "args": ["-X", "utf8", "C:/path/to/wiring-workbench/mcp_server.py"]
}
```

在克隆后的仓库根目录建立虚拟环境（不需要旁边的 OLED 工作台或 vendor 目录）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

然后把 command 改为虚拟环境 python 的绝对路径。需要 Node.js 22+ 在 PATH 中，用于复用网页的验证、布线和检查模型。无需启动网页也能调用 MCP；网页服务更新后应重启，以加载共用存储逻辑。

## 可以这样向 AI 提要求

> 将当前项目切换为供电短线显示，保留所有原始接线，生成 SVG 预览。

对应原子操作为 `{"type":"set_power_display","mode":"compact"}`，恢复完整走线使用 `mode: "full"`。显示模式保存于项目，网页中的临时选择/整网高亮不写入项目。已运行的旧 MCP 进程重启后，`get_edit_help` 才会列出新操作。

> 先列出接线项目，让我指定项目。读取最新 revision 和对象 ID。给 OLED 的 GND 添加网络标记，移动模块以减少线交叉，保留未知电气属性。修改前创建恢复点，修改后检查并给我 SVG 预览。

> 读取最新修订号，把刚才修改前的恢复点恢复回来。保留历史，不要拿旧修订号覆盖当前项目。

## 网页与 MCP 同时编辑

- MCP 只能看到已保存内容，网页未保存的编辑不会同步。
- 每次写入需要 expected_revision。旧窗口保存会返回冲突，不能静默覆盖 MCP 的修改。
- MCP 修改后，在网页重新打开该项目才能看到新版本；有未保存内容时可以先另存副本。
- 不同端口、不同进程的新版网页服务使用同一跨进程锁。此前仍在运行的旧版本服务不具备这项保护，应关闭后从 start.cmd 重新启动。
- 网页“恢复点”区域提供刷新、创建、恢复。恢复生成新修订号，当前磁盘内容也会先留恢复点。

## 恢复和预览边界

自动恢复点保存于 projects/.history/项目ID，覆盖修改前创建；新项目首次创建没有之前的版本可恢复。历史不会自动删除，建议定期备份 projects 目录。

保存相同内容时不重复生成修订号和恢复点。恢复点记录内容指纹，内容被篡改时拒绝恢复。保存/编辑失败不应产生部分项目修改。

预览位于 mcp_previews，使用和网页相同的端点与布线/检查规则。SVG 简图文字样式及线名显示可能与网页导出略有差别，正式展示仍可使用网页 PNG/SVG 导出。

## 实测

7 项存储测试及真实 MCP 会话中的 12 个工具通过。测试覆盖网页/MCP 共享项目、修订号冲突、部分编辑失败、恢复点校验、恢复后修订号递增、显示模式、SVG 与静态检查。并未因此完成任何新的实物验收。
