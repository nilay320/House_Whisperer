# Project Context: House Whisperer

## Project Overview
House Whisperer is an AI-powered home inspection assistant application that helps home inspectors capture, analyze, and generate comprehensive inspection reports.

## Current Implementation State
- **Frontend**: React-based web application with PWA capabilities
- **Mobile App**: React Native application for field inspections
- **Backend**: Python Flask API for PDF processing and AI analysis
- **Database**: Firebase Firestore for data persistence
- **Authentication**: Firebase Auth for user management

## Key Technologies
- **Frontend**: React, Tailwind CSS, PWA
- **Mobile**: React Native, Expo
- **Backend**: Python, Flask, LangChain for AI/RAG
- **Infrastructure**: Firebase, Vercel deployment
- **AI**: PDF processing with RAG (Retrieval Augmented Generation)

## Main Features
1. Voice note capture during inspections
2. Photo capture and annotation
3. AI-powered report generation from inspection data
4. PDF processing and analysis
5. Searchable report viewer
6. Inspector dashboard

## Important Files
- `/frontend/src/App.js`: Main web application entry point
- `/mobile-app/src/screens/`: Mobile app screens (InspectorDashboard, VoiceNoteCapture, AIReportGeneration)
- `/api/app.py`: Backend API server
- `/frontend/src/components/InspectorCapture.js`: Web-based inspection capture component
- `/frontend/src/services/firebase.js`: Firebase configuration
- `CLAUDE.md`: Custom instructions for Claude assistant

## Recent Work
- Fixed MediaRecorder constructor error in InspectorCapture component
- Added PWA functionality for mobile voice/photo capture
- Implemented role support for different user types

## Pending Tasks
- Complete midterm submission requirements
- Test AI report generation with sample PDFs
- Verify Firebase security rules are properly configured
- Ensure mobile app builds correctly

## Session Notes
[Update this section at the end of each work session]

### Last Updated: [Date]
- Work completed: [Summary]
- Files modified: [List]
- Next steps: [Tasks]