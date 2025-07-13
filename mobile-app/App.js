import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { MaterialIcons } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';

// Import screens
import InspectorDashboard from './src/screens/InspectorDashboard';
import VoiceNoteCapture from './src/screens/VoiceNoteCapture';
import AIReportGeneration from './src/screens/AIReportGeneration';
import SearchableReportViewer from './src/components/SearchableReportViewer';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

// Main Tab Navigator
const MainTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'Dashboard') {
            iconName = 'dashboard';
          } else if (route.name === 'Capture') {
            iconName = 'mic';
          } else if (route.name === 'Reports') {
            iconName = 'description';
          } else if (route.name === 'Viewer') {
            iconName = 'search';
          }

          return <MaterialIcons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#3B82F6',
        tabBarInactiveTintColor: '#6B7280',
        tabBarStyle: {
          backgroundColor: 'white',
          borderTopWidth: 1,
          borderTopColor: '#E5E7EB',
          paddingBottom: 5,
          paddingTop: 5,
          height: 60,
        },
        headerShown: false,
      })}
    >
      <Tab.Screen 
        name="Dashboard" 
        component={InspectorDashboard}
        options={{ title: 'Dashboard' }}
      />
      <Tab.Screen 
        name="Capture" 
        component={VoiceNoteCapture}
        options={{ title: 'Capture' }}
      />
      <Tab.Screen 
        name="Reports" 
        component={AIReportGeneration}
        options={{ title: 'Reports' }}
      />
      <Tab.Screen 
        name="Viewer" 
        component={SearchableReportViewer}
        options={{ title: 'Viewer' }}
      />
    </Tab.Navigator>
  );
};

// Root Stack Navigator
const RootStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="Main" component={MainTabs} />
    </Stack.Navigator>
  );
};

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="auto" />
      <RootStack />
    </NavigationContainer>
  );
} 