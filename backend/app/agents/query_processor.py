"""
Intelligent Query Processor for DocuShield Chat
Analyzes user questions and routes them to appropriate handlers
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries the system can handle"""
    DOCUMENT_SUMMARY = "document_summary"
    RISK_ANALYSIS = "risk_analysis"
    CLAUSE_SEARCH = "clause_search"
    COMPARISON = "comparison"
    SPECIFIC_QUESTION = "specific_question"
    GENERAL_INFO = "general_info"
    HELP = "help"
    DOCUMENT_STATS = "document_stats"
    RECOMMENDATION = "recommendation"

class QueryIntent(Enum):
    """User intent behind the query"""
    FIND = "find"
    ANALYZE = "analyze"
    COMPARE = "compare"
    EXPLAIN = "explain"
    LIST = "list"
    COUNT = "count"
    SUMMARIZE = "summarize"
    RECOMMEND = "recommend"

@dataclass
class QueryAnalysis:
    """Results of query analysis"""
    query_type: QueryType
    intent: QueryIntent
    entities: List[str]
    keywords: List[str]
    confidence: float
    requires_document: bool
    suggested_agents: List[str]
    response_format: str
    context_needed: List[str]

class IntelligentQueryProcessor:
    """
    Processes and analyzes user queries to provide intelligent routing and responses
    """
    
    def __init__(self):
        # Pattern matching for different query types
        self.query_patterns = {
            QueryType.DOCUMENT_SUMMARY: [
                r'\b(summary|summarize|overview|key points|main points|brief)\b',
                r'\bwhat.*document.*about\b',
                r'\btell me about.*document\b'
            ],
            QueryType.RISK_ANALYSIS: [
                r'\b(risk|risks|risky|dangerous|problem|issue|concern|red flag)\b',
                r'\bhigh.risk\b',
                r'\bwhat.*wrong\b',
                r'\bshould.*worry\b'
            ],
            QueryType.CLAUSE_SEARCH: [
                r'\b(clause|clauses|term|terms|section|provision)\b',
                r'\bfind.*clause\b',
                r'\bwhere.*says\b',
                r'\bwhat.*14.*clause\b'
            ],
            QueryType.COMPARISON: [
                r'\b(compare|comparison|difference|similar|versus|vs)\b',
                r'\bbetter.*worse\b',
                r'\bwhich.*document\b'
            ],
            QueryType.DOCUMENT_STATS: [
                r'\b(how many|count|number|statistics|stats)\b',
                r'\bhow long\b',
                r'\bwhen.*signed\b'
            ],
            QueryType.RECOMMENDATION: [
                r'\b(recommend|suggestion|advice|should I|what to do)\b',
                r'\bshould.*sign\b',
                r'\bis it safe\b'
            ],
            QueryType.HELP: [
                r'\b(help|how to|tutorial|guide)\b',
                r'\bwhat can you do\b',
                r'\bwhat.*possible\b'
            ]
        }
        
        # Intent patterns
        self.intent_patterns = {
            QueryIntent.FIND: [r'\b(find|search|locate|where|show me)\b'],
            QueryIntent.ANALYZE: [r'\b(analyze|analysis|examine|review|assess)\b'],
            QueryIntent.COMPARE: [r'\b(compare|contrast|difference)\b'],
            QueryIntent.EXPLAIN: [r'\b(explain|why|how|what does|what is)\b'],
            QueryIntent.LIST: [r'\b(list|show all|give me all|what are)\b'],
            QueryIntent.COUNT: [r'\b(how many|count|number of)\b'],
            QueryIntent.SUMMARIZE: [r'\b(summarize|summary|overview|brief)\b'],
            QueryIntent.RECOMMEND: [r'\b(recommend|suggest|advice|should)\b']
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'numbers': r'\b\d+\b',
            'document_types': r'\b(contract|agreement|policy|invoice|document)\b',
            'risk_levels': r'\b(high|medium|low|critical)[-\s]?(risk|priority)\b',
            'clause_types': r'\b(liability|termination|payment|confidentiality|indemnification)\b',
            'legal_terms': r'\b(breach|damages|penalty|jurisdiction|governing law)\b'
        }
        
    async def analyze_query(
        self, 
        query: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> QueryAnalysis:
        """
        Analyze a user query and determine how to best respond
        """
        query_lower = query.lower().strip()
        
        # Determine query type
        query_type = self._classify_query_type(query_lower)
        
        # Determine user intent
        intent = self._determine_intent(query_lower)
        
        # Extract entities and keywords
        entities = self._extract_entities(query_lower)
        keywords = self._extract_keywords(query_lower)
        
        # Calculate confidence
        confidence = self._calculate_confidence(query_lower, query_type, intent)
        
        # Determine if document is required
        requires_document = self._requires_document_context(query_type, query_lower)
        
        # Suggest appropriate agents
        suggested_agents = self._suggest_agents(query_type, intent, entities)
        
        # Determine response format
        response_format = self._determine_response_format(query_type, intent)
        
        # Determine context needed
        context_needed = self._determine_context_needed(query_type, entities, user_context)
        
        return QueryAnalysis(
            query_type=query_type,
            intent=intent,
            entities=entities,
            keywords=keywords,
            confidence=confidence,
            requires_document=requires_document,
            suggested_agents=suggested_agents,
            response_format=response_format,
            context_needed=context_needed
        )
    
    def _classify_query_type(self, query: str) -> QueryType:
        """Classify the type of query"""
        scores = {}
        
        for query_type, patterns in self.query_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query, re.IGNORECASE))
                score += matches
            scores[query_type] = score
        
        # Find the highest scoring type
        if scores and max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # Default classification based on common words
        if any(word in query for word in ['what', 'how', 'why', 'when', 'where']):
            return QueryType.SPECIFIC_QUESTION
        else:
            return QueryType.GENERAL_INFO
    
    def _determine_intent(self, query: str) -> QueryIntent:
        """Determine user intent"""
        scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query, re.IGNORECASE))
                score += matches
            scores[intent] = score
        
        if scores and max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        # Default intent based on question words
        if query.startswith(('what', 'which')):
            return QueryIntent.EXPLAIN
        elif query.startswith(('how many', 'count')):
            return QueryIntent.COUNT
        elif query.startswith('find'):
            return QueryIntent.FIND
        else:
            return QueryIntent.EXPLAIN
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract relevant entities from the query"""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append(f"{entity_type}:{match}")
        
        return entities
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords"""
        # Remove common stop words
        stop_words = {'the', 'is', 'are', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def _calculate_confidence(self, query: str, query_type: QueryType, intent: QueryIntent) -> float:
        """Calculate confidence in the analysis"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on pattern matches
        if query_type in self.query_patterns:
            pattern_matches = sum(
                len(re.findall(pattern, query, re.IGNORECASE))
                for pattern in self.query_patterns[query_type]
            )
            confidence += min(pattern_matches * 0.2, 0.4)
        
        # Increase confidence for clear intents
        if intent in self.intent_patterns:
            intent_matches = sum(
                len(re.findall(pattern, query, re.IGNORECASE))
                for pattern in self.intent_patterns[intent]
            )
            confidence += min(intent_matches * 0.1, 0.2)
        
        return min(confidence, 1.0)
    
    def _requires_document_context(self, query_type: QueryType, query: str) -> bool:
        """Determine if the query requires document context"""
        document_required_types = {
            QueryType.DOCUMENT_SUMMARY,
            QueryType.RISK_ANALYSIS,
            QueryType.CLAUSE_SEARCH,
            QueryType.DOCUMENT_STATS,
            QueryType.RECOMMENDATION
        }
        
        if query_type in document_required_types:
            return True
        
        # Check for document-specific language
        document_indicators = ['this document', 'my contract', 'the agreement', 'this file']
        return any(indicator in query for indicator in document_indicators)
    
    def _suggest_agents(self, query_type: QueryType, intent: QueryIntent, entities: List[str]) -> List[str]:
        """Suggest which agents should handle this query"""
        agent_suggestions = {
            QueryType.DOCUMENT_SUMMARY: ['simple_analyzer', 'search'],
            QueryType.RISK_ANALYSIS: ['clause_analyzer', 'search'],
            QueryType.CLAUSE_SEARCH: ['search', 'clause_analyzer'],
            QueryType.COMPARISON: ['clause_analyzer', 'search'],
            QueryType.SPECIFIC_QUESTION: ['search', 'simple_analyzer'],
            QueryType.DOCUMENT_STATS: ['simple_analyzer'],
            QueryType.RECOMMENDATION: ['clause_analyzer', 'simple_analyzer']
        }
        
        return agent_suggestions.get(query_type, ['search', 'simple_analyzer'])
    
    def _determine_response_format(self, query_type: QueryType, intent: QueryIntent) -> str:
        """Determine the best format for the response"""
        if intent == QueryIntent.LIST:
            return "numbered_list"
        elif intent == QueryIntent.COUNT:
            return "count_with_details"
        elif query_type == QueryType.DOCUMENT_SUMMARY:
            return "structured_summary"
        elif query_type == QueryType.RISK_ANALYSIS:
            return "risk_assessment"
        else:
            return "conversational"
    
    def _determine_context_needed(
        self, 
        query_type: QueryType, 
        entities: List[str], 
        user_context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Determine what context information is needed"""
        context = []
        
        if query_type in [QueryType.DOCUMENT_SUMMARY, QueryType.RISK_ANALYSIS, QueryType.CLAUSE_SEARCH]:
            context.append("document_content")
            context.append("document_metadata")
        
        if any("risk" in entity for entity in entities):
            context.append("risk_scores")
            context.append("findings")
        
        if query_type == QueryType.COMPARISON:
            context.append("multiple_documents")
        
        return context

# Global instance
query_processor = IntelligentQueryProcessor()
