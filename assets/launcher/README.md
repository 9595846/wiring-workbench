# 启动器视觉资源

- `background.png`：使用内置 image_gen 工具生成的原创电子实验室背景，保留原始尺寸，运行时仅缩放显示。
- `workbench.svg`：原创可编辑图标，将电路分支与 OLED 波形结合。
- `workbench.png`、`workbench.ico`：由 `tools/make_launcher_icon.py` 从同一几何设计生成，ICO 包含 16～256 像素多个尺寸。

背景生成提示词：

```text
Use case: stylized-concept. Asset type: background illustration for a Windows electronics project launcher, wide landscape 1600x1000 approximately. A refined miniature electronics laboratory still life on warm ivory paper: a forest-green printed circuit board, a small black OLED screen glowing a few restrained mint pixels, neat copper-gold circuit traces and connector pins. Soft tactile three-dimensional editorial illustration, precision-crafted materials, gentle studio shadows, warm quiet daylight, warm cream #f5f0e6 and deep forest #23483d with sparse amber accents. Composition: the left 58 percent is clean softly textured warm ivory negative space for real application text and buttons; all illustrated components sit elegantly on the right side, strongest in the lower right, with a faint branching circuit motif near the upper right. This is an actual background asset, not a mockup or screenshot. Absolutely no text, letters, numbers, logos, fake interface panels, buttons, watermarks, people or decorative clutter.
```
