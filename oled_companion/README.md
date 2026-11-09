# OLED 套装配套源码

来源项目：https://github.com/9595846/oled-ui-workbench ，参考提交 954594b7129263be06a49fa0bc0143100543f6be；结合用户指定本地 OLED EXE 对应源码保留修改请求等既有功能，并加入桌面联动、相对路径和退出提示。这里是套装配套版本，不声称与上游 main 逐文件一致。

由主仓库 tools/build_suite.py 构建；直接开发时 python desktop.py。字库和适配校验使用 firmware_baseline/ 中的少量只读参考文件，该目录不是可编译 Keil 工程。没有附带个人草稿和真实硬件验证结果。不要将配套参考文件作为你当前真实固件的最新版本。

本轮不会用本目录覆盖上游仓库源码。上游独立使用方式继续保留，套装主文档见 ../docs/SUITE.md。
