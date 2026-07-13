FROM node:20-alpine

WORKDIR /app

# Copy package configurations and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite default dev port
EXPOSE 5173

# Start development server on all interfaces
CMD ["npm", "run", "dev", "--", "--host"]
