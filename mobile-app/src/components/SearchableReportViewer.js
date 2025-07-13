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
  FlatList,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { Card, Title, Paragraph } from 'react-native-paper';

const SearchableReportViewer = ({ navigation }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedSection, setSelectedSection] = useState(null);
  const [expandedResults, setExpandedResults] = useState(new Set());

  // Mock report data
  const reportData = {
    summary: {
      title: 'Executive Summary',
      content: 'This property shows signs of deferred maintenance with several areas requiring attention. The roof has minor damage, plumbing fixtures need updates, and the HVAC system is approaching end-of-life. Overall, the property is structurally sound but would benefit from updates and repairs.',
    },
    roof: {
      title: 'Roof & Exterior',
      content: 'The roof shows signs of aging with some missing shingles and minor water damage. Gutters are clogged and need cleaning. Exterior siding is in good condition with minor paint touch-ups needed. Chimney appears sound with no visible cracks.',
    },
    plumbing: {
      title: 'Plumbing System',
      content: 'Main water line is functional but shows signs of corrosion. Hot water heater is 12 years old and should be replaced within 2-3 years. Bathroom fixtures are dated but functional. Kitchen sink has minor leak that should be addressed.',
    },
    electrical: {
      title: 'Electrical System',
      content: 'Electrical panel is up to code with adequate capacity. Outlets are properly grounded. Some light fixtures need bulb replacements. No major electrical issues identified. Smoke detectors are present and functional.',
    },
    hvac: {
      title: 'HVAC System',
      content: 'Central air conditioning unit is 15 years old and showing signs of wear. Furnace is functional but inefficient. Ductwork appears to be in good condition. Thermostat is programmable and working properly. Recommend HVAC replacement within 2 years.',
    },
    foundation: {
      title: 'Foundation & Structure',
      content: 'Foundation appears solid with no visible cracks or settling issues. Basement shows minor moisture but no structural concerns. Floor joists are sound. No evidence of termite damage or other structural issues.',
    },
    interior: {
      title: 'Interior & Finishes',
      content: 'Interior walls and ceilings are in good condition with minor paint touch-ups needed. Flooring is worn but functional. Windows are double-paned and in good condition. Interior doors are functional with some needing adjustment.',
    },
  };

  const searchInReport = (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    const results = [];
    const searchTerm = query.toLowerCase();

    Object.entries(reportData).forEach(([sectionKey, section]) => {
      const content = section.content.toLowerCase();
      const title = section.title.toLowerCase();
      
      if (content.includes(searchTerm) || title.includes(searchTerm)) {
        const matches = [];
        
        // Find all occurrences in content
        let index = content.indexOf(searchTerm);
        while (index !== -1) {
          const start = Math.max(0, index - 50);
          const end = Math.min(content.length, index + searchTerm.length + 50);
          const context = content.substring(start, end);
          
          matches.push({
            type: 'content',
            context: context,
            position: index,
            highlightStart: index - start,
            highlightEnd: index - start + searchTerm.length,
          });
          
          index = content.indexOf(searchTerm, index + 1);
        }

        // Find matches in title
        if (title.includes(searchTerm)) {
          matches.push({
            type: 'title',
            context: title,
            position: title.indexOf(searchTerm),
            highlightStart: title.indexOf(searchTerm),
            highlightEnd: title.indexOf(searchTerm) + searchTerm.length,
          });
        }

        if (matches.length > 0) {
          results.push({
            sectionKey,
            sectionTitle: section.title,
            matches,
          });
        }
      }
    });

    setSearchResults(results);
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
    searchInReport(query);
  };

  const toggleExpandedResult = (resultId) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(resultId)) {
      newExpanded.delete(resultId);
    } else {
      newExpanded.add(resultId);
    }
    setExpandedResults(newExpanded);
  };

  const highlightText = (text, highlightStart, highlightEnd) => {
    if (highlightStart === -1 || highlightEnd === -1) {
      return <Text style={styles.contextText}>{text}</Text>;
    }

    const before = text.substring(0, highlightStart);
    const highlighted = text.substring(highlightStart, highlightEnd);
    const after = text.substring(highlightEnd);

    return (
      <Text style={styles.contextText}>
        <Text>{before}</Text>
        <Text style={styles.highlightedText}>{highlighted}</Text>
        <Text>{after}</Text>
      </Text>
    );
  };

  const renderSearchResult = ({ item }) => {
    const resultId = `${item.sectionKey}-${item.matches.length}`;
    const isExpanded = expandedResults.has(resultId);

    return (
      <Card style={styles.resultCard}>
        <TouchableOpacity onPress={() => toggleExpandedResult(resultId)}>
          <View style={styles.resultHeader}>
            <View style={styles.resultTitleContainer}>
              <MaterialIcons name="search" size={16} color="#6B7280" />
              <Text style={styles.resultTitle}>{item.sectionTitle}</Text>
              <Text style={styles.matchCount}>{item.matches.length} match{item.matches.length !== 1 ? 'es' : ''}</Text>
            </View>
            <MaterialIcons
              name={isExpanded ? 'expand-less' : 'expand-more'}
              size={20}
              color="#6B7280"
            />
          </View>
        </TouchableOpacity>

        {isExpanded && (
          <View style={styles.resultContent}>
            {item.matches.map((match, index) => (
              <View key={index} style={styles.matchItem}>
                <View style={styles.matchHeader}>
                  <MaterialIcons
                    name={match.type === 'title' ? 'title' : 'description'}
                    size={14}
                    color="#6B7280"
                  />
                  <Text style={styles.matchType}>
                    {match.type === 'title' ? 'Title' : 'Content'}
                  </Text>
                </View>
                <View style={styles.contextContainer}>
                  {highlightText(
                    match.context,
                    match.highlightStart,
                    match.highlightEnd
                  )}
                </View>
              </View>
            ))}
          </View>
        )}
      </Card>
    );
  };

  const renderSection = (sectionKey, sectionData) => {
    const isSelected = selectedSection === sectionKey;

    return (
      <TouchableOpacity
        key={sectionKey}
        style={[styles.sectionCard, isSelected && styles.selectedSection]}
        onPress={() => setSelectedSection(isSelected ? null : sectionKey)}
      >
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{sectionData.title}</Text>
          <MaterialIcons
            name={isSelected ? 'expand-less' : 'expand-more'}
            size={20}
            color="#6B7280"
          />
        </View>
        {isSelected && (
          <Text style={styles.sectionContent}>{sectionData.content}</Text>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#F8FAFC" />
      
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <MaterialIcons name="arrow-back" size={24} color="#374151" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Report Viewer</Text>
        <TouchableOpacity>
          <MaterialIcons name="share" size={24} color="#3B82F6" />
        </TouchableOpacity>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={styles.searchBar}>
          <MaterialIcons name="search" size={20} color="#6B7280" />
          <TextInput
            style={styles.searchInput}
            placeholder="Search the report..."
            value={searchQuery}
            onChangeText={handleSearch}
            placeholderTextColor="#9CA3AF"
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => handleSearch('')}>
              <MaterialIcons name="close" size={20} color="#6B7280" />
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Content */}
      <View style={styles.content}>
        {searchQuery.length > 0 ? (
          // Search Results
          <View style={styles.resultsContainer}>
            <View style={styles.resultsHeader}>
              <Text style={styles.resultsTitle}>Search Results</Text>
              <Text style={styles.resultsCount}>
                {searchResults.length} section{searchResults.length !== 1 ? 's' : ''} found
              </Text>
            </View>
            <FlatList
              data={searchResults}
              renderItem={renderSearchResult}
              keyExtractor={(item) => `${item.sectionKey}-${item.matches.length}`}
              showsVerticalScrollIndicator={false}
              contentContainerStyle={styles.resultsList}
            />
          </View>
        ) : (
          // Full Report View
          <ScrollView showsVerticalScrollIndicator={false}>
            <View style={styles.reportContainer}>
              <Text style={styles.reportTitle}>Home Inspection Report</Text>
              <Text style={styles.reportSubtitle}>
                Tap on any section to expand and read the full content
              </Text>
              {Object.entries(reportData).map(([key, data]) => renderSection(key, data))}
            </View>
          </ScrollView>
        )}
      </View>
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
  searchContainer: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  searchInput: {
    flex: 1,
    marginLeft: 12,
    fontSize: 16,
    color: '#111827',
  },
  content: {
    flex: 1,
  },
  resultsContainer: {
    flex: 1,
  },
  resultsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  resultsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  resultsCount: {
    fontSize: 14,
    color: '#6B7280',
  },
  resultsList: {
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  resultCard: {
    marginBottom: 12,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  resultTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginLeft: 8,
    flex: 1,
  },
  matchCount: {
    fontSize: 12,
    color: '#6B7280',
    marginLeft: 8,
  },
  resultContent: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  matchItem: {
    marginBottom: 12,
  },
  matchHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  matchType: {
    fontSize: 12,
    color: '#6B7280',
    marginLeft: 4,
  },
  contextContainer: {
    backgroundColor: '#F9FAFB',
    borderRadius: 6,
    padding: 8,
  },
  contextText: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
  },
  highlightedText: {
    backgroundColor: '#FEF3C7',
    fontWeight: '600',
  },
  reportContainer: {
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  reportTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#111827',
    marginBottom: 8,
  },
  reportSubtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 24,
  },
  sectionCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  selectedSection: {
    borderLeftWidth: 4,
    borderLeftColor: '#3B82F6',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    flex: 1,
  },
  sectionContent: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
});

export default SearchableReportViewer; 