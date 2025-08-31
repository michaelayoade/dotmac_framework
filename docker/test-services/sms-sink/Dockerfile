FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S sms-sink -u 1001

# Change ownership
RUN chown -R sms-sink:nodejs /app
USER sms-sink

EXPOSE 3030

CMD ["node", "index.js"]