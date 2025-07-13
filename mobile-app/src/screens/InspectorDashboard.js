import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Card, Title, Paragraph, Button } from 'react-native-paper';

const InspectorDashboard = ({ navigation }) => {
  const [recentInspections] = useState([
    {
      id: '1',
      address: '123 Main Street, Anytown, CA',
      date: '2024-01-15',
      status: 'completed',
      clientName: 'John Smith',
      propertyType: 'Single Family Home',
    },
    {
      id: '2',
      address: '456 Oak Avenue, Somewhere, CA',
      date: '2024-01-14',
      status: 'in_progress',
      clientName: 'Sarah Johnson',
      propertyType: 'Condo',
    },
    {
      id: '3',
      address: '789 Pine Road, Elsewhere, CA',
      date: '2024-01-13',
      status: 'scheduled',
      clientName: 'Mike Davis',
      propertyType: 'Townhouse',
    },
    {
      id: '4',
      address: '321 Elm Street, Nowhere, CA',
      date: '2024-01-12',
      status: 'completed',
      clientName: 'Lisa Wilson',
      propertyType: 'Single Family Home',
    },
  ]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return '#10B981';
      case 'in_progress':
        return '#F59E0B';
      case 'scheduled':
        return '#3B82F6';
      default:
        return '#6B7280';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'in_progress':
        return 'In Progress';
      case 'scheduled':
        return 'Scheduled';
      default:
        return 'Unknown';
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const handleStartNewInspection = () => {
    // Navigate to new inspection flow
    navigation.navigate('NewInspection');
  };

  const handleInspectionPress = (inspection) => {
    // Navigate to inspection details
    navigation.navigate('InspectionDetails', { inspection });
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#F8FAFC" />
      
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Inspector Dashboard</Text>
          <Text style={styles.headerSubtitle}>Welcome back, Inspector!</Text>
        </View>
        <View style={styles.headerIcons}>
          <TouchableOpacity style={styles.iconButton}>
            <MaterialIcons name="notifications" size={24} color="#374151" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.iconButton}>
            <MaterialIcons name="settings" size={24} color="#374151" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Quick Stats */}
        <View style={styles.statsContainer}>
          <View style={styles.statCard}>
            <MaterialIcons name="assignment-turned-in" size={24} color="#10B981" />
            <Text style={styles.statNumber}>12</Text>
            <Text style={styles.statLabel}>This Month</Text>
          </View>
          <View style={styles.statCard}>
            <MaterialIcons name="schedule" size={24} color="#F59E0B" />
            <Text style={styles.statNumber}>3</Text>
            <Text style={styles.statLabel}>Pending</Text>
          </View>
          <View style={styles.statCard}>
            <MaterialIcons name="star" size={24} color="#3B82F6" />
            <Text style={styles.statNumber}>4.8</Text>
            <Text style={styles.statLabel}>Rating</Text>
          </View>
        </View>

        {/* Start New Inspection Button */}
        <TouchableOpacity
          style={styles.newInspectionButton}
          onPress={handleStartNewInspection}
        >
          <MaterialIcons name="add-circle" size={24} color="white" />
          <Text style={styles.newInspectionText}>Start New Inspection</Text>
        </TouchableOpacity>

        {/* Recent Inspections */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Recent Inspections</Text>
            <TouchableOpacity>
              <Text style={styles.viewAllText}>View All</Text>
            </TouchableOpacity>
          </View>

          {recentInspections.map((inspection) => (
            <TouchableOpacity
              key={inspection.id}
              style={styles.inspectionCard}
              onPress={() => handleInspectionPress(inspection)}
            >
              <View style={styles.cardHeader}>
                <View style={styles.addressContainer}>
                  <MaterialIcons name="location-on" size={16} color="#6B7280" />
                  <Text style={styles.address} numberOfLines={1}>
                    {inspection.address}
                  </Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(inspection.status) }]}>
                  <Text style={styles.statusText}>{getStatusText(inspection.status)}</Text>
                </View>
              </View>

              <View style={styles.cardContent}>
                <View style={styles.infoRow}>
                  <MaterialIcons name="person" size={16} color="#6B7280" />
                  <Text style={styles.infoText}>{inspection.clientName}</Text>
                </View>
                <View style={styles.infoRow}>
                  <MaterialIcons name="home" size={16} color="#6B7280" />
                  <Text style={styles.infoText}>{inspection.propertyType}</Text>
                </View>
                <View style={styles.infoRow}>
                  <MaterialIcons name="event" size={16} color="#6B7280" />
                  <Text style={styles.infoText}>{formatDate(inspection.date)}</Text>
                </View>
              </View>

              <View style={styles.cardActions}>
                <TouchableOpacity style={styles.actionButton}>
                  <MaterialIcons name="visibility" size={16} color="#3B82F6" />
                  <Text style={styles.actionText}>View Report</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.actionButton}>
                  <MaterialIcons name="edit" size={16} color="#10B981" />
                  <Text style={styles.actionText}>Edit</Text>
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          ))}
        </View>
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
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 2,
  },
  headerIcons: {
    flexDirection: 'row',
    gap: 12,
  },
  iconButton: {
    padding: 8,
  },
  content: {
    flex: 1,
    paddingHorizontal: 20,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 20,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 4,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statNumber: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  newInspectionButton: {
    backgroundColor: '#3B82F6',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 12,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  newInspectionText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  section: {
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
  },
  viewAllText: {
    fontSize: 14,
    color: '#3B82F6',
    fontWeight: '500',
  },
  inspectionCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  addressContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 8,
  },
  address: {
    fontSize: 14,
    fontWeight: '500',
    color: '#111827',
    marginLeft: 4,
    flex: 1,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '500',
    color: 'white',
  },
  cardContent: {
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  infoText: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 6,
  },
  cardActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 16,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionText: {
    fontSize: 12,
    fontWeight: '500',
    marginLeft: 4,
  },
});

export default InspectorDashboard; 