"""
Skill Normalizer Service

Handles canonicalization of skill names with alias mappings.
Preserves display names while computing normalized canonical names.
"""

import re
from typing import Dict, Optional


# Alias mappings: all keys map to their canonical form
# Keys are lowercase for consistent matching
SKILL_ALIASES: Dict[str, str] = {
    # JavaScript variants
    "js": "javascript",
    "javascript": "javascript",

    # C# variants
    "c#": "csharp",
    "csharp": "csharp",

    # .NET variants
    ".net": "dotnet",
    "dotnet": "dotnet",
    ".net core": "dotnet",
    "dotnet core": "dotnet",

    # Node.js variants
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "node": "nodejs",

    # React variants
    "react.js": "react",
    "reactjs": "react",
    "react": "react",

    # Vue variants
    "vue.js": "vue",
    "vuejs": "vue",
    "vue": "vue",

    # TypeScript variants
    "typescript": "typescript",
    "ts": "typescript",

    # Database variants
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "pg": "postgresql",
    "mongodb": "mongodb",
    "mongo": "mongodb",

    # Cloud variants
    "aws": "aws",
    "amazon web services": "aws",

    # C++ variants
    "c++": "cplusplus",
    "cplusplus": "cplusplus",
    "cpp": "cplusplus",

    # Python variants (already normalized)
    "python": "python",
    "python3": "python",
    "py": "python",

    # SQL variants
    "sql": "sql",
    "mysql": "mysql",
    "sqlite": "sqlite",
    "sqlite3": "sqlite",
}

# Display names for canonical forms (user-friendly format)
CANONICAL_DISPLAY_NAMES: Dict[str, str] = {
    "javascript": "JavaScript",
    "csharp": "C#",
    "dotnet": ".NET",
    "nodejs": "Node.js",
    "react": "React",
    "vue": "Vue.js",
    "typescript": "TypeScript",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "aws": "AWS",
    "cplusplus": "C++",
    "python": "Python",
    "sql": "SQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
}


class SkillNormalizer:
    """
    Service for normalizing skill names to canonical forms.

    Handles:
    - Alias resolution (JS -> javascript, C# -> csharp)
    - Whitespace normalization
    - Case normalization
    - Special character handling
    """

    def __init__(
        self,
        aliases: Optional[Dict[str, str]] = None,
        display_names: Optional[Dict[str, str]] = None
    ):
        """
        Initialize SkillNormalizer.

        Args:
            aliases: Custom alias mappings (defaults to SKILL_ALIASES)
            display_names: Custom display names (defaults to CANONICAL_DISPLAY_NAMES)
        """
        self.aliases = aliases or SKILL_ALIASES
        self.display_names = display_names or CANONICAL_DISPLAY_NAMES

    def normalize(self, skill_name: str) -> str:
        """
        Normalize a skill name to its canonical form.

        Args:
            skill_name: Raw skill name (e.g., "  JavaScript  ", "JS", "node.js")

        Returns:
            Canonical name (e.g., "javascript", "javascript", "nodejs")
            Returns empty string for None/empty input.

        Examples:
            >>> normalizer = SkillNormalizer()
            >>> normalizer.normalize("JavaScript")
            'javascript'
            >>> normalizer.normalize("JS")
            'javascript'
            >>> normalizer.normalize("  React.js  ")
            'react'
            >>> normalizer.normalize("C#")
            'csharp'
        """
        # Handle None or empty input
        if not skill_name:
            return ""

        # Convert to string if needed
        if not isinstance(skill_name, str):
            skill_name = str(skill_name)

        # Step 1: Strip whitespace
        cleaned = skill_name.strip()

        # Handle empty after strip
        if not cleaned:
            return ""

        # Step 2: Lowercase for matching
        lowered = cleaned.lower()

        # Step 3: Check alias mapping first (before further processing)
        if lowered in self.aliases:
            return self.aliases[lowered]

        # Step 4: Apply special character transformations
        # Replace common special characters
        normalized = self._normalize_special_chars(lowered)

        # Step 5: Check alias mapping again after normalization
        if normalized in self.aliases:
            return self.aliases[normalized]

        # Step 6: Return normalized string (already lowercase)
        return normalized

    def _normalize_special_chars(self, text: str) -> str:
        """
        Normalize special characters in skill names.

        Args:
            text: Lowercase skill name

        Returns:
            Normalized string with special chars handled
        """
        # Remove extra whitespace (collapse multiple spaces)
        text = re.sub(r'\s+', ' ', text)

        # Replace specific patterns
        # Note: Some patterns like C# and C++ are handled by aliases
        # This handles remaining edge cases

        # Replace forward slashes with nothing (e.g., "Node/Express" -> "nodeexpress")
        text = text.replace('/', '')

        # Replace hyphens with nothing for matching (e.g., "vue-router" stays)
        # We keep hyphens as they might be meaningful

        # Replace underscores with nothing
        text = text.replace('_', '')

        # Remove parentheses and their contents for matching
        text = re.sub(r'\([^)]*\)', '', text).strip()

        return text

    def get_display_name(self, canonical_name: str) -> str:
        """
        Get user-friendly display name for a canonical name.

        Args:
            canonical_name: Normalized canonical name (e.g., "javascript", "csharp")

        Returns:
            Display name (e.g., "JavaScript", "C#")
            Returns title-cased canonical name if no display name defined.

        Examples:
            >>> normalizer = SkillNormalizer()
            >>> normalizer.get_display_name("javascript")
            'JavaScript'
            >>> normalizer.get_display_name("csharp")
            'C#'
            >>> normalizer.get_display_name("django")
            'Django'
        """
        if not canonical_name:
            return ""

        # Check if we have a defined display name
        if canonical_name in self.display_names:
            return self.display_names[canonical_name]

        # Default: Title case the canonical name
        return canonical_name.title()

    def normalize_batch(self, skill_names: list) -> list:
        """
        Normalize a batch of skill names.

        Args:
            skill_names: List of raw skill names

        Returns:
            List of canonical names
        """
        return [self.normalize(name) for name in skill_names]

    def add_alias(self, alias: str, canonical: str) -> None:
        """
        Add a new alias mapping.

        Args:
            alias: The alias to map (will be lowercased)
            canonical: The canonical form
        """
        self.aliases[alias.lower()] = canonical

    def add_display_name(self, canonical: str, display: str) -> None:
        """
        Add a new display name mapping.

        Args:
            canonical: The canonical form
            display: The display name
        """
        self.display_names[canonical] = display


# Singleton instance for convenience
_default_normalizer: Optional[SkillNormalizer] = None


def get_skill_normalizer() -> SkillNormalizer:
    """Get the default SkillNormalizer singleton."""
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = SkillNormalizer()
    return _default_normalizer


def normalize_skill(skill_name: str) -> str:
    """
    Convenience function to normalize a skill name.

    Args:
        skill_name: Raw skill name

    Returns:
        Canonical name
    """
    return get_skill_normalizer().normalize(skill_name)


def get_skill_display_name(canonical_name: str) -> str:
    """
    Convenience function to get display name.

    Args:
        canonical_name: Canonical skill name

    Returns:
        Display name
    """
    return get_skill_normalizer().get_display_name(canonical_name)
