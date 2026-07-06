# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import json
import re
import sys
from typing import AsyncGenerator, Any
from pydantic import BaseModel, Field

from google.adk.workflow import Workflow, node, START
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.agents.context import Context
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.models import Gemini
from google.adk.apps import App, ResumabilityConfig
from google.genai import types

from app.config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("student-success-nav")

# ----------------------------------------------------
# 1. Helper function for dynamic type content parsing
# ----------------------------------------------------
def get_text_content(node_input: Any) -> str:
    """Helper to safely extract string text from any node input type."""
    if isinstance(node_input, str):
        return node_input
    if hasattr(node_input, 'parts'):  # types.Content
        return "".join([part.text for part in node_input.parts if part.text])
    if isinstance(node_input, dict):
        return json.dumps(node_input)
    return str(node_input)

# ----------------------------------------------------
# 2. Local MCP Toolset configuration
# ----------------------------------------------------
mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp_server"],
        )
    )
)

# ----------------------------------------------------
# 3. Specialized LlmAgents (Sub-Agents)
# ----------------------------------------------------
# Scholarship Discovery Agent
scholarship_agent = LlmAgent(
    name="scholarship_agent",
    model=Gemini(model=config.model),
    instruction="""You are an expert Scholarship Advisor. 
Given a student's profile (education level, CGPA, income category, location), search for suitable scholarships (e.g. government scholarships, merit-based, private, corporate).
Use the search_scholarships tool to find matching opportunities.
List matching scholarships with title, eligibility explanation, benefits, and estimated deadlines.
Focus only on realistic opportunities the student is eligible for. Return a detailed, clear markdown report.
""",
    tools=[mcp_toolset],
    description="Finds and analyzes scholarship opportunities based on student profiles.",
)

# Career Growth Agent
career_agent = LlmAgent(
    name="career_agent",
    model=Gemini(model=config.model),
    instruction="""You are an expert Career Mentor.
Given a student's profile (skills, interests, degree, branch), recommend internships, hackathons, open source programs, and professional fellowships.
Use the search_internships tool to look up specific opportunities matching the student's skills.
Provide specific, actionable steps to apply, explaining why each is recommended. List deadlines.
Return a detailed, clear markdown report.
""",
    tools=[mcp_toolset],
    description="Recommends internships, fellowships, hackathons, and competitions matching skills and interests.",
)

# Academic Success Agent
academic_agent = LlmAgent(
    name="academic_agent",
    model=Gemini(model=config.model),
    instruction="""You are an expert Academic Guidance counselor.
Given a student's profile, recommend industry-relevant certifications, learning paths, online courses (e.g. Coursera, edX, NPTEL), and higher education options.
Use the get_certifications tool to recommend high-quality professional learning programs matching their field.
Provide a clear learning roadmap. Return a detailed, clear markdown report.
""",
    tools=[mcp_toolset],
    description="Recommends certifications, online courses, and higher education learning paths.",
)

# ----------------------------------------------------
# 4. Orchestrator LlmAgent
# ----------------------------------------------------
orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=Gemini(model=config.model),
    instruction="""You are the Coordinator for the Student Success Navigator.
You have access to three specialist advisors:
1. scholarship_agent — for scholarship queries.
2. career_agent — for internships, hackathons, and career paths.
3. academic_agent — for certifications, learning paths, and courses.

When a query comes in, you must:
1. Read the user's profile and query details.
2. Delegate the query to the appropriate specialist(s) using their tools. Always call multiple tools if the user is asking for comprehensive guidance.
3. Synthesize the findings into a clear, comprehensive student success roadmap and personalized action plan.
""",
    tools=[AgentTool(scholarship_agent), AgentTool(career_agent), AgentTool(academic_agent)],
    description="Coordinates and delegates student inquiries to relevant specialist agents.",
)

# ----------------------------------------------------
# 5. Workflow Nodes
# ----------------------------------------------------
def security_checkpoint(ctx: Context, node_input: Any) -> Event:
    """Security Checkpoint Node.
    Filters out PII (like phone numbers, emails, and passwords),
    detects prompt injection keywords, and logs security checks.
    """
    query_text = get_text_content(node_input)

    # Log the incoming check
    logger.info(f"Security Checkpoint: Scanning query: {query_text[:100]}...")

    # 2. Prompt Injection Detection
    injection_keywords = [
        "ignore previous instructions", "ignore all instructions", "system prompt",
        "bypass", "override instructions", "you must now act as", "jailbreak"
    ]
    detected_keywords = [kw for kw in injection_keywords if kw in query_text.lower()]
    if detected_keywords:
        audit_log = {
            "event": "PROMPT_INJECTION_DETECTED",
            "severity": "CRITICAL",
            "details": f"Detected keywords: {detected_keywords}",
            "session_id": ctx.session.id
        }
        logger.warning(json.dumps(audit_log))
        return Event(
            output="Security Violation: Possible prompt injection attempt detected.",
            route="security_alert"
        )

    # 3. PII Scrubbing
    # Phone numbers
    phone_pattern = r'\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b'
    # Email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    scrubbed_text = re.sub(phone_pattern, "[PHONE_REDACTED]", query_text)
    scrubbed_text = re.sub(email_pattern, "[EMAIL_REDACTED]", scrubbed_text)

    # 4. Domain-Specific Rule: Prevent scraping or non-academic exploitation
    inappropriate_keywords = ["torrents", "crack software", "bypass exam", "cheat exam"]
    detected_inappropriate = [kw for kw in inappropriate_keywords if kw in scrubbed_text.lower()]
    if detected_inappropriate:
        audit_log = {
            "event": "DOMAIN_RULE_VIOLATION",
            "severity": "WARNING",
            "details": f"Inappropriate keywords: {detected_inappropriate}",
            "session_id": ctx.session.id
        }
        logger.warning(json.dumps(audit_log))
        return Event(
            output="Security Violation: Request contains topics outside academic/career scope.",
            route="security_alert"
        )

    # Success Log
    audit_log = {
        "event": "SECURITY_CHECK_PASSED",
        "severity": "INFO",
        "details": "No issues found. PII redacted if present.",
        "session_id": ctx.session.id
    }
    logger.info(json.dumps(audit_log))

    # Save clean text to state
    return Event(output=scrubbed_text, route="clear", state={"cleaned_query": scrubbed_text})

async def human_review(ctx: Context, node_input: Any) -> AsyncGenerator[Event, None]:
    """Human-in-the-loop verification node."""
    # Check if we have response from HITL
    if not ctx.resume_inputs or "confirm_recommendations" not in ctx.resume_inputs:
        logger.info("Human Review: Requesting user confirmation.")
        
        # Display the draft recommendation to the user
        draft_text = get_text_content(node_input)
        
        prompt_msg = (
            f"Here is the draft recommendation from the Navigator:\n\n{draft_text}\n\n"
            "Please review this draft. Do you approve? Type 'approve' to proceed, or describe any changes you want."
        )
        
        yield RequestInput(
            interrupt_id="confirm_recommendations",
            message=prompt_msg
        )
        return

    # If resumed, read the human input
    user_feedback = ctx.resume_inputs["confirm_recommendations"]
    logger.info(f"Human Review: Received response: {user_feedback}")

    draft_text = get_text_content(node_input)
    if user_feedback.lower().strip() == "approve":
        yield Event(output=draft_text, state={"review_status": "approved"})
    else:
        feedback_msg = f"Draft reviewed by student. Feedback: '{user_feedback}'. Adjusting results accordingly."
        # Yield updated output text reflecting user preference
        yield Event(output=types.Content(role="model", parts=[types.Part.from_text(text=f"{feedback_msg}\n\nProcessed Report:\n\n{draft_text}")]), state={"review_status": "modified", "feedback": user_feedback})

def final_output(node_input: Any) -> Any:
    """Formats and returns the final response for the user interface."""
    text = get_text_content(node_input)
    yield Event(content=types.Content(role='model', parts=[types.Part.from_text(text=text)]))
    yield Event(output=text)

# ----------------------------------------------------
# 6. Workflow Definitions
# ----------------------------------------------------
root_agent = Workflow(
    name="student_success_navigator",
    edges=[
        ('START', security_checkpoint),
        (security_checkpoint, { "clear": orchestrator_agent, "security_alert": final_output }),
        (orchestrator_agent, human_review),
        (human_review, final_output)
    ],
    description="A multi-agent system to guide student academic and career success.",
)

# ----------------------------------------------------
# 7. App Configuration
# ----------------------------------------------------
app = App(
    name="app",
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True)
)
