import Constants from 'expo-constants';

export default {
  expo: {
    name: "House Whisperer AI",
    slug: "house-whisperer-mobile",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    splash: {
      image: "./assets/splash.png",
      resizeMode: "contain",
      backgroundColor: "#ffffff"
    },
    assetBundlePatterns: [
      "**/*"
    ],
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.housewhisperer.mobile"
    },
    android: {
      adaptiveIcon: {
        foregroundImage: "./assets/adaptive-icon.png",
        backgroundColor: "#FFFFFF"
      },
      package: "com.housewhisperer.mobile"
    },
    web: {
      favicon: "./assets/favicon.png"
    },
    plugins: [
      [
        "expo-av",
        {
          "microphonePermission": "Allow House Whisperer to access your microphone."
        }
      ],
      [
        "expo-camera",
        {
          "cameraPermission": "Allow House Whisperer to access your camera."
        }
      ],
      [
        "expo-image-picker",
        {
          "photosPermission": "Allow House Whisperer to access your photos."
        }
      ],
      [
        "expo-media-library",
        {
          "photosPermission": "Allow House Whisperer to access your photos.",
          "savePhotosPermission": "Allow House Whisperer to save photos.",
          "isAccessMediaLocationEnabled": true
        }
      ]
    ],
    extra: {
      // Firebase configuration from environment variables
      firebaseApiKey: process.env.FIREBASE_API_KEY || Constants.expoConfig?.extra?.firebaseApiKey,
      firebaseAuthDomain: process.env.FIREBASE_AUTH_DOMAIN || Constants.expoConfig?.extra?.firebaseAuthDomain,
      firebaseProjectId: process.env.FIREBASE_PROJECT_ID || Constants.expoConfig?.extra?.firebaseProjectId,
      firebaseStorageBucket: process.env.FIREBASE_STORAGE_BUCKET || Constants.expoConfig?.extra?.firebaseStorageBucket,
      firebaseMessagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID || Constants.expoConfig?.extra?.firebaseMessagingSenderId,
      firebaseAppId: process.env.FIREBASE_APP_ID || Constants.expoConfig?.extra?.firebaseAppId,
      backendApiUrl: process.env.BACKEND_API_URL || Constants.expoConfig?.extra?.backendApiUrl,
      eas: {
        projectId: "your-eas-project-id"
      }
    },
    updates: {
      fallbackToCacheTimeout: 0,
      url: "https://u.expo.dev/your-project-id"
    },
    runtimeVersion: {
      policy: "appVersion"
    }
  }
}; 