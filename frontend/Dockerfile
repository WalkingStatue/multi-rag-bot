FROM node:18-alpine

WORKDIR /app

# Set Docker environment variable
ENV DOCKER=true

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start development server with Docker mode
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
