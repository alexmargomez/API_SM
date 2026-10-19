FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE ${FRONTEND_PORT:-5173}

CMD ["sh", "-c", "if [ ! -d node_modules/.bin ]; then npm install; fi && npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-5173}"]
