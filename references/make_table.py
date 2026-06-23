"""make_table.py — 国赛标准三线表(longtable)生成器（I3）

从表格数据一键生成符合 writing-standards.md §9 的 longtable LaTeX 代码，
从源头保证三件铁律不被手写跑偏：

  1. 列居中     ：每列 >{\\centering\\arraybackslash}p{r\\textwidth}
  2. 比例满宽   ：各列比例总和 = 1.04 - 0.04*N（占满版心并居中，不留白、不越界、不用 cm 定宽）
  3. 单底线     ：\\bottomrule 只在 \\endfoot（longtable 末页亦用 \\endfoot），表末不再重复写

跨页结构固定为 \\endfirsthead / \\endhead / \\endfoot（续页自动重出表头）。

依赖：标准库即可；可选传入 pandas.DataFrame。

用法一（pandas）：
    import pandas as pd
    from make_table import make_longtable
    df = pd.read_csv("data/results_problem1.csv")
    code = make_longtable(df, caption="问题一预测结果（Top 5）", label="tab:p1_result")

用法二（无 pandas，直接给表头与数据行）：
    code = make_longtable(None, caption="主要符号说明", label="tab:notation",
                          header=["符号", "类型", "含义"],
                          rows=[["$U$", "集合", "用户集合"], ...])

落盘后在章节 .tex 里 \\input 或直接粘贴：
    open("paper/sections/tables/p1_result.tex", "w", encoding="utf-8").write(code)

注意：单元格内容按"已是合法 LaTeX"对待，默认不转义（域内大量使用 $...$ 数学符号，
自动转义会破坏 `$R^2$`、`$\\alpha$` 等）。若数据含裸 `_ % & #` 等特殊字符且不在数学环境内，
调用方需自行转义或令 escape=True（仅转义非数学片段外的特殊字符，保守起见默认 False）。
"""

from __future__ import annotations

_SPECIAL = {"_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#"}


def _normalize(data, header, rows):
    """统一成 (header:list[str], rows:list[list[str]])。data 可为 DataFrame。"""
    if data is not None:
        # 鸭子类型识别 pandas.DataFrame，避免硬依赖
        if hasattr(data, "columns") and hasattr(data, "itertuples"):
            header = [str(c) for c in data.columns]
            rows = [[("" if v is None else str(v)) for v in row]
                    for row in data.itertuples(index=False, name=None)]
            return header, rows
        # 视为可迭代的二维序列；若未单独给 header 则取首行
        seq = [list(r) for r in data]
        if header is None:
            header, body = seq[0], seq[1:]
        else:
            body = seq
        return [str(h) for h in header], [[str(c) for c in r] for r in body]
    if header is None or rows is None:
        raise ValueError("需提供 data，或同时提供 header 与 rows")
    return [str(h) for h in header], [[str(c) for c in r] for r in rows]


def _cell_weight(s: str) -> int:
    """估算单元格视觉宽度：CJK/全角按 2，其余按 1，math 定界符 $ 不计。"""
    w = 0
    for ch in s:
        if ch == "$":
            continue
        w += 2 if ord(ch) > 0x2E80 else 1
    return max(w, 1)


def _auto_ratios(header, rows, n):
    """按各列最大视觉宽度分配，归一到 total = 1.04 - 0.04*N。"""
    total = round(1.04 - 0.04 * n, 2)
    weights = []
    for j in range(n):
        col = [header[j]] + [r[j] if j < len(r) else "" for r in rows]
        weights.append(max(_cell_weight(c) for c in col))
    s = float(sum(weights)) or 1.0
    ratios = [round(total * w / s, 2) for w in weights]
    # 修正四舍五入残差，让总和精确等于 total（差额并入最宽列）
    drift = round(total - sum(ratios), 2)
    if drift:
        widest = max(range(n), key=lambda j: weights[j])
        ratios[widest] = round(ratios[widest] + drift, 2)
    return ratios


def _fit_ratios(col_ratios, n):
    """调用方自定义比例时，按比例缩放到 total = 1.04 - 0.04*N。"""
    if len(col_ratios) != n:
        raise ValueError(f"col_ratios 长度 {len(col_ratios)} 与列数 {n} 不一致")
    total = round(1.04 - 0.04 * n, 2)
    s = float(sum(col_ratios)) or 1.0
    ratios = [round(total * r / s, 2) for r in col_ratios]
    drift = round(total - sum(ratios), 2)
    if drift:
        widest = max(range(n), key=lambda j: col_ratios[j])
        ratios[widest] = round(ratios[widest] + drift, 2)
    return ratios


def _esc(s: str, escape: bool) -> str:
    if not escape:
        return s
    # 仅转义数学环境（$...$）之外的特殊字符，保留行内公式
    out, in_math = [], False
    for ch in s:
        if ch == "$":
            in_math = not in_math
            out.append(ch)
        elif not in_math and ch in _SPECIAL:
            out.append(_SPECIAL[ch])
        else:
            out.append(ch)
    return "".join(out)


def make_longtable(data=None, caption="", label="", header=None, rows=None,
                   col_ratios=None, escape=False, midrule_before_last=False):
    """生成国赛标准三线表 longtable 代码字符串（以 \\n 结尾）。

    参数：
      data    : pandas.DataFrame 或二维序列；为 None 时用 header+rows。
      caption : 表标题（中文）。
      label   : \\label 标签（如 "tab:p1_result"）。
      header  : 表头列表（data 为二维序列且无表头时用作表头）。
      rows    : 数据行（data 为 None 时必填）。
      col_ratios : 可选，自定义各列相对比例（会自动缩放到 1.04-0.04N）。
      escape  : 是否转义非数学片段中的 _ % & #（默认 False，域内多为已就绪 LaTeX）。
      midrule_before_last : 末行前加一条辅助线 \\midrule（用于"均值±标准差"等汇总行）。
    """
    header, rows = _normalize(data, header, rows)
    n = len(header)
    if n == 0:
        raise ValueError("表头为空")
    ratios = _fit_ratios(col_ratios, n) if col_ratios is not None \
        else _auto_ratios(header, rows, n)
    colspec = "".join(r">{\centering\arraybackslash}p{%.2f\textwidth}" % r
                      for r in ratios)
    head_line = " & ".join(_esc(h, escape) for h in header) + r" \\"

    body_lines = []
    for i, row in enumerate(rows):
        cells = [_esc(c, escape) for c in row] + [""] * (n - len(row))
        if midrule_before_last and i == len(rows) - 1:
            body_lines.append(r"  \midrule")
        body_lines.append("  " + " & ".join(cells[:n]) + r" \\")

    parts = [
        r"\begin{longtable}{%s}" % colspec,
        r"  \caption{%s}\label{%s} \\" % (caption, label),
        r"  \toprule",
        "  " + head_line,
        r"  \midrule",
        r"  \endfirsthead",
        r"  \caption[]{%s（续）} \\" % caption,
        r"  \toprule",
        "  " + head_line,
        r"  \midrule",
        r"  \endhead",
        r"  \bottomrule",
        r"  \endfoot",
        *body_lines,
        r"\end{longtable}",
    ]
    return "\n".join(parts) + "\n"


if __name__ == "__main__":  # 简单自测
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    demo = make_longtable(
        None, caption="问题一预测结果（Top 5）", label="tab:p1_result",
        header=["排名", "博主ID", "预测新增关注数"],
        rows=[["1", "B21", "505"], ["2", "B5", "498"], ["3", "B60", "415"]],
    )
    print(demo)
