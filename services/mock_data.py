"""
Mock personal data for testing agent operations.
"""

MOCK_CHATGPT_LOGS = """
# ChatGPT Conversation History - User: john.doe@example.com

## Conversation: Learning Rust Programming
Date: 2024-01-15
User: Can you explain ownership in Rust?
Assistant: Ownership is Rust's most unique feature, and it enables memory safety without a garbage collector...
User: How do I handle errors in Rust?
Assistant: Rust has a powerful error handling system using Result<T, E> and Option<T> types...

## Conversation: Recipe Ideas
Date: 2024-01-20  
User: I have chicken, rice, and vegetables. What can I make?
Assistant: Here are several delicious options: 1) Chicken stir-fry with vegetables over rice...
User: How long should I marinate the chicken?
Assistant: For best flavor, marinate for at least 30 minutes, but ideally 2-4 hours...

## Conversation: Career Advice
Date: 2024-02-01
User: I'm thinking about transitioning from backend to full-stack development
Assistant: That's a great career move! Here's what you should focus on...
User: Which frontend framework should I learn first?
Assistant: React is often recommended as a first framework because...

Total conversations: 47
Most discussed topics: Programming (18), Cooking (12), Career (8), Health (5), Travel (4)
Average conversation length: 8 messages
Most active time: Evenings (6-10 PM)
"""

MOCK_SPOTIFY_DATA = """
{
  "user_profile": {
    "id": "john_doe_music",
    "email": "john.doe@example.com",
    "country": "US",
    "product": "premium"
  },
  "listening_history": {
    "total_minutes_listened": 14280,
    "unique_artists": 89,
    "unique_tracks": 412,
    "top_genres": ["indie rock", "electronic", "jazz", "lo-fi hip hop", "classical"],
    "listening_patterns": {
      "peak_hours": ["08:00-10:00", "18:00-20:00"],
      "most_active_day": "Friday",
      "average_daily_minutes": 85
    }
  },
  "top_artists_2024": [
    {"name": "Radiohead", "play_count": 234, "total_minutes": 1120},
    {"name": "Bon Iver", "play_count": 189, "total_minutes": 890},
    {"name": "James Blake", "play_count": 156, "total_minutes": 645},
    {"name": "FKA twigs", "play_count": 143, "total_minutes": 580},
    {"name": "Miles Davis", "play_count": 132, "total_minutes": 920}
  ],
  "top_tracks_2024": [
    {"title": "Weird Fishes/Arpeggi", "artist": "Radiohead", "play_count": 47},
    {"title": "Holocene", "artist": "Bon Iver", "play_count": 41},
    {"title": "Retrograde", "artist": "James Blake", "play_count": 38},
    {"title": "Two Weeks", "artist": "FKA twigs", "play_count": 35},
    {"title": "So What", "artist": "Miles Davis", "play_count": 33}
  ],
  "playlists": [
    {"name": "Morning Focus", "tracks": 45, "followers": 0, "collaborative": false},
    {"name": "Workout Energy", "tracks": 32, "followers": 0, "collaborative": false},
    {"name": "Late Night Jazz", "tracks": 78, "followers": 2, "collaborative": true},
    {"name": "Road Trip 2024", "tracks": 124, "followers": 5, "collaborative": true}
  ],
  "discoveries": {
    "new_artists_discovered": 23,
    "through_discover_weekly": 45,
    "through_release_radar": 31,
    "saved_from_recommendations": 67
  }
}
"""

MOCK_LINKEDIN_PROFILE = """
# LinkedIn Profile Export

## Basic Information
Name: John Doe
Headline: Senior Software Engineer | Distributed Systems | ex-Google
Location: San Francisco Bay Area
Connections: 1,247
Profile Views (Last 90 days): 342

## Current Position
Title: Senior Software Engineer
Company: TechCorp Inc.
Duration: 2 years 3 months (Jan 2022 - Present)
Description: Leading the platform team responsible for building scalable microservices infrastructure. 
Key achievements:
- Reduced system latency by 40% through optimization of service mesh
- Led migration from monolith to microservices (12 services)
- Mentored 5 junior engineers
Technologies: Go, Kubernetes, gRPC, PostgreSQL, Redis, AWS

## Previous Experience

### Software Engineer II at Google
Duration: 3 years 7 months (Jun 2018 - Dec 2021)
- Worked on Google Cloud Platform team
- Contributed to Kubernetes open source project
- Developed internal tools for service reliability

### Software Engineer at StartupXYZ
Duration: 2 years (May 2016 - May 2018)
- Full-stack development using React and Node.js
- Implemented real-time collaboration features
- Grew engineering team from 3 to 12 people

## Education
Master of Science in Computer Science
Stanford University (2014-2016)
Focus: Distributed Systems and Machine Learning

Bachelor of Science in Computer Science  
UC Berkeley (2010-2014)
GPA: 3.8/4.0

## Skills
Programming Languages: Go (Expert), Python (Expert), Java (Advanced), JavaScript (Advanced), Rust (Intermediate)
Technologies: Kubernetes, Docker, AWS, GCP, PostgreSQL, MongoDB, Redis, Kafka, gRPC
Concepts: Distributed Systems, Microservices, System Design, API Design, Performance Optimization

## Endorsements
- Go: 47 endorsements
- Distributed Systems: 38 endorsements
- System Architecture: 31 endorsements
- Python: 29 endorsements
- Kubernetes: 26 endorsements

## Recent Activity
- Posted: "Thoughts on the future of edge computing..." (234 likes, 45 comments)
- Shared article: "Building Resilient Distributed Systems" (89 likes)
- Commented on: "Is Rust ready for production?" discussion
- Published article: "Lessons from scaling a platform to 1M+ requests/sec"

## Recommendations
5 recommendations received
3 recommendations given

## Interests
Following: 45 companies, 123 influencers
Topics: Cloud Computing, DevOps, System Architecture, Open Source, Tech Leadership
"""

MOCK_FITNESS_DATA = """
# Apple Health / Fitness Data Export

## Summary Statistics (Last 30 Days)
- Average Daily Steps: 8,234
- Average Active Calories: 485
- Average Sleep Duration: 7h 12m
- Average Heart Rate: 68 bpm (resting: 58 bpm)
- Workouts Completed: 18
- Stand Hours Average: 11/day

## Recent Workouts
1. Running - 5.2 km in 28:32 (Jan 23, 2024)
   - Pace: 5:29/km
   - Heart Rate Avg: 152 bpm
   - Calories: 412

2. Strength Training - 45 minutes (Jan 22, 2024)
   - Focus: Upper body
   - Calories: 285

3. Yoga - 30 minutes (Jan 21, 2024)
   - Type: Vinyasa flow
   - Calories: 95

4. Cycling - 18.3 km in 42:15 (Jan 20, 2024)
   - Speed Avg: 26 km/h
   - Heart Rate Avg: 138 bpm
   - Calories: 380

## Sleep Patterns
- Average Bedtime: 11:24 PM
- Average Wake Time: 6:48 AM
- Deep Sleep: 1h 45m average
- REM Sleep: 1h 32m average
- Sleep Quality Score: 82/100

## Health Metrics
- Blood Pressure: 118/76 (last reading)
- Weight Trend: -2.3 kg over last 3 months
- BMI: 23.4
- VO2 Max: 45.2 mL/kg/min
"""

# Dictionary mapping different data types
MOCK_DATA_SETS = {
    "chatgpt": MOCK_CHATGPT_LOGS,
    "spotify": MOCK_SPOTIFY_DATA,
    "linkedin": MOCK_LINKEDIN_PROFILE,
    "fitness": MOCK_FITNESS_DATA,
}

# Interesting goals for each agent
QWEN_GOALS = [
    "Analyze my ChatGPT conversation history and create a Python script that implements a personal knowledge base system to organize and search through my most frequently discussed topics",
    "Based on my LinkedIn profile and experience, generate a comprehensive technical blog post about scaling distributed systems, including code examples in Go",
    "Review my Spotify listening data and create a Python music recommendation engine that suggests new artists based on my listening patterns and preferences",
    "Analyze my fitness data and create a personalized workout plan generator in Python that adapts based on my performance trends",
    "Combine my ChatGPT logs and LinkedIn profile to identify skill gaps and create a learning roadmap with specific courses and projects",
]

GEMINI_GOALS = [
    "Analyze my LinkedIn profile for security and privacy concerns, identify any information that could be used for social engineering attacks, and provide recommendations",
    "Review my ChatGPT conversation history to identify patterns in my learning style and suggest optimized study techniques based on cognitive science principles",
    "Analyze my Spotify data to create a detailed psychological profile of my music taste evolution and what it reveals about my personality and mood patterns",
    "Review my fitness data to identify health trends, potential issues, and provide evidence-based recommendations for improvement",
    "Create a comprehensive personal data audit report highlighting what companies can infer about me from this data and privacy recommendations",
    "Analyze all my data to identify productivity patterns and suggest an optimized daily schedule that aligns with my energy levels and habits",
]

def get_mock_data_for_permission(permission_id: int) -> tuple[list[str], str]:
    """
    Get mock data and goal based on permission_id.
    
    Returns:
        tuple of (list of file contents, goal string)
    """
    import random
    
    # Map specific permission IDs to specific goals for predictable testing
    SPECIFIC_GOALS = {
        4001: GEMINI_GOALS[0],  # Privacy audit
        4002: GEMINI_GOALS[4],  # Comprehensive data audit  
        3001: QWEN_GOALS[0],    # Knowledge base system
        3002: QWEN_GOALS[2],    # Music recommendation engine
    }
    
    # Map permission IDs to agent types
    AGENT_MAPPING = {
        4001: "gemini",
        4002: "gemini", 
        3001: "qwen",
        3002: "qwen",
    }
    
    # Use permission_id as seed for consistent but varied results
    random.seed(permission_id)
    
    if permission_id in SPECIFIC_GOALS:
        # Use predefined goal for specific test scenarios
        goal = SPECIFIC_GOALS[permission_id]
        agent_type = AGENT_MAPPING[permission_id]
        
        # Select appropriate data sources based on goal
        if "LinkedIn" in goal and "privacy" in goal.lower():
            selected_sources = ["linkedin", "chatgpt"]
        elif "Spotify" in goal:
            selected_sources = ["spotify", "chatgpt"]
        elif "ChatGPT" in goal and "knowledge base" in goal:
            selected_sources = ["chatgpt", "linkedin"]
        elif "companies can infer" in goal.lower():
            # Comprehensive data audit - use all data sources
            selected_sources = ["linkedin", "spotify", "chatgpt", "fitness"]
        else:
            # Default to 2-3 random sources
            num_sources = random.randint(2, 3)
            selected_sources = random.sample(list(MOCK_DATA_SETS.keys()), num_sources)
        
        files = [MOCK_DATA_SETS[source] for source in selected_sources]
        
        # Don't modify the goal - let the agent discover data files in the workspace
        # The base agent will list available files in the prompt
        
        return files, goal
        
    elif permission_id == 3072:  # Qwen
        # Select 2-3 random data sources
        num_sources = random.randint(2, 3)
        selected_sources = random.sample(list(MOCK_DATA_SETS.keys()), num_sources)
        files = [MOCK_DATA_SETS[source] for source in selected_sources]
        
        # Select appropriate goal
        goal = random.choice(QWEN_GOALS)
        
        # Don't modify the goal - let the agent discover data files in the workspace
        
    elif permission_id == 4096:  # Gemini
        # Select 1-2 data sources to keep prompt manageable  
        num_sources = random.randint(1, 2)
        selected_sources = random.sample(list(MOCK_DATA_SETS.keys()), num_sources)
        files = [MOCK_DATA_SETS[source] for source in selected_sources]
        
        # Select appropriate goal
        goal = random.choice(GEMINI_GOALS)
        
    elif permission_id == 9999:  # Simple Gemini test
        files = [MOCK_DATA_SETS["chatgpt"]]  # Just ChatGPT data for testing
        goal = "Create a detailed report analyzing conversation topics, learning patterns, and interests. Generate a summary document and recommendations file."
        
    else:  # Default/other
        # Provide all data for generic operations
        files = list(MOCK_DATA_SETS.values())
        goal = "Analyze the provided personal data and generate insights about patterns, habits, and recommendations for improvement"
    
    return files, goal