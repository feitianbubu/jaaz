# Makefile for Jaaz Application
# =================================

# --- Configuration ---
# IMPORTANT: Set your Docker registry/username here.
# For Docker Hub, this is just your username.
# For other registries, it might be a URL (e.g., ghcr.io/your-org).
DOCKER_REGISTRY ?= skynono

# --- Image Details ---
IMAGE_NAME      ?= jaaz
# Default tag is the short git commit hash. This is a best practice for versioning.
TAG             ?= $(shell git describe --tags --always --dirty)
# Combine into numeric version (e.g., 1.0.16.17 or 1.0.16.0)
NUMERIC_VERSION := $(shell echo "$(TAG)" | sed 's/^v//' | awk -F'-' '{printf "%s.%s", $$1, ($$2=="")?0:$$2}')
LATEST_TAG      ?= latest

FULL_IMAGE_NAME = $(DOCKER_REGISTRY)/$(IMAGE_NAME)

# --- Targets ---

# Phony targets are not actual files. This is a best practice.
.PHONY: help build push publish build-win

# Default target: running `make` without arguments will show the help message.
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo "  build         Build the Docker image with tags: $(TAG) and $(LATEST_TAG)"
	@echo "  push          Push the built image to the configured registry."
	@echo "  publish       A shortcut to build and then push the image."
	@echo "  build:win     Build the Windows application."
	@echo ""
	@echo "Configuration (can be overridden):"
	@echo "  DOCKER_REGISTRY=$(DOCKER_REGISTRY)"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  TAG=$(TAG)"

# Target to build the Docker image
build:
	@echo "▶ Building Docker image: $(FULL_IMAGE_NAME):$(TAG) and $(FULL_IMAGE_NAME):$(LATEST_TAG)"
	docker build -t $(FULL_IMAGE_NAME):$(TAG) -t $(FULL_IMAGE_NAME):$(LATEST_TAG) .
	@echo "✔ Build complete."

# Target to push the image to the registry
push:
	@echo "▶ Pushing image to $(DOCKER_REGISTRY)..."
	docker push $(FULL_IMAGE_NAME):$(TAG)
	docker push $(FULL_IMAGE_NAME):$(LATEST_TAG)
	@echo "✔ Push complete."

# Target to build and then publish the image
publish: build push
	@echo "✨ Publish successful: $(FULL_IMAGE_NAME):$(TAG)"

# Target to build the Windows application
build-win:
	@echo "▶ Building Python server..."
	py -m PyInstaller server/main.spec --distpath server/dist --noconfirm
	@echo "✔ Python server build complete."
	@echo "▶ Building Windows application..."
	npm run build:win -- --config.buildVersion=$(NUMERIC_VERSION) --config.win.artifactName="Jaaz Setup $(TAG).exe"
	@echo "✔ Windows application build complete."
