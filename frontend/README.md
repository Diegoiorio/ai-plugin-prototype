# Nuxt Minimal Starter

Look at the [Nuxt documentation](https://nuxt.com/docs/getting-started/introduction) to learn more.

## Setup

Make sure to install dependencies:

```bash
# npm
npm install

# pnpm
pnpm install

# yarn
yarn install

# bun
bun install
```

## Development Server

Start the development server on `http://localhost:3000`:

```bash
# npm
npm run dev

# pnpm
pnpm dev

# yarn
yarn dev

# bun
bun run dev
```

## Backend API

The frontend relies on the FastAPI backend exposed on `http://localhost:8000`.

Start the PostgreSQL database from the project root:

```bash
docker compose up -d postgres
```

Then start the backend from the `backend` folder.

On Windows (PowerShell):

```bash
# create the virtual environment if needed
python -m venv .venv

# activate it on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# install dependencies
pip install -r requirements.txt

# run the API
uvicorn main:app --reload --port 8000
```

On Linux / WSL / macOS:

```bash
# create the virtual environment if needed
python3 -m venv .venv

# activate it
source .venv/bin/activate

# run the API
uvicorn main:app --reload --port 8000

# install dependencies
pip install -r requirements.txt
```

The backend reads `DATABASE_URL` from `backend/.env`. With the current setup, the health check is available at `http://localhost:8000/health`.
For the swagger: `http://localhost:8000/docs#/`

## Production

Build the application for production:

```bash
# npm
npm run build

# pnpm
pnpm build

# yarn
yarn build

# bun
bun run build
```

Locally preview production build:

```bash
# npm
npm run preview

# pnpm
pnpm preview

# yarn
yarn preview

# bun
bun run preview
```

Check out the [deployment documentation](https://nuxt.com/docs/getting-started/deployment) for more information.
