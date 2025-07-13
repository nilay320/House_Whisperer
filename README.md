# Home Inspection AI Assistant

A comprehensive AI-powered platform for home inspectors and buyers, featuring both web and mobile applications.

## 🏗️ Project Structure

```
Home_inspector_assitant/
├── api/                    # Backend API (Python/Flask)
├── frontend/              # React Web Application
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── screens/       # Page components
│   │   └── services/      # API and Firebase services
├── mobile-app/            # React Native Mobile Application
│   ├── src/
│   │   ├── components/    # Mobile UI components
│   │   └── screens/       # Mobile screen components
└── README.md
```

## 🚀 Features

### Web Application (React)
- **Authentication System**: Firebase-powered login/signup with Google integration
- **Chatbot Widget**: AI-powered chat interface for buyers to ask questions about inspection reports
- **PDF Upload**: Drag-and-drop functionality for inspection report uploads
- **Responsive Design**: Modern, professional UI optimized for all devices

### Mobile Application (React Native)
- **Inspector Dashboard**: Overview of recent inspections with quick stats
- **Voice Note Capture**: Record voice notes with play/pause functionality
- **Photo Capture**: Take photos or upload from gallery with text notes
- **AI Report Generation**: Collapsible sections for reviewing and editing AI-generated reports
- **Searchable Report Viewer**: Keyword search with highlighted results and expandable context

## 🛠️ Technology Stack

### Frontend (Web)
- **React 18** with React Router
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **Firebase** for authentication
- **React Hook Form** for form handling
- **React Dropzone** for file uploads

### Mobile App
- **React Native** with Expo
- **React Navigation** for routing
- **Expo AV** for audio recording
- **Expo Camera/Image Picker** for photo capture
- **React Native Paper** for UI components
- **Material Icons** for icons

### Backend
- **Python/Flask** API
- **Firebase** for authentication and storage
- **Vector storage** for AI processing

## 📱 Screens & Components

### Web Application
1. **Authentication Screen** (`frontend/src/screens/AuthScreen.js`)
   - Email/password login and signup
   - Google authentication
   - Form validation and error handling

2. **Chatbot Widget** (`frontend/src/components/ChatbotWidget.js`)
   - Floating chat interface
   - PDF upload functionality
   - AI-powered responses
   - Real-time messaging

### Mobile Application
1. **Inspector Dashboard** (`mobile-app/src/screens/InspectorDashboard.js`)
   - Recent inspections list
   - Quick statistics
   - Start new inspection button
   - Modern card-based UI

2. **Voice Note Capture** (`mobile-app/src/screens/VoiceNoteCapture.js`)
   - Voice recording with play/pause
   - Photo capture and upload
   - Text notes for images
   - Clean mobile-friendly interface

3. **AI Report Generation** (`mobile-app/src/screens/AIReportGeneration.js`)
   - Collapsible accordion sections
   - Editable text fields
   - Approve/edit functionality
   - Progress tracking

4. **Searchable Report Viewer** (`mobile-app/src/components/SearchableReportViewer.js`)
   - Keyword search functionality
   - Highlighted search results
   - Expandable context views
   - Mobile-optimized interface

## 🚀 Getting Started

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn
- Expo CLI (for mobile development)
- Firebase project setup

### Web Application Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure Firebase**:
   Create a `.env` file in the `frontend` directory:
   ```
   REACT_APP_FIREBASE_API_KEY=your_api_key
   REACT_APP_FIREBASE_AUTH_DOMAIN=your_auth_domain
   REACT_APP_FIREBASE_PROJECT_ID=your_project_id
   REACT_APP_FIREBASE_STORAGE_BUCKET=your_storage_bucket
   REACT_APP_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   REACT_APP_FIREBASE_APP_ID=your_app_id
   ```

3. **Start the development server**:
   ```bash
   npm start
   ```

### Mobile Application Setup

1. **Install dependencies**:
   ```bash
   cd mobile-app
   npm install
   ```

2. **Start the Expo development server**:
   ```bash
   npm start
   ```

3. **Run on device/simulator**:
   - Scan QR code with Expo Go app
   - Press 'i' for iOS simulator
   - Press 'a' for Android emulator

## 🎨 Design System

### Color Palette
- **Primary Blue**: #3B82F6
- **Success Green**: #10B981
- **Warning Orange**: #F59E0B
- **Error Red**: #EF4444
- **Gray Scale**: #111827, #374151, #6B7280, #9CA3AF, #E5E7EB

### Typography
- **Headers**: Bold, 18-24px
- **Body Text**: Regular, 14-16px
- **Captions**: Regular, 12-14px

### Components
- **Cards**: Rounded corners (12px), subtle shadows
- **Buttons**: Primary actions (blue), secondary (gray), destructive (red)
- **Inputs**: Clean borders, focus states with blue ring
- **Icons**: Material Design icons throughout

## 🔧 Development

### Code Style
- **React**: Functional components with hooks
- **JavaScript**: ES6+ features, consistent naming
- **CSS**: Tailwind utility classes, custom components when needed
- **Mobile**: React Native best practices, platform-specific considerations

### File Organization
- **Components**: Reusable, single responsibility
- **Screens**: Page-level components
- **Services**: API calls, Firebase integration
- **Utils**: Helper functions, constants

## 📦 Deployment

### Web Application
- Build: `npm run build`
- Deploy to Vercel, Netlify, or Firebase Hosting

### Mobile Application
- Build: `expo build:android` or `expo build:ios`
- Submit to App Store/Google Play Store

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support, please open an issue in the repository or contact the development team. 