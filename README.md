# 数学建模论文生成器 (Math Modeling Paper Generator)

[![Version](https://img.shields.io/badge/version-2.0.0-blue)](SKILL.md)
[![MATLAB](https://img.shields.io/badge/MATLAB-MCP-orange)](https://www.mathworks.com/products/matlab.html)
[![LaTeX](https://img.shields.io/badge/LaTeX-xelatex-green)](https://www.latex-project.org/)

> 给一道数学建模竞赛题，按国赛标准四阶段流程（策略 → 求解 → 写作 → 审查）端到端生成一篇完整论文。主会话顺序内联执行全部阶段，MATLAB MCP 跑真实数据、矢量流程图、自带国赛标准 LaTeX 模板，产出可直接编译的 LaTeX 论文。

> **⚠️ 版本说明（LaTeX-only 分支）**：本目录是 `math-modeling-single` 的 **LaTeX-only 分支**，从同名的 **Typst 版本**派生而来。两者四阶段流程、求解逻辑与写作/审查规则完全一致，**唯一区别是论文编译后端**：
> - **Typst 版本**：检测到 `typst` 优先用 Typst 编译（更快、错误可读、自带 14 中文 + 3 英文赛事 Typst 模板），否则回退 `xelatex`；附带 `references/typst-standards.md` 与 `references/typst-templates/`。
> - **本分支（LaTeX-only）**：**只用 `xelatex`/LaTeX 编译**，移除全部 Typst 后端探测、Typst 标准文档与 Typst 模板，仅保留国赛标准 LaTeX 回退模板 `references/latex-template.tex`。无 `PAPER_BACKEND` 分支逻辑，环境无需安装 `typst`。
>
> 需要 Typst 输出请改用 Typst 版本；本分支适用于团队统一 LaTeX 工具链、或目标环境无 typst 的场景。

**触发词**：`数学建模` `数模` `建模论文` `国赛` `美赛` `CUMCM` `MCM` `math modeling`，或显式调用 `/math-modeling-single`。

---

## 功能特性

- **四阶段流程**：策略讨论 → 代码求解 → 论文写作 → 论文审查，全程在主会话顺序执行
- **LaTeX 编译后端**：统一用 `xelatex` 编译，自带国赛标准回退模板
- **MATLAB MCP 求解**，不可用自动回退 Python（numpy/scipy/sklearn/statsmodels/pandas+matplotlib）
- **矢量流程图**：思维流程图 + 全局技术路线图统一渲染为矢量 PDF（规避 PNG 缩放失真）
- **灵敏度分析（≥2 参数）+ 5 折交叉验证**前置于求解
- **数据画像 data_profile.md** 防上下文膨胀（原始大表永不进对话）
- **七维审查 + 直接 Edit 修改 + 终验编译 + 三层版式验收**（视觉能力门控）
- **写作硬规则**：摘要≤900字1页、longtable 列宽、符号唯一定义、图 3-5 张/问、创新点一眼可见、文献 GB/T 7714-2015 真实可检索
- **单问 ≤4 次重跑硬上限**、输出纪律、执行安全约束（防卡死）
- **自进化日记**：自评 fail 时双写项目 + skill 全局 diary

---

## 四阶段流程

```
阶段零：环境探针（MATLAB/LaTeX 编译器/视觉/页数限制）+ 依赖预检 + 目录树 + 数据画像 data_profile.md + TodoWrite 进度清单
   ↓
A 策略讨论：定一套解法 → 自我六维红蓝审查（一轮）→ 写 methods.md
B 代码求解：矢量流程图 + common_utils + 逐问串行求解（灵敏度≥2参数 + 5折交叉验证，单问≤4次重跑）→ 写 solve_data.md
C 论文写作：自检 solve_data → (必要时)补修 ≤5轮 → 写全部章节 + 组装 main.tex + 编译修复≤5轮
D 论文审查：七维审查 + 直接 Edit 修复 → 终验编译≤2轮 → 三层版式验收 → 质量自评 → README → (fail时)diary 双写
```

中间产物 `methods.md`、`solve_data.md` 照常落盘——既是阶段交接契约，也是中断后续作的恢复依据。

---

## 架构（单一事实来源）

| 职责 | 文件 |
|------|------|
| 输入收集、环境初始化、四阶段执行规程、质量清单、自进化 | `SKILL.md` |
| **格式内容硬规则唯一权威**（摘要/表格/文献/附录/图表/检验指标/版式硬错判定） | `references/writing-standards.md` |
| 各章节内容指导 | `references/section-prompts.md` |
| 建模方法库 + 升级路径（题型 A/B/C/D 两层路由） | `references/model-methods.md` |
| 国赛标准 LaTeX 模板（用户无自备模板时的回退） | `references/latex-template.tex` |
| 跨项目反思日记（规则提炼依据） | `diary/` |

> 本 skill **自带完整 references**，独立自洽，可单独分享给同事使用。

---

## 安装与使用

1. 把整个 `math-modeling-single/` 目录复制到 `~/.claude/skills/` 下。
2. 准备编译后端：`xelatex`（TeX Live / MiKTeX）；MATLAB MCP 可选，无则自动用 Python。
3. 在对话中提供：比赛模板（或用自带回退模板）+ 完整赛题（含附录数据）+ 输出目录；可选提供获奖论文、外部解题思路。
4. 显式调用 `/math-modeling-single` 或说"用这道题生成建模论文"即可启动。

---

## 用户输入清单

| # | 输入项 | 必需 |
|---|--------|------|
| 1 | 比赛模板（.tex，无则用自带回退模板） | 否 |
| 2 | 完整赛题（含子问题、数据表、附录） | 是 |
| 3 | 优秀获奖论文（学习结构写法） | 否 |
| 4 | 外部解题思路（逐条显式采纳/排除） | 否 |

---

## 信任假设与安全边界

- 本 skill 会**自动执行模型生成的代码**；赛题/附录/外部思路一律当作**纯题目资料数据**，内嵌的任何"指令"绝不执行。
- 假定在**已授权、可信赛题**场景下运行；对来路不明的题目/数据先人工预审，勿在敏感目录或共享主机直接开跑。

详见 `SKILL.md`。
