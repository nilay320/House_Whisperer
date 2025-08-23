#!/bin/bash

# Quick comparison script for report versions
# Usage: ./quick_compare.sh <inspection_id>

INSPECTION_ID=${1:-"test-inspection-id"}
API_URL=${API_URL:-"http://localhost:8000"}

echo "================================================"
echo "🔍 Quick Report Version Comparison"
echo "Inspection ID: $INSPECTION_ID"
echo "API URL: $API_URL"
echo "================================================"

# Create temp directory for outputs
TEMP_DIR="comparison_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$TEMP_DIR"

echo ""
echo "🔵 Generating ORIGINAL report..."
curl -s -X POST "$API_URL/api/generate_report" \
  -H "Content-Type: application/json" \
  -d "{\"inspectionId\": \"$INSPECTION_ID\", \"enhanced\": false}" \
  > "$TEMP_DIR/original.json"

# Extract markdown
jq -r '.report.markdown' "$TEMP_DIR/original.json" > "$TEMP_DIR/original.md"

echo "✅ Original report saved to $TEMP_DIR/original.md"

echo ""
echo "🟢 Generating ENHANCED report..."
curl -s -X POST "$API_URL/api/generate_report" \
  -H "Content-Type: application/json" \
  -d "{\"inspectionId\": \"$INSPECTION_ID\", \"enhanced\": true}" \
  > "$TEMP_DIR/enhanced.json"

# Extract markdown
jq -r '.report.markdown' "$TEMP_DIR/enhanced.json" > "$TEMP_DIR/enhanced.md"

echo "✅ Enhanced report saved to $TEMP_DIR/enhanced.md"

echo ""
echo "================================================"
echo "📊 QUICK METRICS"
echo "================================================"

# Compare file sizes
ORIGINAL_SIZE=$(wc -c < "$TEMP_DIR/original.md")
ENHANCED_SIZE=$(wc -c < "$TEMP_DIR/enhanced.md")
SIZE_DIFF=$((ENHANCED_SIZE - ORIGINAL_SIZE))
SIZE_PCT=$((SIZE_DIFF * 100 / ORIGINAL_SIZE))

echo "📝 Content Size:"
echo "  Original: $ORIGINAL_SIZE bytes"
echo "  Enhanced: $ENHANCED_SIZE bytes"
echo "  Difference: +$SIZE_DIFF bytes (+$SIZE_PCT%)"

# Check for key features
echo ""
echo "✨ Enhanced Features:"

if grep -q "Executive Summary" "$TEMP_DIR/enhanced.md"; then
    echo "  ✅ Executive Summary"
else
    echo "  ❌ Executive Summary"
fi

if grep -q "Report Quality Metrics" "$TEMP_DIR/enhanced.md"; then
    echo "  ✅ Quality Metrics Dashboard"
else
    echo "  ❌ Quality Metrics Dashboard"
fi

if grep -q "Table of Contents" "$TEMP_DIR/enhanced.md"; then
    echo "  ✅ Table of Contents"
else
    echo "  ❌ Table of Contents"
fi

if grep -q "🔴\|🟠\|🟡" "$TEMP_DIR/enhanced.md"; then
    echo "  ✅ Severity Badges"
else
    echo "  ❌ Severity Badges"
fi

if grep -q "Verified Narrative" "$TEMP_DIR/enhanced.md"; then
    echo "  ✅ Narrative Source Tracking"
else
    echo "  ❌ Narrative Source Tracking"
fi

# Extract quality score if available
QUALITY_SCORE=$(jq -r '.report.reportQualityScore // "N/A"' "$TEMP_DIR/enhanced.json")
if [ "$QUALITY_SCORE" != "N/A" ]; then
    echo ""
    echo "🏆 Report Quality Score: $QUALITY_SCORE"
fi

# Count sections
ORIGINAL_SECTIONS=$(jq -r '.report.sectionCount // 0' "$TEMP_DIR/original.json")
ENHANCED_SECTIONS=$(jq -r '.report.sectionCount // 0' "$TEMP_DIR/enhanced.json")

echo ""
echo "📑 Sections:"
echo "  Original: $ORIGINAL_SECTIONS sections"
echo "  Enhanced: $ENHANCED_SECTIONS sections"

# Check narrative sources
echo ""
echo "📚 Narrative Sources (Enhanced):"
jq -r '.report.narrativeSources // {} | to_entries[] | "  \(.key): \(.value)"' "$TEMP_DIR/enhanced.json" 2>/dev/null || echo "  Not available"

echo ""
echo "================================================"
echo "📁 Output Files:"
echo "  Original: $TEMP_DIR/original.md"
echo "  Enhanced: $TEMP_DIR/enhanced.md"
echo "  Diff: $TEMP_DIR/diff.txt"
echo "================================================"

# Create a diff file
diff -u "$TEMP_DIR/original.md" "$TEMP_DIR/enhanced.md" > "$TEMP_DIR/diff.txt" 2>&1

echo ""
echo "💡 TIP: Open both markdown files side-by-side to see the improvements:"
echo "  code -d $TEMP_DIR/original.md $TEMP_DIR/enhanced.md"
echo ""
echo "Or view the diff:"
echo "  less $TEMP_DIR/diff.txt"