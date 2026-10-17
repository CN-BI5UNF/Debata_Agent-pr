"""测试 token 预算估算口径。"""

from __future__ import annotations

from utils.token_budget import TokenEstimator


def test_estimate_messages_ignores_provider_stripped_metadata():
    estimator = TokenEstimator()
    base = [{"role": "user", "content": "hello"}]
    noisy = [
        {
            "role": "user",
            "content": "hello",
            "metadata": {"raw": "x" * 20000},
        }
    ]

    assert estimator.estimate_messages(noisy) == estimator.estimate_messages(base)


def test_estimate_messages_ignores_conversation_id():
    estimator = TokenEstimator()
    base = [{"role": "user", "content": "hello"}]
    noisy = [
        {
            "role": "user",
            "content": "hello",
            "conversation_id": "conv-" + ("x" * 20000),
        }
    ]

    assert estimator.estimate_messages(noisy) == estimator.estimate_messages(base)


def test_estimate_messages_does_not_count_reasoning_content_by_default():
    estimator = TokenEstimator()
    base = [{"role": "assistant", "content": "done"}]
    noisy = [
        {
            "role": "assistant",
            "content": "done",
            "reasoning_content": "hidden " * 4000,
        }
    ]

    assert estimator.estimate_messages(noisy) == estimator.estimate_messages(base)


def test_estimate_messages_still_counts_tool_calls():
    estimator = TokenEstimator()
    without_tool = [{"role": "assistant", "content": ""}]
    with_tool = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "search",
                        "arguments": '{"query":"' + ("alpha " * 400) + '"}',
                    },
                }
            ],
        }
    ]

    assert estimator.estimate_messages(with_tool) > estimator.estimate_messages(without_tool) + 100


def test_update_calibration_converges_downward_on_consistent_overestimate():
    """tiktoken 对中文高估：持续反馈应让系数收敛到 1 以下，而不是被推高。"""
    estimator = TokenEstimator()
    assert estimator.calib_ratio == 1.0
    for _ in range(20):
        estimator.update_calibration(estimated=10000, actual_prompt_tokens=6000)
    assert estimator.calib_ratio < 0.7
    # 估算结果随之下降
    assert estimator.estimate_text("中文内容" * 100) < TokenEstimator().estimate_text("中文内容" * 100)


def test_update_calibration_clamps_wild_ratio():
    """单次异常样本（例如误传了工具循环累加值）不能把系数带飞。"""
    estimator = TokenEstimator()
    estimator.update_calibration(estimated=10000, actual_prompt_tokens=1_000_000)
    assert estimator.calib_ratio <= 2.0

    estimator = TokenEstimator()
    for _ in range(50):
        estimator.update_calibration(estimated=10000, actual_prompt_tokens=1)
    assert estimator.calib_ratio >= 0.35


def test_update_calibration_ignores_invalid_samples():
    estimator = TokenEstimator()
    estimator.update_calibration(estimated=0, actual_prompt_tokens=100)
    estimator.update_calibration(estimated=100, actual_prompt_tokens=0)
    assert estimator.calib_ratio == 1.0


def test_agent_run_result_defaults_first_prompt_tokens_to_zero():
    from agents.base import AgentRunResult

    result = AgentRunResult()
    assert result.first_prompt_tokens == 0
    assert result.prompt_tokens == 0
