FROM node:16.16-slim

USER node
WORKDIR /home/node/app

# Install dependencies
COPY --chown=node:node package*.json .

RUN npm install --legacy-peer-deps

COPY --chown=node:node . .

CMD ["npm", "start"]
