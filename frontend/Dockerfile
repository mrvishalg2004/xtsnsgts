FROM node:20-alpine

WORKDIR /app

# Copy package manifests and install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source code
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
