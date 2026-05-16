"""
Dataset Token Verification Script
Verifies that the dataset meets the 2M+ token requirement for the hackathon
"""

import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("ERROR: tiktoken not installed. Run: pip install tiktoken")
    sys.exit(1)


def extract_narrative_text(incident: dict) -> str:
    """
    Extract only narrative text fields from incident
    Excludes JSON keys, metadata, and structural elements
    """
    narrative_fields = []
    
    # Description
    if 'description' in incident and incident['description']:
        narrative_fields.append(incident['description'])
    
    # Timeline
    if 'timeline' in incident and incident['timeline']:
        narrative_fields.append(incident['timeline'])
    
    # Root cause
    if 'root_cause' in incident and incident['root_cause']:
        narrative_fields.append(incident['root_cause'])
    
    # Resolution
    if 'resolution' in incident and incident['resolution']:
        narrative_fields.append(incident['resolution'])
    
    # Logs (if it's a string, not a list)
    if 'logs' in incident:
        if isinstance(incident['logs'], str):
            narrative_fields.append(incident['logs'])
        elif isinstance(incident['logs'], list):
            # Join log entries
            narrative_fields.extend([str(log) for log in incident['logs'] if log])
    
    # Alert name and severity (short but narrative)
    if 'alert_name' in incident and incident['alert_name']:
        narrative_fields.append(incident['alert_name'])
    
    # Team owner
    if 'team_owner' in incident and incident['team_owner']:
        narrative_fields.append(incident['team_owner'])
    
    return ' '.join(narrative_fields)


def verify_dataset_tokens(dataset_path: str = "data/synthetic_incidents.json"):
    """
    Verify dataset token count
    
    Args:
        dataset_path: Path to the incidents JSON file
        
    Returns:
        dict with verification results
    """
    print(f"Verifying dataset: {dataset_path}")
    print("=" * 60)
    
    # Check if file exists
    if not os.path.exists(dataset_path):
        print(f"ERROR: Dataset file not found: {dataset_path}")
        return {
            'success': False,
            'error': 'File not found'
        }
    
    # Load dataset
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load dataset: {e}")
        return {
            'success': False,
            'error': str(e)
        }
    
    incidents = data.get('incidents', [])
    
    if not incidents:
        print("ERROR: No incidents found in dataset")
        return {
            'success': False,
            'error': 'No incidents found'
        }
    
    print(f"Found {len(incidents)} incidents in dataset")
    print()
    
    # Initialize tiktoken encoder
    enc = tiktoken.get_encoding("cl100k_base")
    
    # Count tokens for each incident
    total_tokens = 0
    incident_tokens = []
    
    for i, incident in enumerate(incidents, 1):
        narrative_text = extract_narrative_text(incident)
        tokens = len(enc.encode(narrative_text))
        total_tokens += tokens
        incident_tokens.append({
            'incident_id': incident.get('incident_id', f'incident_{i}'),
            'tokens': tokens
        })
    
    # Calculate statistics
    avg_tokens_per_incident = total_tokens / len(incidents) if incidents else 0
    min_tokens = min(inc['tokens'] for inc in incident_tokens) if incident_tokens else 0
    max_tokens = max(inc['tokens'] for inc in incident_tokens) if incident_tokens else 0
    
    # Check if meets 2M requirement
    meets_requirement = total_tokens >= 2_000_000
    
    # Print results
    print("RESULTS:")
    print("-" * 60)
    print(f"Total incidents:           {len(incidents):,}")
    print(f"Total narrative tokens:    {total_tokens:,}")
    print(f"Average tokens/incident:   {avg_tokens_per_incident:,.1f}")
    print(f"Min tokens/incident:       {min_tokens:,}")
    print(f"Max tokens/incident:       {max_tokens:,}")
    print()
    
    if meets_requirement:
        print(f"✅ MEETS REQUIREMENT: {total_tokens:,} tokens >= 2,000,000 tokens")
        print(f"   Surplus: {total_tokens - 2_000_000:,} tokens")
    else:
        shortage = 2_000_000 - total_tokens
        print(f"❌ DOES NOT MEET REQUIREMENT: {total_tokens:,} tokens < 2,000,000 tokens")
        print(f"   Shortage: {shortage:,} tokens")
        print()
        
        # Calculate how many more incidents needed
        if avg_tokens_per_incident > 0:
            additional_incidents_needed = int(shortage / avg_tokens_per_incident) + 1
            print(f"📊 RECOMMENDATION:")
            print(f"   Need approximately {additional_incidents_needed:,} more incidents")
            print(f"   (at {avg_tokens_per_incident:,.1f} tokens/incident average)")
            print()
            print(f"   Run: python data/generate_incidents.py --count {len(incidents) + additional_incidents_needed}")
    
    print("=" * 60)
    
    # Show sample of incidents with token counts
    print()
    print("SAMPLE (first 5 incidents):")
    print("-" * 60)
    for inc in incident_tokens[:5]:
        print(f"  {inc['incident_id']}: {inc['tokens']:,} tokens")
    
    if len(incident_tokens) > 5:
        print(f"  ... and {len(incident_tokens) - 5} more incidents")
    
    return {
        'success': True,
        'total_incidents': len(incidents),
        'total_tokens': total_tokens,
        'avg_tokens_per_incident': avg_tokens_per_incident,
        'min_tokens': min_tokens,
        'max_tokens': max_tokens,
        'meets_requirement': meets_requirement,
        'shortage': max(0, 2_000_000 - total_tokens),
        'incident_tokens': incident_tokens
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify dataset token count")
    parser.add_argument(
        '--dataset',
        default='data/synthetic_incidents.json',
        help='Path to incidents JSON file'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    result = verify_dataset_tokens(args.dataset)
    
    if args.json:
        print()
        print(json.dumps(result, indent=2))
    
    # Exit with error code if requirement not met
    if not result.get('meets_requirement', False):
        sys.exit(1)
