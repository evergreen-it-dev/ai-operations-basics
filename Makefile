.PHONY: agent-bridge agent-bridge-check

# На Windows без make: py -3 tools/agents/sync_agent_bridge.py [--check]
# З make на Windows: make PYTHON="py -3" agent-bridge
PYTHON ?= python3

agent-bridge:
	$(PYTHON) tools/agents/sync_agent_bridge.py

agent-bridge-check:
	$(PYTHON) tools/agents/sync_agent_bridge.py --check
