FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY server.js ./

# Create non-root user for security
RUN addgroup -g 1001 -S mockidp && \
    adduser -S mockidp -u 1001

# Set ownership
RUN chown -R mockidp:mockidp /app
USER mockidp

# Expose port
EXPOSE 8040

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8040/health || exit 1

# Start the server
CMD ["npm", "start"]