"""Controlled vocabularies shared by onboarding, the engines and the frontend."""
from __future__ import annotations

# Domains used for interests, career categorisation and the profile visualisation.
DOMAINS: dict[str, str] = {
    "ai": "AI",
    "technology": "Technology",
    "data": "Data",
    "business": "Business",
    "finance": "Finance",
    "cybersecurity": "Cybersecurity",
    "design": "Design",
    "marketing": "Marketing",
    "healthcare": "Healthcare",
    "research": "Research",
    "product": "Product",
    "entrepreneurship": "Entrepreneurship",
    "cloud": "Cloud",
    "engineering": "Engineering",
    "science": "Science",
    "media": "Media",
    "education": "Education",
    "operations": "Operations",
}

# Onboarding step 1 — "What are you interested in?"
INTEREST_OPTIONS = [
    "ai", "technology", "business", "finance", "healthcare", "cybersecurity", "design",
    "marketing", "research", "entrepreneurship", "data", "science", "engineering", "media", "education",
]

# Onboarding step 3 — "What do you enjoy doing?" -> domain signal weights
ACTIVITIES: dict[str, dict] = {
    "building": {"label": "Building things", "domains": {"technology": 1.0, "engineering": 0.8, "ai": 0.4, "entrepreneurship": 0.3}},
    "problem_solving": {"label": "Solving problems", "domains": {"technology": 0.6, "engineering": 0.6, "data": 0.4, "business": 0.4, "research": 0.3}},
    "analyzing_data": {"label": "Analyzing data", "domains": {"data": 1.0, "ai": 0.4, "finance": 0.3, "research": 0.3}},
    "people": {"label": "Working with people", "domains": {"business": 0.8, "product": 0.6, "marketing": 0.4, "education": 0.5}},
    "researching": {"label": "Researching", "domains": {"research": 1.0, "science": 0.8, "ai": 0.3}},
    "designing": {"label": "Designing", "domains": {"design": 1.0, "product": 0.4, "media": 0.4}},
    "managing_projects": {"label": "Managing projects", "domains": {"business": 0.8, "product": 0.8, "operations": 0.8}},
    "numbers": {"label": "Working with numbers", "domains": {"finance": 1.0, "data": 0.7, "science": 0.3}},
    "writing": {"label": "Writing", "domains": {"media": 1.0, "marketing": 0.5, "research": 0.4, "education": 0.3}},
    "teaching": {"label": "Teaching", "domains": {"education": 1.0, "media": 0.3}},
    "starting_businesses": {"label": "Starting businesses", "domains": {"entrepreneurship": 1.0, "business": 0.6, "product": 0.4}},
    "technology": {"label": "Working with technology", "domains": {"technology": 1.0, "cloud": 0.5, "ai": 0.4, "cybersecurity": 0.3}},
}

# Onboarding step 4 — "What kind of work sounds interesting?"
WORK_STYLES: dict[str, dict] = {
    "build_software": {"label": "Build software", "domains": {"technology": 1.0, "engineering": 0.5, "cloud": 0.3}},
    "analyze_information": {"label": "Analyze information", "domains": {"data": 0.8, "research": 0.6, "business": 0.4}},
    "work_with_data": {"label": "Work with data", "domains": {"data": 1.0, "ai": 0.5}},
    "create_products": {"label": "Create products", "domains": {"product": 1.0, "design": 0.4, "entrepreneurship": 0.5, "technology": 0.3}},
    "solve_business_problems": {"label": "Solve business problems", "domains": {"business": 1.0, "operations": 0.5, "finance": 0.3}},
    "research_technology": {"label": "Research new technology", "domains": {"research": 0.8, "ai": 0.7, "science": 0.5}},
    "manage_teams": {"label": "Manage teams", "domains": {"business": 0.6, "operations": 0.7, "product": 0.4}},
    "work_with_customers": {"label": "Work with customers", "domains": {"business": 0.5, "marketing": 0.6, "product": 0.3}},
    "design_experiences": {"label": "Design experiences", "domains": {"design": 1.0, "product": 0.5}},
    "financial_information": {"label": "Work with financial information", "domains": {"finance": 1.0, "data": 0.3}},
}

LEVELS = {0: "Not yet", 1: "Beginner", 2: "Intermediate", 3: "Advanced"}
LEVEL_FROM_LABEL = {"none": 0, "beginner": 1, "intermediate": 2, "advanced": 3}

EXPERIENCE_LEVELS = ["student", "entry", "junior", "mid", "senior", "career_switcher"]
LEARNING_PREFERENCES = ["video", "reading", "hands_on", "courses", "mentorship", "projects"]

IMPORTANCE_WEIGHT = {"core": 1.0, "important": 0.6, "useful": 0.3}

# Comparison dimensions are derived from the skill categories a career requires.
COMPARISON_DIMENSIONS = {
    "programming": {"label": "Programming", "categories": ["programming", "software"]},
    "statistics": {"label": "Statistics", "categories": ["statistics"]},
    "ai_ml": {"label": "AI / ML", "categories": ["ai"]},
    "data": {"label": "Data", "categories": ["data"]},
    "deployment": {"label": "Deployment", "categories": ["infrastructure"]},
    "business": {"label": "Business interaction", "categories": ["business", "professional"]},
}
EMPHASIS_LABELS = {0: "Minimal", 1: "Some", 2: "Significant", 3: "Central"}


def a_an(phrase: str) -> str:
    """'an AI Engineer', 'a UX Designer', 'an important skill', 'a useful skill'."""
    word = phrase.strip().split(" ")[0].strip("*_`\"'")
    if len(word) > 1 and word[:2].isupper():  # acronym (AI, UX, MLOps): pronounced letter by letter
        vowel_sound = word[0] in "AEFHILMNORSX"
    else:
        low = word.lower()
        vowel_sound = low[:1] in "aeiou" and not low.startswith(("use", "usu", "uni", "one"))
    return f"{'an' if vowel_sound else 'a'} {phrase}"
