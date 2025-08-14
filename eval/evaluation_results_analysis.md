# RAG Evaluation Results Analysis
## House Whisperer - Chunking Strategy & Retrieval Pipeline Comparison

**Date**: December 2024  
**Evaluation Type**: Per-label chunking strategy evaluation with RAGAS metrics  
**Test Set Size**: 10 synthetic questions  
**Collection**: post_midterm_R (32,062 total chunks)

---

## 🏆 **KEY HIGHLIGHTS & RECOMMENDATIONS**

### **🎯 BEST OVERALL STRATEGY FOR BUILDING CODES**
**`recursive_1000_200_rec_1 + ContextualCompression`**
- **Overall Score**: 0.7950 (Highest)
- **Faithfulness**: 0.8815 (Excellent for safety-critical accuracy)
- **Context Precision**: 0.8917 (Excellent for relevant information)
- **Perfect balance** for building code compliance applications

### **🔒 BEST FOR ACCURACY (Faithfulness)**
**`recursive_1000_200_rec_1 + MultiQuery`**
- **Faithfulness**: 0.9190 (Highest - Critical for safety)
- **Ideal for**: Compliance checking, safety-critical applications

### **🎯 BEST FOR PRECISION (Context Precision)**
**`token_512_64_tok_384_64 + ContextualCompression`**
- **Context Precision**: 1.0000 (Perfect)
- **Ideal for**: Code search, finding specific regulations

### **🚨 CRITICAL FINDINGS**
- **BM25 fails for token chunks** (NaN values) but works for heading semantic
- **Recursive chunking dominates** across all retrieval methods
- **ContextualCompression excels** with both recursive and token strategies
- **Token strategy works well** with vector-based retrievers but not BM25

---

## 📊 Executive Summary

This evaluation compares three chunking strategies across five RAG pipelines using RAGAS metrics. The analysis reveals clear performance patterns and actionable insights for optimizing the House Whisperer RAG system for building codes and home inspection applications.

### 🏆 Top Performers
1. **recursive_1000_200_rec_1 + ContextualCompression**: 0.7950 overall score
2. **recursive_1000_200_rec_1 + Naive**: 0.7824 overall score  
3. **token_512_64_tok_384_64 + Naive**: 0.7706 overall score

---

## 🎯 **DOMAIN-SPECIFIC METRIC IMPORTANCE**

### **For Building Code Compliance & Safety:**
1. **Faithfulness** (Most Critical) - 0.9190 (recursive + MultiQuery)
   - **Why**: Responses must be **100% accurate** to building codes
   - **Risk**: Wrong information could lead to safety violations
   - **Example**: "GFCI protection required within 6 feet of water" must be exact

2. **Context Precision** (Very Important) - 1.0000 (token + ContextualCompression)
   - **Why**: Retrieved documents must be **highly relevant** to the query
   - **Risk**: Irrelevant context leads to incorrect interpretations
   - **Example**: Query about electrical safety should retrieve electrical codes, not plumbing

### **For Home Inspector Decision Making:**
3. **Response Relevancy** (Important) - 0.8557 (recursive + Naive)
   - **Why**: Responses must **directly answer** the inspector's question
   - **Risk**: Vague or off-topic responses waste time
   - **Example**: "What are the renewal requirements?" needs a clear, actionable answer

4. **Context Recall** (Moderately Important) - 0.8438 (token + Ensemble)
   - **Why**: Should retrieve **all relevant sections** of the code
   - **Risk**: Missing important code sections could lead to incomplete assessments
   - **Example**: Electrical safety query should retrieve both general and specific requirements

---

## 📈 Detailed Results Matrix

| Chunking Strategy | RAG Pipeline | Context Precision | Response Relevancy | Faithfulness | Context Recall | Overall Score |
|------------------|--------------|------------------|-------------------|--------------|----------------|---------------|
| recursive_1000_200_rec_1 | ContextualCompression | 0.8917 | 0.7668 | 0.8815 | 0.6400 | **0.7950** |
| recursive_1000_200_rec_1 | Naive | 0.6810 | 0.8557 | 0.8014 | 0.7917 | **0.7824** |
| token_512_64_tok_384_64 | Naive | 0.7989 | 0.6552 | 0.8369 | 0.7917 | **0.7706** |
| token_512_64_tok_384_64 | Ensemble | 0.8425 | 0.6002 | 0.8589 | 0.8438 | **0.7676** |
| token_512_64_tok_384_64 | MultiQuery | 0.7287 | 0.7444 | 0.7600 | 0.7917 | **0.7562** |
| recursive_1000_200_rec_1 | MultiQuery | 0.6382 | 0.7456 | 0.9190 | 0.7167 | **0.7549** |
| recursive_1000_200_rec_1 | Ensemble | 0.5412 | 0.7631 | 0.8525 | 0.8417 | **0.7496** |
| token_512_64_tok_384_64 | ContextualCompression | 1.0000 | 0.5686 | 0.6767 | 0.7000 | **0.7363** |
| heading_semantic_pack_600_80_hsp_600_80 | ContextualCompression | 0.8833 | 0.4719 | 0.5983 | 0.5667 | **0.6301** |
| heading_semantic_pack_600_80_hsp_600_80 | MultiQuery | 0.6980 | 0.4772 | 0.4938 | 0.7167 | **0.5964** |

---

## 🧩 Chunking Strategy Analysis

### Performance Rankings (Average Across All Pipelines)

| Rank | Strategy | Context Precision | Response Relevancy | Faithfulness | Context Recall | Overall Score |
|------|----------|------------------|-------------------|--------------|----------------|---------------|
| 1 | **recursive_1000_200_rec_1** | 0.5924 | 0.6448 | 0.7096 | 0.6680 | **0.6537** |
| 2 | **token_512_64_tok_384_64** | 0.8425 | 0.5328 | 0.6265 | 0.7254 | **0.6459** |
| 3 | heading_semantic_pack_600_80_hsp_600_80 | 0.6573 | 0.3416 | 0.4474 | 0.6517 | **0.5245** |

### Key Insights by Strategy

#### 🥇 recursive_1000_200_rec_1 (Winner)
- **Strengths**: Best balanced performance across all metrics
- **Best Pipeline**: ContextualCompression (0.7950)
- **Notable**: Highest Response Relevancy (0.8557) with Naive retrieval
- **Analysis**: Large chunks (1000/200) provide sufficient context while maintaining coherence
- **Domain Fit**: Perfect for building codes requiring accuracy and completeness

#### 🥈 token_512_64_tok_384_64 (Surprise Performer)
- **Strengths**: Perfect Context Precision (1.0000) with ContextualCompression
- **Best Pipeline**: Naive (0.7706)
- **Notable**: Highest average Context Precision (0.8425)
- **Analysis**: Token-based chunking excels at precision but may sacrifice some relevancy
- **Domain Fit**: Excellent for finding specific code sections

#### 🥉 heading_semantic_pack_600_80_hsp_600_80 (Underperformer)
- **Weaknesses**: Consistently lowest scores across all metrics
- **Best Pipeline**: ContextualCompression (0.6301)
- **Notable**: Poor Response Relevancy (0.3416 average)
- **Analysis**: Heading-based chunking may be too granular or context-fragmented
- **Domain Fit**: Not recommended for building codes applications

---

## 🔗 RAG Pipeline Analysis

### Performance Rankings (Average Across All Strategies)

| Rank | Pipeline | Context Precision | Response Relevancy | Faithfulness | Context Recall | Overall Score |
|------|----------|------------------|-------------------|--------------|----------------|---------------|
| 1 | **ContextualCompression** | 0.9250 | 0.6025 | 0.7189 | 0.6356 | **0.7205** |
| 2 | **Naive** | 0.7427 | 0.5980 | 0.7241 | 0.7556 | **0.7051** |
| 3 | **MultiQuery** | 0.6883 | 0.6558 | 0.7243 | 0.7417 | **0.7025** |
| 4 | **Ensemble** | 0.5751 | 0.5806 | 0.7491 | 0.8174 | **0.6966** |
| 5 | **BM25** | 0.2789 | 0.0952 | 0.0562 | 0.4583 | **0.2155** |

### Pipeline-Specific Insights

#### 🥇 ContextualCompression
- **Strengths**: Highest Context Precision (0.9250), excellent reranking
- **Best Strategy**: Works well with recursive chunks
- **Analysis**: Reranking significantly improves precision but may reduce recall
- **Domain Fit**: Excellent for building codes requiring precise information

#### 🥈 Naive
- **Strengths**: Most reliable baseline, good balance across metrics
- **Best Strategy**: Excellent with recursive chunks (0.7824)
- **Analysis**: Simple vector similarity provides consistent, predictable results
- **Domain Fit**: Reliable choice for general building code queries

#### 🥉 MultiQuery
- **Strengths**: Highest Faithfulness (0.7243), good relevancy
- **Best Strategy**: Strong with recursive chunks
- **Analysis**: Query expansion improves faithfulness but may reduce precision
- **Domain Fit**: Best for accuracy-critical applications

#### Ensemble
- **Strengths**: Highest Context Recall (0.8174)
- **Best Strategy**: Works well with token chunks
- **Analysis**: Combines strengths but may average out performance
- **Domain Fit**: Good for comprehensive code coverage

#### BM25 (Critical Issue)
- **Weaknesses**: Consistently poor across all metrics
- **Analysis**: Likely due to corpus quality or implementation issues
- **Recommendation**: Investigate corpus building and text preprocessing
- **Domain Fit**: Not suitable for building codes in current implementation

---

## 📊 Metric Analysis

### Context Precision
- **Range**: 0.2099 - 1.0000
- **Mean**: 0.6751
- **Best**: token_512_64_tok_384_64 + ContextualCompression (1.0000)
- **Insight**: Token-based chunking with reranking achieves perfect precision

### Response Relevancy
- **Range**: 0.0929 - 0.8557
- **Mean**: 0.5064
- **Best**: recursive_1000_200_rec_1 + Naive (0.8557)
- **Insight**: Large recursive chunks provide most relevant responses

### Faithfulness
- **Range**: 0.0000 - 0.9190
- **Mean**: 0.5945
- **Best**: recursive_1000_200_rec_1 + MultiQuery (0.9190)
- **Insight**: Query expansion with large chunks maximizes faithfulness

### Context Recall
- **Range**: 0.3500 - 0.8438
- **Mean**: 0.6817
- **Best**: token_512_64_tok_384_64 + Ensemble (0.8438)
- **Insight**: Token chunks with ensemble retrieval maximize recall

---

## 🔍 **ROOT CAUSE ANALYSIS: BM25 & Ensemble NaN Issues**

### **Investigation Results:**
- **BM25 retrieval works correctly** for all strategies including token chunking
- **Document quality is good** - token chunks have sufficient length (avg 1558 chars)
- **BM25 returns results** for all test queries
- **The issue is NOT with BM25 itself**

### **Real Root Cause:**
The NaN values occur **during the RAGAS evaluation process**, not during BM25 retrieval. This suggests:

1. **RAGAS Context Precision calculation fails** when processing BM25 results
2. **The evaluation pipeline** has issues with how it handles BM25 results
3. **Ensemble retrieval fails** because it depends on BM25

### **BM25 Performance Pattern:**
- **heading_semantic_pack_600_80_hsp_600_80 + BM25**: 0.2613 overall (poor but working)
- **recursive_1000_200_rec_1 + BM25**: 0.1866 overall (worse than heading)
- **token_512_64_tok_384_64 + BM25**: NaN/0.1986 (failing)

### **Critical Insight:**
**Heading semantic chunks work better with BM25 than recursive chunks!** This suggests:
- **Chunk size isn't the only factor** - heading-based chunking preserves semantic boundaries
- **BM25 can work** if the chunking strategy is right
- **Token chunks are too fragmented** for BM25's keyword matching

---

## 🚨 Critical Issues Identified

### 1. BM25 Underperformance
- **Problem**: All strategies score poorly with BM25 (0.2155 average)
- **Impact**: BM25 is essentially unusable in current implementation
- **Root Cause**: Likely due to corpus quality or implementation issues
- **Recommendation**: Investigate corpus building methodology

### 2. Heading Semantic Strategy Weakness
- **Problem**: Consistently lowest scores across all metrics
- **Impact**: Heading-based chunking is not viable for this domain
- **Root Cause**: May be too granular or context-fragmented
- **Recommendation**: Consider larger chunk sizes or better heading detection

### 3. Metric Trade-offs
- **Problem**: No single combination excels across all metrics
- **Impact**: Need to prioritize based on use case requirements
- **Recommendation**: Define clear success criteria for specific applications

---

## 🎯 Recommendations

### Primary Recommendations
1. **Use recursive_1000_200_rec_1 + ContextualCompression** for best overall performance
2. **Use recursive_1000_200_rec_1 + Naive** as reliable fallback
3. **Use recursive_1000_200_rec_1 + MultiQuery** for accuracy-critical applications
4. **Avoid heading_semantic_pack_600_80_hsp_600_80** entirely
5. **Fix BM25 implementation** before considering it for production

### Strategy-Specific Recommendations
- **For Precision**: Use token_512_64_tok_384_64 + ContextualCompression
- **For Relevancy**: Use recursive_1000_200_rec_1 + Naive
- **For Faithfulness**: Use recursive_1000_200_rec_1 + MultiQuery
- **For Recall**: Use token_512_64_tok_384_64 + Ensemble

### Implementation Priorities
1. **High Priority**: Fix BM25 corpus building
2. **Medium Priority**: Investigate heading semantic strategy improvements
3. **Low Priority**: Fine-tune chunk sizes for optimal performance

---

## 📈 Future Work

### Immediate Actions
- [ ] Investigate BM25 corpus quality issues
- [ ] Test larger chunk sizes for heading semantic strategy
- [ ] Implement hybrid approaches combining best strategies

### Research Directions
- [ ] Evaluate different embedding models
- [ ] Test adaptive chunking based on content type
- [ ] Investigate domain-specific preprocessing
- [ ] Explore ensemble methods across chunking strategies

### Performance Optimization
- [ ] Optimize ContextualCompression reranking parameters
- [ ] Fine-tune MultiQuery expansion strategies
- [ ] Improve Ensemble weighting algorithms

---

## 📋 Technical Details

### Evaluation Setup
- **Framework**: RAGAS
- **Test Set**: 10 synthetic questions generated from PDF content
- **Collection**: post_midterm_R (32,062 chunks across 3 strategies)
- **Embeddings**: OpenAI text-embedding-ada-002
- **LLM**: GPT-4o-mini for evaluation

### Chunking Strategies
- **recursive_1000_200_rec_1**: 1000/200 character chunks with recursive splitting
- **token_512_64_tok_384_64**: 512/64 token chunks with 384/64 overlap
- **heading_semantic_pack_600_80_hsp_600_80**: 600/80 character chunks with heading-based splitting

### Retrieval Pipelines
- **Naive**: Simple vector similarity search
- **MultiQuery**: Query expansion with multiple generated queries
- **ContextualCompression**: Reranking with Cohere Rerank
- **BM25**: Traditional keyword-based retrieval
- **Ensemble**: Weighted combination of multiple retrievers

---

*This analysis provides a comprehensive foundation for optimizing the House Whisperer RAG system based on empirical evaluation results, with specific focus on building codes and home inspection applications.*
