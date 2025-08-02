# Quick Setup Guide for Testing

## 1. Set up Qdrant Cloud (5 minutes)

1. Go to https://cloud.qdrant.io/
2. Sign up for free account
3. Create a new cluster (choose AWS, any region)
4. Click on your cluster and copy:
   - Cluster URL (looks like: https://xxx.aws.cloud.qdrant.io)
   - API Key

## 2. Configure Environment

1. Copy the example env file:
   ```bash
   cp .env.local.example .env.local
   ```

2. Edit `.env.local` and add your keys:
   ```
   OPENAI_API_KEY=sk-...
   QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
   QDRANT_API_KEY=your-qdrant-key
   ```

## 3. Install and Test Locally

```bash
# Install dependencies
cd frontend
npm install
cd api
npm install
cd ..

# Start dev server
npm start

# In another terminal, ingest sample data
npm run ingest:sample

# Test the setup
node scripts/test-setup.js
```

## 4. Test in Browser

1. Open http://localhost:3000
2. Click the chat widget (bottom right)
3. Ask a question like "What is the required clearance for electrical panels?"
4. You should get a response with sources

## 5. Deploy to Vercel

```bash
# Install Vercel CLI if needed
npm i -g vercel

# Deploy
vercel

# Add env vars when prompted or in Vercel dashboard
```

## Troubleshooting

- **"Cannot find module" errors**: Make sure you're in the `frontend` directory
- **API errors**: Check your .env.local file has correct keys
- **No response**: Check browser console for errors
- **Vercel issues**: Make sure env vars are added in Vercel dashboard