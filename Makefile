.PHONY: build-mcp clean-mcp help

# Detect container runtime
CONTAINER_CMD := $(shell command -v podman 2> /dev/null || command -v docker 2> /dev/null)

build-mcp:
	$(CONTAINER_CMD) build -f Dockerfile.mcp -t prow-audit-mcp:latest .

clean-mcp:
	$(CONTAINER_CMD) rmi prow-audit-mcp:latest

help:
	@echo "Available targets:"
	@echo "  build-mcp  - Build the MCP server container image"
	@echo "  clean-mcp  - Remove the MCP server container image"

