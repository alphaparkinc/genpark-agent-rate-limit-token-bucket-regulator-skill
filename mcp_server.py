import sys, json
from client import AgentRateLimitRegulator

def handle_mcp():
    regulator = AgentRateLimitRegulator()
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(json.dumps(regulator.run_rate_limiter_benchmark(), indent=2))
        return

    for line in sys.stdin:
        if not line.strip(): continue
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "initialize":
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "genpark-agent-rate-limit-token-bucket-regulator-skill", "version": "1.0.0"},
                    "capabilities": {"tools": {}}
                }}
            elif method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": [
                    {"name": "configure_provider", "description": "Configure provider limits.", "inputSchema": {"type": "object", "properties": {"provider_id": {"type": "string"}, "max_rpm": {"type": "integer"}, "max_tpm": {"type": "integer"}}}},
                    {"name": "acquire_tokens", "description": "Reserve tokens from bucket.", "inputSchema": {"type": "object", "properties": {"provider_id": {"type": "string"}, "estimated_tokens": {"type": "integer"}}}},
                    {"name": "get_provider_status", "description": "Get real-time provider saturation.", "inputSchema": {"type": "object", "properties": {"provider_id": {"type": "string"}}}},
                    {"name": "run_rate_limiter_benchmark", "description": "Run rate limiter benchmark.", "inputSchema": {"type": "object"}}
                ]}}
            elif method == "tools/call":
                tname = req.get("params", {}).get("name")
                args = req.get("params", {}).get("arguments", {})
                if tname == "configure_provider":
                    res = regulator.configure_provider(args.get("provider_id", "p1"), args.get("max_rpm", 60), args.get("max_tpm", 40000))
                elif tname == "acquire_tokens":
                    res = regulator.acquire_tokens(args.get("provider_id", "p1"), args.get("estimated_tokens", 1000))
                elif tname == "get_provider_status":
                    res = regulator.get_provider_status(args.get("provider_id", "p1"))
                else:
                    res = regulator.run_rate_limiter_benchmark()
                resp = {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}}
            else:
                resp = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
            
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    handle_mcp()
