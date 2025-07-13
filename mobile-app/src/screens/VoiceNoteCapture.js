import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  TextInput,
  Alert,
  Image,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as ImagePicker from 'expo-image-picker';
import { Button, Card, Title, Paragraph } from 'react-native-paper';

const VoiceNoteCapture = ({ navigation }) => {
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [recordedNotes, setRecordedNotes] = useState([]);
  const [currentTextNote, setCurrentTextNote] = useState('');
  const [capturedImages, setCapturedImages] = useState([]);
  const [sound, setSound] = useState(null);
  const recordingRef = useRef(null);

  // Request permissions on component mount
  React.useEffect(() => {
    (async () => {
      const { status: audioStatus } = await Audio.requestPermissionsAsync();
      const { status: cameraStatus } = await ImagePicker.requestCameraPermissionsAsync();
      const { status: mediaLibraryStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      
      if (audioStatus !== 'granted') {
        Alert.alert('Permission needed', 'Audio recording permission is required');
      }
      if (cameraStatus !== 'granted') {
        Alert.alert('Permission needed', 'Camera permission is required');
      }
      if (mediaLibraryStatus !== 'granted') {
        Alert.alert('Permission needed', 'Media library permission is required');
      }
    })();
  }, []);

  const startRecording = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      
      setRecording(recording);
      setIsRecording(true);
      recordingRef.current = recording;
    } catch (err) {
      console.error('Failed to start recording', err);
      Alert.alert('Error', 'Failed to start recording');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    setIsRecording(false);
    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    setRecording(null);
    recordingRef.current = null;

    // Add to recorded notes
    const newNote = {
      id: Date.now().toString(),
      type: 'voice',
      uri: uri,
      timestamp: new Date().toISOString(),
      duration: '00:30', // Mock duration
    };
    setRecordedNotes([...recordedNotes, newNote]);
  };

  const playRecording = async (uri) => {
    try {
      if (sound) {
        await sound.unloadAsync();
      }
      
      const { sound: newSound } = await Audio.Sound.createAsync({ uri });
      setSound(newSound);
      setIsPlaying(true);
      
      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.didJustFinish) {
          setIsPlaying(false);
        }
      });
      
      await newSound.playAsync();
    } catch (err) {
      console.error('Failed to play recording', err);
      Alert.alert('Error', 'Failed to play recording');
    }
  };

  const stopPlaying = async () => {
    if (sound) {
      await sound.stopAsync();
      setIsPlaying(false);
    }
  };

  const takePhoto = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        const newImage = {
          id: Date.now().toString(),
          uri: result.assets[0].uri,
          timestamp: new Date().toISOString(),
          textNote: '',
        };
        setCapturedImages([...capturedImages, newImage]);
      }
    } catch (err) {
      console.error('Failed to take photo', err);
      Alert.alert('Error', 'Failed to take photo');
    }
  };

  const pickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        const newImage = {
          id: Date.now().toString(),
          uri: result.assets[0].uri,
          timestamp: new Date().toISOString(),
          textNote: '',
        };
        setCapturedImages([...capturedImages, newImage]);
      }
    } catch (err) {
      console.error('Failed to pick image', err);
      Alert.alert('Error', 'Failed to pick image');
    }
  };

  const addTextNote = (imageId, text) => {
    setCapturedImages(prevImages =>
      prevImages.map(img =>
        img.id === imageId ? { ...img, textNote: text } : img
      )
    );
  };

  const deleteNote = (id, type) => {
    if (type === 'voice') {
      setRecordedNotes(prevNotes => prevNotes.filter(note => note.id !== id));
    } else {
      setCapturedImages(prevImages => prevImages.filter(img => img.id !== id));
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#F8FAFC" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <MaterialIcons name="arrow-back" size={24} color="#374151" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Voice & Photo Notes</Text>
        <TouchableOpacity>
          <MaterialIcons name="save" size={24} color="#3B82F6" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Voice Recording Section */}
        <Card style={styles.section}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Voice Recording</Title>
            <View style={styles.recordingControls}>
              <TouchableOpacity
                style={[styles.recordButton, isRecording && styles.recordingActive]}
                onPress={isRecording ? stopRecording : startRecording}
              >
                <MaterialIcons
                  name={isRecording ? 'stop' : 'mic'}
                  size={32}
                  color="white"
                />
              </TouchableOpacity>
              <Text style={styles.recordingText}>
                {isRecording ? 'Recording...' : 'Tap to record'}
              </Text>
            </View>
          </Card.Content>
        </Card>

        {/* Photo Capture Section */}
        <Card style={styles.section}>
          <Card.Content>
            <Title style={styles.sectionTitle}>Photo Capture</Title>
            <View style={styles.photoControls}>
              <TouchableOpacity style={styles.photoButton} onPress={takePhoto}>
                <MaterialIcons name="camera-alt" size={24} color="white" />
                <Text style={styles.photoButtonText}>Take Photo</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.photoButton} onPress={pickImage}>
                <MaterialIcons name="photo-library" size={24} color="white" />
                <Text style={styles.photoButtonText}>Upload Photo</Text>
              </TouchableOpacity>
            </View>
          </Card.Content>
        </Card>

        {/* Recorded Voice Notes */}
        {recordedNotes.length > 0 && (
          <Card style={styles.section}>
            <Card.Content>
              <Title style={styles.sectionTitle}>Voice Notes</Title>
              {recordedNotes.map((note) => (
                <View key={note.id} style={styles.noteItem}>
                  <View style={styles.noteHeader}>
                    <MaterialIcons name="mic" size={20} color="#6B7280" />
                    <Text style={styles.noteTimestamp}>
                      {formatTimestamp(note.timestamp)}
                    </Text>
                    <TouchableOpacity
                      onPress={() => deleteNote(note.id, 'voice')}
                      style={styles.deleteButton}
                    >
                      <MaterialIcons name="delete" size={20} color="#EF4444" />
                    </TouchableOpacity>
                  </View>
                  <View style={styles.audioControls}>
                    <TouchableOpacity
                      style={styles.playButton}
                      onPress={() => isPlaying ? stopPlaying() : playRecording(note.uri)}
                    >
                      <MaterialIcons
                        name={isPlaying ? 'pause' : 'play-arrow'}
                        size={24}
                        color="white"
                      />
                    </TouchableOpacity>
                    <Text style={styles.duration}>{note.duration}</Text>
                  </View>
                </View>
              ))}
            </Card.Content>
          </Card>
        )}

        {/* Captured Images */}
        {capturedImages.length > 0 && (
          <Card style={styles.section}>
            <Card.Content>
              <Title style={styles.sectionTitle}>Photos</Title>
              {capturedImages.map((image) => (
                <View key={image.id} style={styles.imageItem}>
                  <View style={styles.imageHeader}>
                    <MaterialIcons name="photo" size={20} color="#6B7280" />
                    <Text style={styles.noteTimestamp}>
                      {formatTimestamp(image.timestamp)}
                    </Text>
                    <TouchableOpacity
                      onPress={() => deleteNote(image.id, 'image')}
                      style={styles.deleteButton}
                    >
                      <MaterialIcons name="delete" size={20} color="#EF4444" />
                    </TouchableOpacity>
                  </View>
                  <Image source={{ uri: image.uri }} style={styles.capturedImage} />
                  <TextInput
                    style={styles.textNoteInput}
                    placeholder="Add a note to this photo..."
                    value={image.textNote}
                    onChangeText={(text) => addTextNote(image.id, text)}
                    multiline
                  />
                </View>
              ))}
            </Card.Content>
          </Card>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8FAFC',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
  },
  section: {
    marginTop: 16,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 16,
  },
  recordingControls: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  recordingActive: {
    backgroundColor: '#EF4444',
  },
  recordingText: {
    fontSize: 14,
    color: '#6B7280',
  },
  photoControls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 20,
  },
  photoButton: {
    backgroundColor: '#10B981',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  photoButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
    marginLeft: 8,
  },
  noteItem: {
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  noteHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  noteTimestamp: {
    fontSize: 12,
    color: '#6B7280',
    marginLeft: 6,
    flex: 1,
  },
  deleteButton: {
    padding: 4,
  },
  audioControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  playButton: {
    backgroundColor: '#3B82F6',
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  duration: {
    fontSize: 14,
    color: '#6B7280',
  },
  imageItem: {
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  imageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  capturedImage: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    marginBottom: 8,
  },
  textNoteInput: {
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 6,
    padding: 8,
    fontSize: 14,
    color: '#374151',
    backgroundColor: 'white',
  },
});

export default VoiceNoteCapture; 