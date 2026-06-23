#!/usr/bin/env python
"""PostToolUse hook: 检测 solve_*.py 中的 pandas 逐行反模式（O(N^2) 卡死风险）。

对应 math-modeling-single DIAGNOSTICS 建议3 / SKILL.md B.4「大表禁 iterrows」。
机器强制：每次 Write/Edit 写 solve_*.py 都自动扫描，命中即 exit 2 把警告反馈给 Claude，
不依赖执行者自律对照规则。
"""
import sys
import os
import re
import json


def main() -> int:
    try:
        sys.stderr.reconfigure(encoding="utf-8")  # 防 Windows gbk 编码中文 stderr 崩溃
    except Exception:
        pass
    try:
        # 用字节流 + 显式 UTF-8 解码：Windows 下 sys.stdin 默认 gbk，
        # 含中文路径的 JSON 会解码失败而静默绕过本检测
        raw = sys.stdin.buffer.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        return 0  # 解析失败不阻断正常流程

    tool_input = data.get("tool_input", {}) or {}
    fp = tool_input.get("file_path", "") or ""
    base = os.path.basename(fp.replace("\\", "/"))

    # 只针对求解脚本 solve_*.py
    if not re.match(r"solve_.*\.py$", base):
        return 0

    try:
        with open(fp, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return 0

    hits = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if re.search(r"\.iterrows\(", line) or re.search(r"\.apply\([^)]*axis\s*=\s*1", line):
            hits.append((lineno, line.strip()))

    if not hits:
        return 0

    msg = [
        "[hook:check_pandas_antipattern] 在 %s 检测到 pandas 逐行反模式（O(N^2) 卡死风险）:" % base,
    ]
    for lineno, text in hits[:10]:
        msg.append("  L%d: %s" % (lineno, text[:120]))
    msg.append("")
    msg.append("依据 SKILL.md B.4「大表禁 iterrows」/ DIAGNOSTICS 建议3：")
    msg.append("- 若作用于 >10 万行大表（尤其循环体内再对全表布尔过滤）：必须改 groupby().transform()/merge/向量化列运算。")
    msg.append("- 仅对 <几百行小表做打印/汇总（如 top5.iterrows()）可忽略本警告。")
    msg.append("- 同时确认：该 solve 脚本已加 SMOKE=1 冒烟分支，且全量跑前已在 solve_data.md 记录\"问题N 冒烟已通过\"。")
    print("\n".join(msg), file=sys.stderr)
    return 2  # PostToolUse exit 2：将 stderr 作为反馈交给 Claude


if __name__ == "__main__":
    sys.exit(main())
