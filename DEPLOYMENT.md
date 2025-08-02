# Deployment Instructions for Vercel

## Prerequisites
1. Install Vercel CLI: `npm install -g vercel`
2. Have your environment variables ready:
   - `OPENAI_API_KEY`
   - `QDRANT_URL`
   - `QDRANT_API_KEY`

## Deployment Steps

### 1. Login to Vercel
```bash
vercel login
```

### 2. Deploy from Root Directory
```bash
cd /path/to/House_Whisperer
vercel
```

### 3. Configure Project (First Time)
When prompted:
- Set up and deploy: `Y`
- Which scope: Select your account
- Link to existing project: `N` (first time) or `Y` (subsequent)
- Project name: `house-whisperer` (or your choice)
- Directory: `./` (the root directory)
- Override settings: `Y`
  - Build Command: `cd frontend && npm run build`
  - Output Directory: `frontend/build`
  - Install Command: `cd frontend && npm install`

### 4. Set Environment Variables
```bash
# Set production environment variables
vercel env add OPENAI_API_KEY production
vercel env add QDRANT_URL production  
vercel env add QDRANT_API_KEY production
```

Or add them in Vercel Dashboard:
1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add each variable for "Production" environment

### 5. Deploy to Production
```bash
vercel --prod
```

## Important Notes

### API Endpoint
- Local: `http://localhost:8000/api/chat`
- Production: `https://your-app.vercel.app/api/chat`

### CORS Configuration
The API automatically configures CORS for:
- `localhost:3000` (development)
- `*.vercel.app` (preview deployments)
- Your production domain

### Limitations
- Vercel serverless functions have a 30-second timeout
- For longer operations, consider using Vercel Edge Functions or external hosting

### Testing Deployment
After deployment, test your API:
```bash
curl https://your-app.vercel.app/api/health
```

## Alternative: Deploy Backend Separately

If you need longer timeouts or more control, deploy the FastAPI backend to:
- **Railway**: `railway up` (great for Python apps)
- **Render**: Free tier available
- **Fly.io**: Good for containerized apps
- **AWS Lambda**: Using Mangum adapter

Then update `frontend/.env.production`:
```
REACT_APP_API_URL=https://your-backend-api.com
```

## Troubleshooting

### "Module not found" errors
- Ensure all imports use relative paths
- Check that requirements.txt includes all dependencies

### CORS errors
- Verify environment variables are set
- Check browser console for specific domain issues

### Function timeout
- Optimize LangGraph agents for speed
- Consider streaming responses
- Use external backend for complex operations