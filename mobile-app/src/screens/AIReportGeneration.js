import React, { useState } from 'react';
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
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Card, Title, Paragraph, Button } from 'react-native-paper';

const AIReportGeneration = ({ navigation }) => {
  const [expandedSections, setExpandedSections] = useState(new Set(['summary']));
  const [reportData, setReportData] = useState({
    summary: {
      title: 'Executive Summary',
      content: 'This property shows signs of deferred maintenance with several areas requiring attention. The roof has minor damage, plumbing fixtures need updates, and the HVAC system is approaching end-of-life. Overall, the property is structurally sound but would benefit from updates and repairs.',
      isEditing: false,
      isApproved: false,
    },
    roof: {
      title: 'Roof & Exterior',
      content: 'The roof shows signs of aging with some missing shingles and minor water damage. Gutters are clogged and need cleaning. Exterior siding is in good condition with minor paint touch-ups needed. Chimney appears sound with no visible cracks.',
      isEditing: false,
      isApproved: false,
    },
    plumbing: {
      title: 'Plumbing System',
      content: 'Main water line is functional but shows signs of corrosion. Hot water heater is 12 years old and should be replaced within 2-3 years. Bathroom fixtures are dated but functional. Kitchen sink has minor leak that should be addressed.',
      isEditing: false,
      isApproved: false,
    },
    electrical: {
      title: 'Electrical System',
      content: 'Electrical panel is up to code with adequate capacity. Outlets are properly grounded. Some light fixtures need bulb replacements. No major electrical issues identified. Smoke detectors are present and functional.',
      isEditing: false,
      isApproved: false,
    },
    hvac: {
      title: 'HVAC System',
      content: 'Central air conditioning unit is 15 years old and showing signs of wear. Furnace is functional but inefficient. Ductwork appears to be in good condition. Thermostat is programmable and working properly. Recommend HVAC replacement within 2 years.',
      isEditing: false,
      isApproved: false,
    },
    foundation: {
      title: 'Foundation & Structure',
      content: 'Foundation appears solid with no visible cracks or settling issues. Basement shows minor moisture but no structural concerns. Floor joists are sound. No evidence of termite damage or other structural issues.',
      isEditing: false,
      isApproved: false,
    },
    interior: {
      title: 'Interior & Finishes',
      content: 'Interior walls and ceilings are in good condition with minor paint touch-ups needed. Flooring is worn but functional. Windows are double-paned and in good condition. Interior doors are functional with some needing adjustment.',
      isEditing: false,
      isApproved: false,
    },
  });

  const toggleSection = (sectionKey) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionKey)) {
      newExpanded.delete(sectionKey);
    } else {
      newExpanded.add(sectionKey);
    }
    setExpandedSections(newExpanded);
  };

  const toggleEditing = (sectionKey) => {
    setReportData(prev => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        isEditing: !prev[sectionKey].isEditing,
      },
    }));
  };

  const updateContent = (sectionKey, newContent) => {
    setReportData(prev => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        content: newContent,
      },
    }));
  };

  const approveSection = (sectionKey) => {
    setReportData(prev => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        isApproved: true,
        isEditing: false,
      },
    }));
  };

  const getApprovalStatus = () => {
    const sections = Object.keys(reportData);
    const approvedSections = sections.filter(key => reportData[key].isApproved);
    return {
      total: sections.length,
      approved: approvedSections.length,
      percentage: Math.round((approvedSections.length / sections.length) * 100),
    };
  };

  const handleFinalizeReport = () => {
    const status = getApprovalStatus();
    if (status.approved === status.total) {
      Alert.alert(
        'Report Complete',
        'All sections have been approved. The report is ready for delivery.',
        [
          { text: 'OK', onPress: () => navigation.navigate('Dashboard') }
        ]
      );
    } else {
      Alert.alert(
        'Incomplete Report',
        `${status.total - status.approved} sections still need approval.`,
        [{ text: 'OK' }]
      );
    }
  };

  const renderSection = (sectionKey, sectionData) => {
    const isExpanded = expandedSections.has(sectionKey);
    const isEditing = sectionData.isEditing;
    const isApproved = sectionData.isApproved;

    return (
      <Card key={sectionKey} style={[styles.sectionCard, isApproved && styles.approvedCard]}>
        <TouchableOpacity onPress={() => toggleSection(sectionKey)}>
          <View style={styles.sectionHeader}>
            <View style={styles.sectionTitleContainer}>
              <MaterialIcons
                name={isExpanded ? 'expand-less' : 'expand-more'}
                size={24}
                color="#374151"
              />
              <Text style={styles.sectionTitle}>{sectionData.title}</Text>
              {isApproved && (
                <MaterialIcons name="check-circle" size={20} color="#10B981" />
              )}
            </View>
            <View style={styles.sectionActions}>
              {!isApproved && (
                <>
                  <TouchableOpacity
                    style={styles.actionButton}
                    onPress={() => toggleEditing(sectionKey)}
                  >
                    <MaterialIcons
                      name={isEditing ? 'close' : 'edit'}
                      size={20}
                      color={isEditing ? '#EF4444' : '#3B82F6'}
                    />
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.actionButton}
                    onPress={() => approveSection(sectionKey)}
                  >
                    <MaterialIcons name="check" size={20} color="#10B981" />
                  </TouchableOpacity>
                </>
              )}
            </View>
          </View>
        </TouchableOpacity>

        {isExpanded && (
          <View style={styles.sectionContent}>
            {isEditing ? (
              <TextInput
                style={styles.editableText}
                value={sectionData.content}
                onChangeText={(text) => updateContent(sectionKey, text)}
                multiline
                textAlignVertical="top"
              />
            ) : (
              <Text style={styles.sectionText}>{sectionData.content}</Text>
            )}
          </View>
        )}
      </Card>
    );
  };

  const approvalStatus = getApprovalStatus();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#F8FAFC" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <MaterialIcons name="arrow-back" size={24} color="#374151" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>AI Report Generation</Text>
        <TouchableOpacity onPress={handleFinalizeReport}>
          <MaterialIcons name="send" size={24} color="#3B82F6" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Progress Indicator */}
        <Card style={styles.progressCard}>
          <Card.Content>
            <View style={styles.progressHeader}>
              <Text style={styles.progressTitle}>Report Progress</Text>
              <Text style={styles.progressText}>
                {approvalStatus.approved} of {approvalStatus.total} sections approved
              </Text>
            </View>
            <View style={styles.progressBar}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${approvalStatus.percentage}%` },
                ]}
              />
            </View>
            <Text style={styles.progressPercentage}>{approvalStatus.percentage}% Complete</Text>
          </Card.Content>
        </Card>

        {/* Report Sections */}
        <View style={styles.sectionsContainer}>
          {Object.entries(reportData).map(([key, data]) => renderSection(key, data))}
        </View>

        {/* Finalize Button */}
        <TouchableOpacity
          style={[
            styles.finalizeButton,
            approvalStatus.approved === approvalStatus.total && styles.finalizeButtonActive,
          ]}
          onPress={handleFinalizeReport}
        >
          <MaterialIcons name="send" size={24} color="white" />
          <Text style={styles.finalizeButtonText}>
            {approvalStatus.approved === approvalStatus.total
              ? 'Finalize Report'
              : 'Review Report'}
          </Text>
        </TouchableOpacity>
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
  progressCard: {
    marginTop: 16,
    marginBottom: 16,
  },
  progressHeader: {
    marginBottom: 12,
  },
  progressTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  progressText: {
    fontSize: 14,
    color: '#6B7280',
  },
  progressBar: {
    height: 8,
    backgroundColor: '#E5E7EB',
    borderRadius: 4,
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#10B981',
    borderRadius: 4,
  },
  progressPercentage: {
    fontSize: 14,
    fontWeight: '500',
    color: '#10B981',
    textAlign: 'center',
  },
  sectionsContainer: {
    marginBottom: 24,
  },
  sectionCard: {
    marginBottom: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#E5E7EB',
  },
  approvedCard: {
    borderLeftColor: '#10B981',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  sectionTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginLeft: 8,
    flex: 1,
  },
  sectionActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    padding: 8,
    borderRadius: 4,
    backgroundColor: '#F3F4F6',
  },
  sectionContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  sectionText: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
  },
  editableText: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    borderRadius: 6,
    padding: 12,
    backgroundColor: 'white',
    minHeight: 100,
  },
  finalizeButton: {
    backgroundColor: '#6B7280',
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
  finalizeButtonActive: {
    backgroundColor: '#10B981',
  },
  finalizeButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});

export default AIReportGeneration; 