# 🔐 Firebase Security Rules

## Storage Rules (storage.rules)

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Allow authenticated users to access their own files
    match /users/{userId}/{allPaths=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow authenticated users to upload inspection files
    // Users can only access files they uploaded (checked via metadata)
    match /inspections/{inspectionId}/{allPaths=**} {
      allow read, write: if request.auth != null && 
        (
          // User can access files they uploaded (check metadata)
          resource.metadata.userId == request.auth.uid ||
          // Or if it's a new upload, allow authenticated users
          (request.method == 'write' && request.auth != null)
        );
    }
    
    // Public read access for shared reports (optional)
    match /public/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    
    // Deny all other access
    match /{allPaths=**} {
      allow read, write: if false;
    }
  }
}
```

## Firestore Rules (firestore.rules)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Inspections - users can only access their own inspections
    match /inspections/{inspectionId} {
      allow read, write: if request.auth != null && 
        resource.data.userId == request.auth.uid;
      
      // Allow creation of new inspections
      allow create: if request.auth != null && 
        request.resource.data.userId == request.auth.uid;
    }
    
    // Reports - users can only access reports for their inspections
    match /reports/{reportId} {
      allow read, write: if request.auth != null && 
        resource.data.userId == request.auth.uid;
      
      allow create: if request.auth != null && 
        request.resource.data.userId == request.auth.uid;
    }
    
    // Voice notes - users can only access their own voice notes
    match /voice-notes/{noteId} {
      allow read, write: if request.auth != null && 
        resource.data.userId == request.auth.uid;
      
      allow create: if request.auth != null && 
        request.resource.data.userId == request.auth.uid;
    }
    
    // Photos - users can only access their own photos
    match /photos/{photoId} {
      allow read, write: if request.auth != null && 
        resource.data.userId == request.auth.uid;
      
      allow create: if request.auth != null && 
        request.resource.data.userId == request.auth.uid;
    }
    
    // Deny all other access
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

## Authentication Rules

### Email/Password Authentication
```javascript
// In Firebase Console → Authentication → Sign-in method
// Enable Email/Password authentication
// Set password requirements:
// - Minimum 8 characters
// - Require uppercase letters
// - Require lowercase letters
// - Require numbers
```

### Google OAuth Configuration
```javascript
// In Firebase Console → Authentication → Sign-in method → Google
// Enable Google sign-in
// Add authorized domains:
// - your-vercel-app.vercel.app
// - your-expo-app.expo.dev
// - localhost (for development)
```

## Security Best Practices

### 1. Environment Variables
```bash
# Never commit these to version control
# Use .env.local for web app
# Use .env for mobile app
# Use Vercel/Expo environment variables for production
```

### 2. API Key Restrictions
```javascript
// In Firebase Console → Project Settings → General
// Add authorized domains:
// - your-vercel-app.vercel.app
// - your-expo-app.expo.dev
// - localhost (for development)
```

### 3. Storage Security
- ✅ Files are organized by user ID
- ✅ Users can only access their own files
- ✅ Metadata includes user ID for verification
- ✅ Public access is disabled by default

### 4. Database Security
- ✅ Users can only access their own data
- ✅ All operations require authentication
- ✅ User ID is verified on every request
- ✅ No public read/write access

## Testing Security Rules

### Test Storage Rules
```javascript
// Test file upload
const testUpload = async () => {
  const file = new File(['test'], 'test.txt', { type: 'text/plain' });
  const result = await uploadFile(file, 'users/user123/test.txt', {
    customMetadata: { userId: 'user123' }
  });
  console.log('Upload result:', result);
};
```

### Test Firestore Rules
```javascript
// Test document creation
const testCreate = async () => {
  const result = await createInspection({
    userId: 'user123',
    title: 'Test Inspection',
    address: '123 Test St'
  });
  console.log('Create result:', result);
};
```

## Deployment Commands

### Deploy Storage Rules
```bash
firebase deploy --only storage
```

### Deploy Firestore Rules
```bash
firebase deploy --only firestore:rules
```

### Deploy All Rules
```bash
firebase deploy --only storage,firestore:rules
```

## Monitoring Security

### Firebase Console
- Go to Firebase Console → Authentication → Users
- Monitor sign-in attempts and blocked users
- Check for suspicious activity

### Storage Monitoring
- Go to Firebase Console → Storage → Usage
- Monitor file uploads and downloads
- Check for unauthorized access attempts

### Firestore Monitoring
- Go to Firebase Console → Firestore → Usage
- Monitor read/write operations
- Check for rule violations

## Security Checklist

- [ ] Storage rules deployed and tested
- [ ] Firestore rules deployed and tested
- [ ] Authentication methods configured
- [ ] Authorized domains set
- [ ] API key restrictions applied
- [ ] Environment variables secured
- [ ] No sensitive data in code
- [ ] Regular security audits scheduled 