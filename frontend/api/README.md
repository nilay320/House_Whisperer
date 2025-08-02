# House Whisperer RAG API

This directory contains the Vercel Functions for the RAG-powered inspector Q&A system.

## Setup

1. **Environment Variables**
   Create a `.env.local` file in the `frontend` directory with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   QDRANT_URL=https://your-cluster.qdrant.tech
   QDRANT_API_KEY=your_qdrant_api_key
   ```

2. **Qdrant Cloud Setup**
   - Sign up at https://cloud.qdrant.io/
   - Create a new cluster (free tier available)
   - Copy the URL and API key to your `.env.local`

3. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   cd api
   npm install
   ```

## API Endpoints

### POST `/api/chat`
Main RAG chat endpoint for inspector questions.

**Request:**
```json
{
  "message": "What is the required clearance for electrical panels?",
  "sessionId": "optional-session-id"
}
```

**Response:** Server-Sent Events stream with:
- Content chunks: `data: {"content": "..."}\n\n`
- Sources: `data: {"sources": [...], "done": true}\n\n`

### POST `/api/ingest`
Ingest documents into the vector database.

**Request:**
```json
{
  "documents": [
    {
      "source": "Document source",
      "section": "Category",
      "content": "Document content..."
    }
  ],
  "reset": true  // Optional: recreate collection
}
```

**Response:**
```json
{
  "success": true,
  "message": "Ingested X documents into Y chunks",
  "collection": "inspector-standards"
}
```

## Local Development

1. Run the development server:
   ```bash
   cd frontend
   npm run dev
   ```

2. Ingest sample data:
   ```bash
   node scripts/ingest-sample-data.js
   ```

3. Test the chat interface at http://localhost:3000

## Deployment

Deploy to Vercel:
```bash
vercel --prod
```

Make sure to add your environment variables in the Vercel dashboard.