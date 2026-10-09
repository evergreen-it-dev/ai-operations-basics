.PHONY: agent-bridge agent-bridge-check

agent-bridge:
	python3 tools/agents/sync_agent_bridge.py

agent-bridge-check:
	python3 tools/agents/sync_agent_bridge.py --check
