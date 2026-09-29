from client import AgentRateLimitRegulator
import json

regulator = AgentRateLimitRegulator()
print("=== AGENT RATE LIMIT TOKEN BUCKET REGULATOR BENCHMARK ===")
res = regulator.run_rate_limiter_benchmark()
print(json.dumps(res, indent=2))
