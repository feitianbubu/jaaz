# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jaaz is an open-source AI design agent desktop application built with Electron, React, and FastAPI. It supports image generation/editing, storyboarding, and canvas-based design workflows with both local and cloud AI models.

## Architecture

The project consists of three main components:

1. **Electron App** (`/electron/main.js`) - Desktop application wrapper
2. **React Frontend** (`/react/`) - Vite + TypeScript + React 19 frontend
3. **FastAPI Backend** (`/server/`) - Python backend with WebSocket support

## Development Commands

### Frontend Development
```bash
cd react
npm install --force  # Initial setup
npm run dev          # Start Vite dev server
npm run lint         # Run ESLint
npm run build        # Build production bundle
```

### Backend Development  
```bash
cd server
pip install -r requirements.txt  # Install dependencies
python main.py --port 57988      # Start FastAPI server
```

### Full Development Mode
```bash
# From root directory
npm run dev                    # Runs both frontend and Electron dev
```

### Building & Testing
```bash
# Run tests
npm test                        # Vitest test runner

# Build for production
npm run build:win              # Windows build
npm run build:mac              # macOS build  
npm run build:linux            # Linux build
```

## Key Backend Endpoints

- `/` - Serves React frontend (built files from `react/dist/`)
- `/socket.io/` - WebSocket connection for real-time updates
- API routers under `/routers/` handle different functionality:
  - `config` - Configuration management
  - `agent` - AI agent initialization
  - `workspace` - Project/workspace management
  - `image_tools` - Image generation/editing
  - `canvas` - Canvas operations
  - `chat_router` - Chat functionality
  - `settings` - User settings

## Backend Dependencies

The server uses:
- **FastAPI** for REST API
- **LangGraph + LangChain** for AI agent orchestration
- **SocketIO** for real-time communication
- **Various AI providers** (OpenAI, Claude, Ollama, Replicate)

## Frontend Tech Stack

React 19 app with:
- **Vite** for build tooling
- **TailwindCSS** for styling
- **Zustand** for state management
- **TanStack Router** for routing
- **Radix UI** components
- **Excalidraw** for drawing functionality
- **tldraw** for canvas operations

## Model Integration

The app supports multiple AI model providers:
- **LLMs**: OpenAI, Claude, Deepseek, Ollama (local)
- **Image Generation**: GPT-4O, Replicate, Flux, Google Imagen
- **Backend**: ComfyUI support for advanced workflows