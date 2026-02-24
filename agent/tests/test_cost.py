"""Tests for cost analysis module."""

from src.observability.cost import calculate_cost, calculate_batch_cost, MODEL_PRICING


class TestCalculateCost:
    def test_zero_tokens(self):
        result = calculate_cost(0, 0)
        assert result["total_cost_usd"] == 0
        assert result["input_cost_usd"] == 0
        assert result["output_cost_usd"] == 0

    def test_gpt4o_pricing(self):
        # 1000 input tokens at $2.50/1M = $0.0025
        # 500 output tokens at $10.00/1M = $0.005
        result = calculate_cost(1000, 500, model="gpt-4o")
        assert result["model"] == "gpt-4o"
        assert result["input_cost_usd"] == 0.0025
        assert result["output_cost_usd"] == 0.005
        assert result["total_cost_usd"] == 0.0075

    def test_gpt4o_mini_pricing(self):
        # 1000 input tokens at $0.15/1M = $0.00015
        # 500 output tokens at $0.60/1M = $0.0003
        result = calculate_cost(1000, 500, model="gpt-4o-mini")
        assert result["model"] == "gpt-4o-mini"
        assert result["input_cost_usd"] == 0.00015
        assert result["output_cost_usd"] == 0.0003
        assert result["total_cost_usd"] == 0.00045

    def test_unknown_model_uses_default(self):
        result = calculate_cost(1000, 500, model="unknown-model")
        default_result = calculate_cost(1000, 500, model="gpt-4o")
        assert result["total_cost_usd"] == default_result["total_cost_usd"]

    def test_large_token_count(self):
        # 1M input tokens = $2.50, 1M output tokens = $10.00
        result = calculate_cost(1_000_000, 1_000_000, model="gpt-4o")
        assert result["input_cost_usd"] == 2.5
        assert result["output_cost_usd"] == 10.0
        assert result["total_cost_usd"] == 12.5

    def test_returns_token_counts(self):
        result = calculate_cost(1500, 800)
        assert result["input_tokens"] == 1500
        assert result["output_tokens"] == 800

    def test_typical_chat_request(self):
        # Typical single-tool chat: ~2000 input, ~500 output
        result = calculate_cost(2000, 500)
        assert result["total_cost_usd"] <= 0.01  # Should be about 1 cent
        assert result["total_cost_usd"] > 0


class TestCalculateBatchCost:
    def test_empty_batch(self):
        result = calculate_batch_cost([])
        assert result["request_count"] == 0
        assert result["total_cost_usd"] == 0
        assert result["avg_cost_per_request_usd"] == 0

    def test_single_request(self):
        result = calculate_batch_cost([
            {"input_tokens": 1000, "output_tokens": 500},
        ])
        assert result["request_count"] == 1
        assert result["total_input_tokens"] == 1000
        assert result["total_output_tokens"] == 500
        assert result["total_cost_usd"] == result["avg_cost_per_request_usd"]

    def test_multiple_requests(self):
        result = calculate_batch_cost([
            {"input_tokens": 1000, "output_tokens": 500},
            {"input_tokens": 2000, "output_tokens": 1000},
            {"input_tokens": 3000, "output_tokens": 1500},
        ])
        assert result["request_count"] == 3
        assert result["total_input_tokens"] == 6000
        assert result["total_output_tokens"] == 3000
        assert len(result["per_request"]) == 3

    def test_avg_cost_calculation(self):
        result = calculate_batch_cost([
            {"input_tokens": 1000, "output_tokens": 500},
            {"input_tokens": 1000, "output_tokens": 500},
        ])
        assert result["avg_cost_per_request_usd"] == result["total_cost_usd"] / 2

    def test_mixed_models(self):
        result = calculate_batch_cost([
            {"input_tokens": 1000, "output_tokens": 500, "model": "gpt-4o"},
            {"input_tokens": 1000, "output_tokens": 500, "model": "gpt-4o-mini"},
        ])
        assert result["request_count"] == 2
        # gpt-4o costs more than gpt-4o-mini
        gpt4o_cost = result["per_request"][0]["total_cost_usd"]
        mini_cost = result["per_request"][1]["total_cost_usd"]
        assert gpt4o_cost > mini_cost

    def test_model_pricing_has_expected_models(self):
        assert "gpt-4o" in MODEL_PRICING
        assert "gpt-4o-mini" in MODEL_PRICING
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert pricing["input"] > 0
            assert pricing["output"] > 0
