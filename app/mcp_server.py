import sys
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Student Success Navigator MCP Server")

# 1. Scholarship database and tool
MOCK_SCHOLARSHIPS = [
    {
        "title": "National Merit Scholarship (India)",
        "eligibility": "Undergraduate students, CGPA > 8.0, annual income < 8 LPA",
        "benefits": "INR 50,000 per year + tuition waiver",
        "deadline": "2026-10-15"
    },
    {
        "title": "Microsoft Tuition Scholarship",
        "eligibility": "B.Tech/BS Computer Science, CGPA > 9.0, passionate about software engineering",
        "benefits": "Full tuition coverage + Microsoft mentorship + internship opportunities",
        "deadline": "2026-11-01"
    },
    {
        "title": "Google Generation Scholarship",
        "eligibility": "Women in Computer Science/Engineering, CGPA > 8.0",
        "benefits": "$1,000 USD funding + community access",
        "deadline": "2026-09-30"
    },
    {
        "title": "Reliance Foundation Undergraduate Scholarship",
        "eligibility": "Undergraduate students in any branch, annual income < 15 LPA, merit-cum-means",
        "benefits": "Up to INR 2 Lakhs over the course of the degree",
        "deadline": "2026-10-31"
    }
]

@mcp.tool()
def search_scholarships(query: str) -> str:
    """Searches for scholarships matching the query keywords.
    
    Args:
        query: Search term (e.g. 'computer science', 'women', 'merit', 'india')
    """
    query_lower = query.lower()
    matches = []
    for s in MOCK_SCHOLARSHIPS:
        if (query_lower in s["title"].lower() or 
            query_lower in s["eligibility"].lower()):
            matches.append(s)
            
    if not matches:
        return f"No direct scholarships found for query: '{query}'. Try searching for general or merit-based opportunities."
    
    return f"Scholarship search results for '{query}':\n" + "\n\n".join(
        [f"- **{s['title']}**\n  - Eligibility: {s['eligibility']}\n  - Benefits: {s['benefits']}\n  - Deadline: {s['deadline']}" for s in matches]
    )


# 2. Internship database and tool
MOCK_INTERNSHIPS = [
    {
        "title": "Google STEP Internship (Software Product Engineering)",
        "role": "Software Engineering Intern",
        "requirements": "Second-year B.Tech / BS in Computer Science",
        "skills": ["python", "java", "c++", "data structures"],
        "deadline": "2026-08-31"
    },
    {
        "title": "Microsoft Intern Program",
        "role": "Software Engineer Intern",
        "requirements": "Undergraduate / Postgraduate student in CS/IT",
        "skills": ["c#", "dotnet", "cloud", "javascript"],
        "deadline": "2026-09-15"
    },
    {
        "title": "Amazon Software Dev Intern",
        "role": "SDE Intern",
        "requirements": "Pre-final year BS/MS/B.Tech",
        "skills": ["java", "c++", "problem solving", "algorithms"],
        "deadline": "2026-10-01"
    },
    {
        "title": "AstraZeneca AI Research Internship",
        "role": "AI / ML Research Intern",
        "requirements": "Knowledge of Deep Learning, PyTorch, Python",
        "skills": ["python", "pytorch", "machine learning", "tensorflow"],
        "deadline": "2026-11-15"
    }
]

@mcp.tool()
def search_internships(skills_query: str) -> str:
    """Searches for internship opportunities matching a list or string of skills.
    
    Args:
        skills_query: A skill keyword or comma-separated list of skills (e.g. 'python', 'java', 'cloud')
    """
    skills_list = [s.strip().lower() for s in skills_query.replace(",", " ").split()]
    matches = []
    for intern in MOCK_INTERNSHIPS:
        if any(sk in intern["skills"] for sk in skills_list):
            matches.append(intern)
            
    if not matches:
        return f"No internship matches found for skills: '{skills_query}'. Try searching for generic keywords like 'python' or 'javascript'."
        
    return f"Internship recommendations matching '{skills_query}':\n" + "\n\n".join(
        [f"- **{i['title']}**\n  - Role: {i['role']}\n  - Requirements: {i['requirements']}\n  - Required Skills: {', '.join(i['skills'])}\n  - Deadline: {i['deadline']}" for i in matches]
    )


# 3. Certifications and Courses database and tool
MOCK_COURSES = [
    {
        "title": "Google Data Analytics Professional Certificate",
        "domain": "data science",
        "platform": "Coursera",
        "estimated_duration": "6 months (10 hours/week)"
    },
    {
        "title": "AWS Certified Solutions Architect - Associate",
        "domain": "cloud computing",
        "platform": "AWS / Udemy",
        "estimated_duration": "2 months"
    },
    {
        "title": "DeepLearning.AI TensorFlow Developer Professional Certificate",
        "domain": "machine learning",
        "platform": "Coursera",
        "estimated_duration": "4 months"
    },
    {
        "title": "Meta Front-End Developer Professional Certificate",
        "domain": "software development",
        "platform": "Coursera",
        "estimated_duration": "7 months"
    }
]

@mcp.tool()
def get_certifications(domain: str) -> str:
    """Recommends professional certifications and learning paths for a given career domain.
    
    Args:
        domain: The domain of interest (e.g. 'data science', 'cloud computing', 'machine learning', 'software development')
    """
    domain_lower = domain.lower()
    matches = []
    for c in MOCK_COURSES:
        if domain_lower in c["domain"] or domain_lower in c["title"].lower():
            matches.append(c)
            
    if not matches:
        return f"No specific courses found for '{domain}'. We recommend searching general MOOC platforms like Coursera/edX under the computer science category."
        
    return f"Certification and course recommendations for '{domain}':\n" + "\n\n".join(
        [f"- **{c['title']}**\n  - Platform: {c['platform']}\n  - Duration: {c['estimated_duration']}\n  - Focus Domain: {c['domain']}" for c in matches]
    )

if __name__ == "__main__":
    mcp.run()
