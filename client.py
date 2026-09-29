import sys, json, time, math

class AgentRateLimitRegulator:
    """
    Multi-Provider Token-Bucket & Sliding-Window Rate Limiter.
    Manages Tokens-Per-Minute (TPM) and Requests-Per-Minute (RPM) quotas
    across LLM provider endpoints to eliminate 429 throttling exceptions.
    """
    def __init__(self):
        self.providers = {}

    def configure_provider(self, provider_id, max_rpm=60, max_tpm=40000, burst_multiplier=1.2):
        capacity = int(max_tpm * burst_multiplier)
        self.providers[provider_id] = {
            "provider_id": provider_id,
            "max_rpm": max_rpm,
            "max_tpm": max_tpm,
            "bucket_capacity": capacity,
            "available_tokens": float(capacity),
            "refill_rate_per_sec": max_tpm / 60.0,
            "last_refill_time": time.time(),
            "request_timestamps": [],
            "total_requests": 0,
            "throttled_requests": 0
        }
        return {"status": "CONFIGURED", "provider_id": provider_id, "capacity": capacity}

    def _refill_tokens(self, p):
        now = time.time()
        delta = now - p["last_refill_time"]
        refill_amount = delta * p["refill_rate_per_sec"]
        p["available_tokens"] = min(float(p["bucket_capacity"]), p["available_tokens"] + refill_amount)
        p["last_refill_time"] = now

        # Prune sliding window RPM (older than 60s)
        cutoff = now - 60.0
        p["request_timestamps"] = [t for t in p["request_timestamps"] if t > cutoff]

    def acquire_tokens(self, provider_id, estimated_tokens=1000, wait_if_needed=False, max_wait_seconds=3.0):
        if provider_id not in self.providers:
            self.configure_provider(provider_id)
        p = self.providers[provider_id]
        self._refill_tokens(p)

        now = time.time()
        rpm_current = len(p["request_timestamps"])

        # Check RPM limit
        if rpm_current >= p["max_rpm"]:
            p["throttled_requests"] += 1
            return {"allowed": False, "reason": "RPM_EXCEEDED", "current_rpm": rpm_current, "wait_seconds_est": 1.0}

        # Check Token Bucket
        if p["available_tokens"] >= estimated_tokens:
            p["available_tokens"] -= estimated_tokens
            p["request_timestamps"].append(now)
            p["total_requests"] += 1
            return {
                "allowed": True,
                "allocated_tokens": estimated_tokens,
                "remaining_tokens": int(p["available_tokens"]),
                "current_rpm": len(p["request_timestamps"])
            }
        else:
            deficit = estimated_tokens - p["available_tokens"]
            wait_needed = deficit / p["refill_rate_per_sec"]
            p["throttled_requests"] += 1
            return {
                "allowed": False,
                "reason": "TPM_CAPACITY_EXHAUSTED",
                "deficit_tokens": int(deficit),
                "wait_seconds_est": round(wait_needed, 3)
            }

    def get_provider_status(self, provider_id):
        if provider_id not in self.providers:
            return {"status": "NOT_FOUND"}
        p = self.providers[provider_id]
        self._refill_tokens(p)
        saturation_pct = round(((p["bucket_capacity"] - p["available_tokens"]) / p["bucket_capacity"]) * 100, 2)
        return {
            "provider_id": provider_id,
            "available_tokens": int(p["available_tokens"]),
            "bucket_capacity": p["bucket_capacity"],
            "saturation_pct": saturation_pct,
            "current_rpm": len(p["request_timestamps"]),
            "max_rpm": p["max_rpm"],
            "total_requests": p["total_requests"],
            "throttled_requests": p["throttled_requests"]
        }

    def run_rate_limiter_benchmark(self):
        self.providers.clear()
        self.configure_provider("openai_gpt4o", max_rpm=100, max_tpm=20000)
        self.configure_provider("anthropic_claude", max_rpm=50, max_tpm=10000)

        results = []
        # Simulate burst allocations
        for i in range(5):
            r = self.acquire_tokens("openai_gpt4o", estimated_tokens=3000)
            results.append({"call": i + 1, "provider": "openai_gpt4o", "result": r})

        status = self.get_provider_status("openai_gpt4o")

        return {
            "suite": "Rate Limit Token Bucket Regulator Benchmark",
            "burst_simulation_log": results,
            "final_provider_telemetry": status,
            "engine_state": "ACTIVE_TRAFFIC_PROTECTED"
        }
