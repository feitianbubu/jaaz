# ---- Stage 1: Build the React Frontend ----
# Use a Node.js image to build our frontend assets
FROM node:20-alpine AS frontend-builder

# Set the working directory for the frontend
WORKDIR /app/react

# Copy package files and install dependencies first to leverage Docker cache
COPY react/package.json react/package-lock.json ./
RUN npm install --force

# Copy the rest of the frontend source code
COPY react/ ./

# Build the frontend application
RUN npm run build

# ---- Stage 2: Build the Python Backend ----
# Use a Python image to install backend dependencies
FROM python:3.11-slim AS backend-builder

# Set the working directory for the backend
WORKDIR /app/server

# Install Python dependencies
COPY server/requirements.txt .
# Using --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r requirements.txt


# ---- Stage 3: Create the Final Production Image ----
# Use a slim Python image for the final application
FROM python:3.11-slim

# Set the working directory in the final image
WORKDIR /app

# Create a non-root user for security
RUN addgroup --system app && adduser --system --group app

# Copy installed Python dependencies from the backend-builder stage
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# ALSO COPY THE EXECUTABLES (like uvicorn)
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy the backend source code
# We copy the whole server directory
COPY server/ ./server/

# Copy the built frontend from the frontend-builder stage
# The backend will serve these static files
COPY --from=frontend-builder /app/react/dist ./ui

# Copy the entrypoint script and make it executable
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the environment variable for the backend to find the UI files
ENV UI_DIST_DIR=/app/ui

# Change ownership of the app directory to the non-root user
# This is for files copied into /app, not for mounted volumes
RUN chown -R app:app /app

# Expose the port the app will run on
EXPOSE 57988

# Set the entrypoint to our script
# The script will handle changing ownership of mounted volumes
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Switch to the non-root user BEFORE running the CMD
USER app

# CMD provides the default command to be executed by the ENTRYPOINT script
CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "57988", "--app-dir", "/app/server"]