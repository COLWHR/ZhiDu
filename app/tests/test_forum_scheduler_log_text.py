import ast
from pathlib import Path


def _collect_scheduler_string_fragments() -> list[str]:
    source = Path("app/services/forum_scheduler.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    fragments: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str):
                fragments.append(node.value)

    Visitor().visit(tree)
    return fragments


def test_forum_scheduler_visible_text_is_human_readable_chinese():
    log_text = "\n".join(_collect_scheduler_string_fragments())

    mojibake_markers = [
        "瑙備紬",
        "鍙戣█",
        "璁哄潧",
        "鍢夊",
        "鎬濊",
        "鐢熸垚",
        "澶辫触",
        "寮€",
        "瑷€",
    ]

    assert not any(marker in log_text for marker in mojibake_markers)
    assert "观众" in log_text
    assert "论坛主循环启动" in log_text
    assert "主持人正在进行开场白" in log_text
    assert "所有参与者正在思考中" in log_text
    assert "嘉宾" in log_text
    assert "当前发言队列" in log_text
    assert "下一位发言" in log_text
    assert "论坛异常终止" in log_text
