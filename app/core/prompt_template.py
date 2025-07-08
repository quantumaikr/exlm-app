"""
Prompt template engine for managing and rendering prompts
"""

import re
import json
from typing import Dict, Any, List, Optional
from jinja2 import Template, Environment, meta, TemplateError
from pydantic import BaseModel, Field

from app.core.logging import logger


class PromptVariable(BaseModel):
    """Prompt template variable definition"""
    name: str
    type: str = "text"  # text, number, boolean, list, json
    description: str = ""
    required: bool = True
    default: Any = None
    validation: Optional[Dict[str, Any]] = None  # min_length, max_length, min, max, regex, etc.


class PromptTemplate(BaseModel):
    """Prompt template definition"""
    id: str
    name: str
    description: str
    template: str
    variables: List[PromptVariable] = []
    tags: List[str] = []
    examples: List[Dict[str, Any]] = []
    version: str = "1.0"
    
    class Config:
        json_encoders = {
            PromptVariable: lambda v: v.dict()
        }


class PromptTemplateEngine:
    """Engine for managing and rendering prompt templates"""
    
    def __init__(self):
        self.env = Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        self.templates: Dict[str, PromptTemplate] = {}
    
    def register_template(self, template: PromptTemplate):
        """Register a prompt template"""
        self.templates[template.id] = template
        logger.info(f"Registered prompt template: {template.id}")
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a prompt template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """List all templates, optionally filtered by tags"""
        templates = list(self.templates.values())
        
        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]
        
        return templates
    
    def extract_variables(self, template_str: str) -> List[str]:
        """Extract variable names from a template string"""
        try:
            ast = self.env.parse(template_str)
            return sorted(meta.find_undeclared_variables(ast))
        except TemplateError as e:
            logger.error(f"Failed to parse template: {e}")
            return []
    
    def validate_variables(
        self,
        template: PromptTemplate,
        variables: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Validate variables against template requirements"""
        errors = {}
        
        for var in template.variables:
            if var.required and var.name not in variables:
                errors.setdefault(var.name, []).append("Required variable missing")
                continue
            
            if var.name not in variables:
                continue
            
            value = variables[var.name]
            
            # Type validation
            if var.type == "number":
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    errors.setdefault(var.name, []).append("Must be a number")
                    continue
            
            elif var.type == "boolean":
                if not isinstance(value, bool):
                    errors.setdefault(var.name, []).append("Must be a boolean")
                    continue
            
            elif var.type == "list":
                if not isinstance(value, list):
                    errors.setdefault(var.name, []).append("Must be a list")
                    continue
            
            elif var.type == "json":
                if isinstance(value, str):
                    try:
                        json.loads(value)
                    except json.JSONDecodeError:
                        errors.setdefault(var.name, []).append("Must be valid JSON")
                        continue
            
            # Additional validation rules
            if var.validation:
                if var.type == "text" and isinstance(value, str):
                    if "min_length" in var.validation and len(value) < var.validation["min_length"]:
                        errors.setdefault(var.name, []).append(
                            f"Minimum length is {var.validation['min_length']}"
                        )
                    
                    if "max_length" in var.validation and len(value) > var.validation["max_length"]:
                        errors.setdefault(var.name, []).append(
                            f"Maximum length is {var.validation['max_length']}"
                        )
                    
                    if "regex" in var.validation:
                        if not re.match(var.validation["regex"], value):
                            errors.setdefault(var.name, []).append(
                                f"Does not match pattern: {var.validation['regex']}"
                            )
                
                elif var.type == "number" and isinstance(value, (int, float)):
                    if "min" in var.validation and value < var.validation["min"]:
                        errors.setdefault(var.name, []).append(
                            f"Minimum value is {var.validation['min']}"
                        )
                    
                    if "max" in var.validation and value > var.validation["max"]:
                        errors.setdefault(var.name, []).append(
                            f"Maximum value is {var.validation['max']}"
                        )
        
        return errors
    
    def render(
        self,
        template_id: str,
        variables: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """Render a prompt template with variables"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Apply defaults
        for var in template.variables:
            if var.name not in variables and var.default is not None:
                variables[var.name] = var.default
        
        # Validate if requested
        if validate:
            errors = self.validate_variables(template, variables)
            if errors:
                raise ValueError(f"Variable validation failed: {errors}")
        
        # Render template
        try:
            jinja_template = self.env.from_string(template.template)
            return jinja_template.render(**variables)
        except TemplateError as e:
            logger.error(f"Failed to render template {template_id}: {e}")
            raise
    
    def render_string(
        self,
        template_str: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render a template string directly"""
        try:
            jinja_template = self.env.from_string(template_str)
            return jinja_template.render(**variables)
        except TemplateError as e:
            logger.error(f"Failed to render template string: {e}")
            raise


# Pre-defined templates
DEFAULT_TEMPLATES = [
    PromptTemplate(
        id="instruction_following",
        name="Instruction Following",
        description="Template for instruction-following tasks",
        template="""Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{{ instruction }}

### Response:
{{ response }}""",
        variables=[
            PromptVariable(name="instruction", type="text", description="The instruction to follow"),
            PromptVariable(name="response", type="text", description="The expected response")
        ],
        tags=["instruction", "general"]
    ),
    
    PromptTemplate(
        id="qa_context",
        name="Question Answering with Context",
        description="Template for QA tasks with context",
        template="""Answer the question based on the context below.

Context: {{ context }}

Question: {{ question }}

Answer: {{ answer }}""",
        variables=[
            PromptVariable(name="context", type="text", description="The context information"),
            PromptVariable(name="question", type="text", description="The question to answer"),
            PromptVariable(name="answer", type="text", description="The expected answer")
        ],
        tags=["qa", "context"]
    ),
    
    PromptTemplate(
        id="chat_conversation",
        name="Chat Conversation",
        description="Template for multi-turn chat conversations",
        template="""{% for message in messages %}
{{ message.role|capitalize }}: {{ message.content }}
{% endfor %}
Assistant: {{ response }}""",
        variables=[
            PromptVariable(name="messages", type="list", description="List of conversation messages"),
            PromptVariable(name="response", type="text", description="The assistant's response")
        ],
        tags=["chat", "conversation"]
    ),
    
    PromptTemplate(
        id="code_generation",
        name="Code Generation",
        description="Template for code generation tasks",
        template="""Generate {{ language }} code for the following task:

Task: {{ task_description }}
{% if requirements %}
Requirements:
{% for req in requirements %}
- {{ req }}
{% endfor %}
{% endif %}

Code:
```{{ language }}
{{ code }}
```""",
        variables=[
            PromptVariable(name="language", type="text", description="Programming language"),
            PromptVariable(name="task_description", type="text", description="Description of the coding task"),
            PromptVariable(name="requirements", type="list", description="Additional requirements", required=False),
            PromptVariable(name="code", type="text", description="The generated code")
        ],
        tags=["code", "generation"]
    ),
    
    PromptTemplate(
        id="summarization",
        name="Text Summarization",
        description="Template for text summarization tasks",
        template="""Summarize the following text in {{ style }} style{% if max_length %}, keeping it under {{ max_length }} words{% endif %}:

Text: {{ text }}

Summary: {{ summary }}""",
        variables=[
            PromptVariable(name="text", type="text", description="Text to summarize"),
            PromptVariable(name="style", type="text", description="Summary style (e.g., 'concise', 'detailed')", default="concise"),
            PromptVariable(name="max_length", type="number", description="Maximum summary length in words", required=False),
            PromptVariable(name="summary", type="text", description="The generated summary")
        ],
        tags=["summarization", "text"]
    )
]


# Global template engine instance
template_engine = PromptTemplateEngine()

# Register default templates
for template in DEFAULT_TEMPLATES:
    template_engine.register_template(template)