"""check_tables.py — 三线表(longtable)确定性版式 lint（I1）

扫描章节 .tex，对每个 longtable 环境机器校验是否符合 writing-standards.md §9：
  H1 列未居中    ：列规格出现裸 p{...}（前面没有 >{\\centering\\arraybackslash}）→ 左对齐丑表
  H2 定宽非比例  ：列宽用 cm/mm/pt/in 等绝对单位（应一律 r\\textwidth 比例）→ 不满宽/越界
  H3 比例不满宽  ：各列 \\textwidth 比例总和 ≠ 1.04-0.04N（容差 ±0.03）→ 留白或越界
  H4 非三线表    ：缺 \\toprule / \\midrule / \\bottomrule 任一
  M1 底线重复    ：环境内 \\bottomrule 多于 1 条（典型：\\endfoot 内一条 + 表末又写一条）
  M2 头尾不全    ：缺 \\endfirsthead / \\endhead / \\endfoot 任一（续页丢表头/结构脆弱）

用法：
    python references/check_tables.py <paper/sections 目录或若干 .tex 文件>
退出码：发现任一 HIGH(H*) 违规则非 0（可作硬门禁）；仅 MEDIUM 退 0 但打印告警。

设计：纯标准库、模型无关。这是"双保险"中的审查期可执行检测，配合 make_table.py 的生成期保证。
"""

from __future__ import annotations

import os
import re
import sys

TARGET_TOL = 0.03  # 比例总和与 1.04-0.04N 的容差


def _find_envs(text):
    """返回 [(start_line, body_str)]，每项为一个 longtable 环境。"""
    envs = []
    for m in re.finditer(r"\\begin\{longtable\}(.*?)\\end\{longtable\}",
                         text, re.S):
        start_line = text.count("\n", 0, m.start()) + 1
        envs.append((start_line, m.group(0)))
    return envs


def _extract_colspec(env):
    """取 \\begin{longtable}[..]{COLSPEC} 的 COLSPEC（平衡花括号）。"""
    i = env.find(r"\begin{longtable}") + len(r"\begin{longtable}")
    # 跳过可选的 [..] 位置参数与空白
    while i < len(env) and env[i] in " \t\r\n":
        i += 1
    if i < len(env) and env[i] == "[":
        depth = 0
        while i < len(env):
            if env[i] == "[":
                depth += 1
            elif env[i] == "]":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        while i < len(env) and env[i] in " \t\r\n":
            i += 1
    if i >= len(env) or env[i] != "{":
        return ""
    depth, j = 0, i
    while j < len(env):
        if env[j] == "{":
            depth += 1
        elif env[j] == "}":
            depth -= 1
            if depth == 0:
                return env[i + 1:j]
        j += 1
    return ""


def _check_env(start_line, env, fname, issues):
    spec = _extract_colspec(env)

    # H1 裸 p{：把所有 >{\centering\arraybackslash} 包裹处挖掉后仍残留 p{ 即裸列
    spec_wo_centered = re.sub(
        r">\{[^{}]*arraybackslash[^{}]*\}\s*p\{", "<<C>>{", spec)
    if re.search(r"(?<!<<C>>)\bp\{", spec_wo_centered) or \
       re.search(r"(?:^|[^>])\bp\{", re.sub(
           r">\{[^{}]*arraybackslash[^{}]*\}p\{[^{}]*\}", "", spec)):
        # 第二个条件兜底：去掉所有居中列后还剩 p{ / l / r / c 实列
        leftover = re.sub(r">\{[^{}]*arraybackslash[^{}]*\}p\{[^{}]*\}", "", spec)
        if re.search(r"\bp\{|[lrc](?![a-zA-Z])", leftover):
            issues.append((fname, start_line, "HIGH", "H1",
                           "列未居中（出现裸 p{}/l/r/c，应 >{\\centering\\arraybackslash}p{}）",
                           spec.strip()[:80]))

    # H2 绝对单位定宽
    if re.search(r"p\{[^{}]*\d\s*(cm|mm|pt|in|bp)\b", spec):
        issues.append((fname, start_line, "HIGH", "H2",
                       "列宽用绝对单位(cm/mm/pt/in)，应改 r\\textwidth 比例",
                       spec.strip()[:80]))

    # H3 比例总和
    ratios = [float(x) for x in re.findall(r"p\{\s*([0-9]*\.?[0-9]+)\\textwidth", spec)]
    n_cols = len(re.findall(r"p\{", spec)) or len(ratios)
    if ratios and n_cols:
        target = round(1.04 - 0.04 * n_cols, 2)
        ssum = round(sum(ratios), 3)
        if abs(ssum - target) > TARGET_TOL:
            issues.append((fname, start_line, "HIGH", "H3",
                           f"列宽比例总和 {ssum} ≠ 目标 {target}（N={n_cols}，1.04-0.04N，差 {round(ssum-target,3)}）",
                           spec.strip()[:80]))

    # H4 三线齐备
    for rule, zh in ((r"\toprule", "顶线"), (r"\midrule", "栏目线"),
                     (r"\bottomrule", "底线")):
        if rule not in env and (rule != r"\midrule" or r"\cmidrule" not in env):
            issues.append((fname, start_line, "HIGH", "H4",
                           f"缺 {rule}（{zh}）——不是合规三线表", ""))

    # M1 底线重复
    nbot = env.count(r"\bottomrule")
    if nbot > 1:
        issues.append((fname, start_line, "MEDIUM", "M1",
                       f"\\bottomrule 出现 {nbot} 次（应仅 1 条于 \\endfoot，表末不重复）", ""))

    # M2 头尾结构
    for tok in (r"\endfirsthead", r"\endhead", r"\endfoot"):
        if tok not in env:
            issues.append((fname, start_line, "MEDIUM", "M2",
                           f"缺 {tok}（longtable 跨页头尾结构不全）", ""))


def _iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith(".tex"):
                        yield os.path.join(root, f)
        elif p.endswith(".tex"):
            yield p


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows 控制台默认 GBK，强制 UTF-8 防中文乱码
    except Exception:
        pass
    paths = argv[1:] or ["sections"]
    issues = []
    n_tables = 0
    for fname in _iter_files(paths):
        try:
            text = open(fname, encoding="utf-8").read()
        except Exception as e:
            print(f"[skip] {fname}: {e}")
            continue
        for start_line, env in _find_envs(text):
            n_tables += 1
            _check_env(start_line, env, fname, issues)

    highs = [x for x in issues if x[2] == "HIGH"]
    meds = [x for x in issues if x[2] == "MEDIUM"]
    print(f"扫描 longtable 环境 {n_tables} 个；HIGH {len(highs)} 项，MEDIUM {len(meds)} 项")
    for fname, line, sev, code, msg, snip in issues:
        loc = f"{fname}:{line}"
        print(f"  [{sev}] {code} {loc} — {msg}")
        if snip:
            print(f"          列规格: {snip}")
    if not issues:
        print("  ✓ 全部三线表合规（居中 / 比例满宽 / 单底线 / 头尾完整）")
    return 1 if highs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
