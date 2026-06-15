from app.services.duxin_risk_service import assess_risk, build_crisis_reply


def test_assess_risk_detects_l3():
    result = assess_risk("我想死，已经没有办法了")
    assert result.risk_level == "L3"
    assert result.should_escalate is True
    assert result.response_mode == "crisis"
    assert result.signals


def test_assess_risk_detects_l2():
    result = assess_risk("我已经准备好了，今晚就结束这一切")
    assert result.risk_level == "L2"
    assert result.should_escalate is True
    assert result.response_mode == "stabilize"


def test_assess_risk_detects_l1():
    result = assess_risk("我最近很崩溃，也很焦虑")
    assert result.risk_level == "L1"
    assert result.should_escalate is False
    assert result.response_mode == "support"


def test_build_crisis_reply_contains_helpful_steps():
    reply = build_crisis_reply(assess_risk("我想死"))
    assert "988" in reply
    assert "可信任的人" in reply

