"""
Response Verifier for PostMortemIQ
Detects hallucinations by checking entities against subgraph
"""

import re
from typing import Dict, List, Set, Any


class ResponseVerifier:
    """Verifies LLM responses against graph subgraph to detect hallucinations"""
    
    @staticmethod
    def extract_entities(response_text: str) -> Set[str]:
        """
        Extract entity names from LLM response
        
        Args:
            response_text: The LLM's response text
            
        Returns:
            Set of entity names mentioned
        """
        entities = set()
        
        # Extract service names (pattern: word-svc or word_svc)
        services = re.findall(r'\b[\w]+-svc\b|\b[\w]+_svc\b', response_text, re.IGNORECASE)
        entities.update(services)
        
        # Extract config keys (pattern: UPPERCASE_WITH_UNDERSCORES, min 4 chars with at least one underscore)
        config_keys = re.findall(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b', response_text)
        entities.update(config_keys)
        
        # Extract team names (common patterns)
        teams = re.findall(r'\b(?:Payments|API|Auth|Platform|Data)\s+[Tt]eam\b', response_text)
        entities.update([t.strip() for t in teams])
        
        # Extract deployment versions (pattern: v1.2.3)
        versions = re.findall(r'\bv\d+\.\d+\.\d+\b', response_text)
        entities.update(versions)
        
        return entities
    
    @staticmethod
    def get_valid_entities(subgraph: Dict[str, Any]) -> Set[str]:
        """
        Extract all valid entity names from the subgraph
        
        Args:
            subgraph: The graph subgraph from TigerGraph
            
        Returns:
            Set of valid entity names
        """
        valid_entities = set()
        
        for node in subgraph.get("nodes", []):
            # Add node ID
            if "id" in node:
                valid_entities.add(node["id"])
            
            # Add node name
            if "name" in node:
                valid_entities.add(node["name"])
            
            # Add config key
            if "key" in node:
                valid_entities.add(node["key"])
            
            # Add version
            if "version" in node:
                valid_entities.add(node["version"])
        
        # Add team names from unpaged_teams
        for team in subgraph.get("unpaged_teams", []):
            if "name" in team:
                valid_entities.add(team["name"])
        
        return valid_entities
    
    @staticmethod
    def detect_hallucinations(response_text: str, subgraph: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect hallucinated entities in LLM response
        
        Args:
            response_text: The LLM's response
            subgraph: The graph subgraph used for context
            
        Returns:
            Hallucination report with count, rate, and entities
        """
        mentioned_entities = ResponseVerifier.extract_entities(response_text)
        valid_entities = ResponseVerifier.get_valid_entities(subgraph)
        
        # Find entities mentioned but not in subgraph
        hallucinated = mentioned_entities - valid_entities
        
        # Calculate hallucination rate
        total_mentioned = len(mentioned_entities)
        hallucination_count = len(hallucinated)
        hallucination_rate = hallucination_count / total_mentioned if total_mentioned > 0 else 0.0
        
        return {
            "hallucination_count": hallucination_count,
            "hallucination_rate": hallucination_rate,
            "hallucinated_entities": list(hallucinated),
            "total_entities_mentioned": total_mentioned,
            "valid_entities_mentioned": total_mentioned - hallucination_count
        }


if __name__ == "__main__":
    # Test hallucination detection
    verifier = ResponseVerifier()
    
    subgraph = {
        "nodes": [
            {"id": "svc_1", "name": "auth-svc"},
            {"id": "config_3", "key": "JWT_EXPIRY_SECONDS", "old_value": "3600", "new_value": "60"}
        ],
        "unpaged_teams": [
            {"name": "Payments"}
        ]
    }
    
    # Response with hallucination
    response_with_hallucination = """
    The root cause is JWT_EXPIRY_SECONDS change in auth-svc.
    This also affected billing-svc and the Database team should be paged.
    """
    
    report = verifier.detect_hallucinations(response_with_hallucination, subgraph)
    print(f"Hallucination report:")
    print(f"  Count: {report['hallucination_count']}")
    print(f"  Rate: {report['hallucination_rate']:.2%}")
    print(f"  Hallucinated entities: {report['hallucinated_entities']}")
