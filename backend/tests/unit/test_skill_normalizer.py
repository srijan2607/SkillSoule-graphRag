"""
Unit tests for SkillNormalizer service.

Tests cover:
- All alias mappings (JS→javascript, C#→csharp, .NET→dotnet, etc.)
- Case insensitivity
- Whitespace handling
- Special character handling
- Display name conversion
- Edge cases (empty, None, numbers)
"""

import pytest
from app.services.skill_normalizer import (
    SkillNormalizer,
    normalize_skill,
    get_skill_display_name,
    get_skill_normalizer,
    SKILL_ALIASES,
    CANONICAL_DISPLAY_NAMES,
)


class TestSkillNormalizer:
    """Tests for SkillNormalizer class."""

    @pytest.fixture
    def normalizer(self) -> SkillNormalizer:
        """Create a fresh SkillNormalizer instance."""
        return SkillNormalizer()

    # ===========================================
    # JavaScript variants
    # ===========================================

    def test_normalize_js_returns_javascript(self, normalizer: SkillNormalizer):
        """Test JS alias maps to javascript."""
        assert normalizer.normalize("JS") == "javascript"
        assert normalizer.normalize("js") == "javascript"

    def test_normalize_javascript_returns_javascript(self, normalizer: SkillNormalizer):
        """Test JavaScript normalizes correctly."""
        assert normalizer.normalize("JavaScript") == "javascript"
        assert normalizer.normalize("javascript") == "javascript"
        assert normalizer.normalize("JAVASCRIPT") == "javascript"

    # ===========================================
    # C# variants
    # ===========================================

    def test_normalize_csharp_returns_csharp(self, normalizer: SkillNormalizer):
        """Test C# variants map to csharp."""
        assert normalizer.normalize("C#") == "csharp"
        assert normalizer.normalize("c#") == "csharp"
        assert normalizer.normalize("csharp") == "csharp"
        assert normalizer.normalize("CSharp") == "csharp"

    # ===========================================
    # .NET variants
    # ===========================================

    def test_normalize_dotnet_variants(self, normalizer: SkillNormalizer):
        """Test .NET variants all map to dotnet."""
        assert normalizer.normalize(".NET") == "dotnet"
        assert normalizer.normalize(".net") == "dotnet"
        assert normalizer.normalize("dotnet") == "dotnet"
        assert normalizer.normalize(".NET Core") == "dotnet"
        assert normalizer.normalize(".net core") == "dotnet"
        assert normalizer.normalize("dotnet core") == "dotnet"

    # ===========================================
    # Node.js variants
    # ===========================================

    def test_normalize_nodejs_variants(self, normalizer: SkillNormalizer):
        """Test Node.js variants all map to nodejs."""
        assert normalizer.normalize("Node.js") == "nodejs"
        assert normalizer.normalize("node.js") == "nodejs"
        assert normalizer.normalize("NodeJS") == "nodejs"
        assert normalizer.normalize("nodejs") == "nodejs"
        assert normalizer.normalize("node") == "nodejs"

    # ===========================================
    # React variants
    # ===========================================

    def test_normalize_react_variants(self, normalizer: SkillNormalizer):
        """Test React variants all map to react."""
        assert normalizer.normalize("React") == "react"
        assert normalizer.normalize("react") == "react"
        assert normalizer.normalize("React.js") == "react"
        assert normalizer.normalize("react.js") == "react"
        assert normalizer.normalize("ReactJS") == "react"
        assert normalizer.normalize("reactjs") == "react"

    # ===========================================
    # Vue variants
    # ===========================================

    def test_normalize_vue_variants(self, normalizer: SkillNormalizer):
        """Test Vue variants all map to vue."""
        assert normalizer.normalize("Vue") == "vue"
        assert normalizer.normalize("vue") == "vue"
        assert normalizer.normalize("Vue.js") == "vue"
        assert normalizer.normalize("vue.js") == "vue"
        assert normalizer.normalize("VueJS") == "vue"
        assert normalizer.normalize("vuejs") == "vue"

    # ===========================================
    # TypeScript variants
    # ===========================================

    def test_normalize_typescript_variants(self, normalizer: SkillNormalizer):
        """Test TypeScript variants all map to typescript."""
        assert normalizer.normalize("TypeScript") == "typescript"
        assert normalizer.normalize("typescript") == "typescript"
        assert normalizer.normalize("TS") == "typescript"
        assert normalizer.normalize("ts") == "typescript"

    # ===========================================
    # Database variants
    # ===========================================

    def test_normalize_postgresql_variants(self, normalizer: SkillNormalizer):
        """Test PostgreSQL variants all map to postgresql."""
        assert normalizer.normalize("PostgreSQL") == "postgresql"
        assert normalizer.normalize("postgresql") == "postgresql"
        assert normalizer.normalize("Postgres") == "postgresql"
        assert normalizer.normalize("postgres") == "postgresql"
        assert normalizer.normalize("pg") == "postgresql"

    def test_normalize_mongodb_variants(self, normalizer: SkillNormalizer):
        """Test MongoDB variants all map to mongodb."""
        assert normalizer.normalize("MongoDB") == "mongodb"
        assert normalizer.normalize("mongodb") == "mongodb"
        assert normalizer.normalize("Mongo") == "mongodb"
        assert normalizer.normalize("mongo") == "mongodb"

    # ===========================================
    # Cloud variants
    # ===========================================

    def test_normalize_aws_variants(self, normalizer: SkillNormalizer):
        """Test AWS variants all map to aws."""
        assert normalizer.normalize("AWS") == "aws"
        assert normalizer.normalize("aws") == "aws"
        assert normalizer.normalize("Amazon Web Services") == "aws"
        assert normalizer.normalize("amazon web services") == "aws"

    # ===========================================
    # C++ variants
    # ===========================================

    def test_normalize_cplusplus_variants(self, normalizer: SkillNormalizer):
        """Test C++ variants all map to cplusplus."""
        assert normalizer.normalize("C++") == "cplusplus"
        assert normalizer.normalize("c++") == "cplusplus"
        assert normalizer.normalize("cpp") == "cplusplus"
        assert normalizer.normalize("CPP") == "cplusplus"

    # ===========================================
    # Python variants
    # ===========================================

    def test_normalize_python_variants(self, normalizer: SkillNormalizer):
        """Test Python variants all map to python."""
        assert normalizer.normalize("Python") == "python"
        assert normalizer.normalize("python") == "python"
        assert normalizer.normalize("PYTHON") == "python"
        assert normalizer.normalize("Python3") == "python"
        assert normalizer.normalize("python3") == "python"
        assert normalizer.normalize("py") == "python"

    # ===========================================
    # Case insensitivity tests
    # ===========================================

    def test_normalize_case_insensitive(self, normalizer: SkillNormalizer):
        """Test that normalization is case insensitive."""
        # Various case combinations should all normalize the same
        assert normalizer.normalize("Python") == "python"
        assert normalizer.normalize("PYTHON") == "python"
        assert normalizer.normalize("python") == "python"
        assert normalizer.normalize("PyThOn") == "python"

        assert normalizer.normalize("Django") == "django"
        assert normalizer.normalize("DJANGO") == "django"
        assert normalizer.normalize("django") == "django"

    # ===========================================
    # Whitespace handling tests
    # ===========================================

    def test_normalize_whitespace_handling(self, normalizer: SkillNormalizer):
        """Test whitespace is properly stripped."""
        assert normalizer.normalize("  React  ") == "react"
        assert normalizer.normalize("\tPython\t") == "python"
        assert normalizer.normalize("\n  JavaScript  \n") == "javascript"
        assert normalizer.normalize("   ") == ""  # Only whitespace

    def test_normalize_internal_whitespace(self, normalizer: SkillNormalizer):
        """Test internal whitespace is handled."""
        # Multiple spaces should be collapsed
        assert normalizer.normalize("Amazon  Web  Services") == "aws"

    # ===========================================
    # Special character tests
    # ===========================================

    def test_normalize_special_characters(self, normalizer: SkillNormalizer):
        """Test special character handling."""
        # C++ and C# are handled by aliases
        assert normalizer.normalize("C++") == "cplusplus"
        assert normalizer.normalize("C#") == "csharp"

        # .NET variants
        assert normalizer.normalize(".NET") == "dotnet"

    # ===========================================
    # Edge case tests
    # ===========================================

    def test_normalize_empty_string_returns_empty(self, normalizer: SkillNormalizer):
        """Test empty string returns empty."""
        assert normalizer.normalize("") == ""

    def test_normalize_none_returns_empty(self, normalizer: SkillNormalizer):
        """Test None returns empty string."""
        assert normalizer.normalize(None) == ""

    def test_normalize_whitespace_only_returns_empty(self, normalizer: SkillNormalizer):
        """Test whitespace-only string returns empty."""
        assert normalizer.normalize("   ") == ""
        assert normalizer.normalize("\t\n") == ""

    def test_normalize_unknown_skill_returns_lowercase(self, normalizer: SkillNormalizer):
        """Test unknown skills are returned as lowercase."""
        assert normalizer.normalize("Django") == "django"
        assert normalizer.normalize("Flask") == "flask"
        assert normalizer.normalize("FastAPI") == "fastapi"
        assert normalizer.normalize("KUBERNETES") == "kubernetes"

    def test_normalize_numbers_handled(self, normalizer: SkillNormalizer):
        """Test skills with numbers are handled."""
        assert normalizer.normalize("Python3") == "python"
        assert normalizer.normalize("ES6") == "es6"
        assert normalizer.normalize("HTML5") == "html5"
        assert normalizer.normalize("CSS3") == "css3"

    def test_normalize_non_string_input(self, normalizer: SkillNormalizer):
        """Test non-string input is converted to string."""
        # Numbers passed as integers
        assert normalizer.normalize(123) == "123"

    # ===========================================
    # Display name tests
    # ===========================================

    def test_get_display_name_returns_proper_format(self, normalizer: SkillNormalizer):
        """Test display names are properly formatted."""
        assert normalizer.get_display_name("javascript") == "JavaScript"
        assert normalizer.get_display_name("csharp") == "C#"
        assert normalizer.get_display_name("dotnet") == ".NET"
        assert normalizer.get_display_name("nodejs") == "Node.js"
        assert normalizer.get_display_name("react") == "React"
        assert normalizer.get_display_name("vue") == "Vue.js"
        assert normalizer.get_display_name("typescript") == "TypeScript"
        assert normalizer.get_display_name("postgresql") == "PostgreSQL"
        assert normalizer.get_display_name("mongodb") == "MongoDB"
        assert normalizer.get_display_name("aws") == "AWS"
        assert normalizer.get_display_name("cplusplus") == "C++"
        assert normalizer.get_display_name("python") == "Python"

    def test_get_display_name_unknown_returns_title_case(self, normalizer: SkillNormalizer):
        """Test unknown canonical names return title case."""
        assert normalizer.get_display_name("django") == "Django"
        assert normalizer.get_display_name("flask") == "Flask"
        assert normalizer.get_display_name("fastapi") == "Fastapi"
        assert normalizer.get_display_name("kubernetes") == "Kubernetes"

    def test_get_display_name_empty_returns_empty(self, normalizer: SkillNormalizer):
        """Test empty canonical name returns empty."""
        assert normalizer.get_display_name("") == ""

    # ===========================================
    # Batch normalization tests
    # ===========================================

    def test_normalize_batch(self, normalizer: SkillNormalizer):
        """Test batch normalization works correctly."""
        skills = ["JS", "Python", "  React  ", "C#", "Node.js"]
        expected = ["javascript", "python", "react", "csharp", "nodejs"]
        assert normalizer.normalize_batch(skills) == expected

    def test_normalize_batch_empty_list(self, normalizer: SkillNormalizer):
        """Test empty batch returns empty list."""
        assert normalizer.normalize_batch([]) == []

    # ===========================================
    # Custom alias tests
    # ===========================================

    def test_add_alias(self, normalizer: SkillNormalizer):
        """Test adding custom alias."""
        normalizer.add_alias("k8s", "kubernetes")
        assert normalizer.normalize("k8s") == "kubernetes"
        assert normalizer.normalize("K8S") == "kubernetes"

    def test_add_display_name(self, normalizer: SkillNormalizer):
        """Test adding custom display name."""
        normalizer.add_display_name("kubernetes", "Kubernetes (K8s)")
        assert normalizer.get_display_name("kubernetes") == "Kubernetes (K8s)"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_normalize_skill_function(self):
        """Test normalize_skill convenience function."""
        assert normalize_skill("JavaScript") == "javascript"
        assert normalize_skill("  Python  ") == "python"
        assert normalize_skill("C#") == "csharp"

    def test_get_skill_display_name_function(self):
        """Test get_skill_display_name convenience function."""
        assert get_skill_display_name("javascript") == "JavaScript"
        assert get_skill_display_name("csharp") == "C#"
        assert get_skill_display_name("unknown") == "Unknown"

    def test_get_skill_normalizer_returns_singleton(self):
        """Test get_skill_normalizer returns singleton instance."""
        normalizer1 = get_skill_normalizer()
        normalizer2 = get_skill_normalizer()
        assert normalizer1 is normalizer2


class TestAliasCompleteness:
    """Tests to ensure alias mappings are complete."""

    def test_all_expected_aliases_exist(self):
        """Test that all expected aliases are in SKILL_ALIASES."""
        expected_aliases = [
            "js", "javascript",
            "c#", "csharp",
            ".net", "dotnet", ".net core", "dotnet core",
            "node.js", "nodejs", "node",
            "react.js", "reactjs", "react",
            "vue.js", "vuejs", "vue",
            "typescript", "ts",
            "postgresql", "postgres", "pg",
            "mongodb", "mongo",
            "aws", "amazon web services",
            "c++", "cplusplus", "cpp",
            "python", "python3", "py",
        ]
        for alias in expected_aliases:
            assert alias in SKILL_ALIASES, f"Missing alias: {alias}"

    def test_all_expected_display_names_exist(self):
        """Test that all expected display names are defined."""
        expected_canonicals = [
            "javascript", "csharp", "dotnet", "nodejs", "react",
            "vue", "typescript", "postgresql", "mongodb", "aws",
            "cplusplus", "python",
        ]
        for canonical in expected_canonicals:
            assert canonical in CANONICAL_DISPLAY_NAMES, f"Missing display name for: {canonical}"


class TestNormalizationConsistency:
    """Tests for normalization consistency across variants."""

    @pytest.fixture
    def normalizer(self) -> SkillNormalizer:
        return SkillNormalizer()

    def test_javascript_variants_consistent(self, normalizer: SkillNormalizer):
        """All JavaScript variants should normalize to same value."""
        variants = ["JS", "js", "JavaScript", "javascript", "JAVASCRIPT"]
        results = [normalizer.normalize(v) for v in variants]
        assert len(set(results)) == 1, f"Inconsistent results: {results}"
        assert results[0] == "javascript"

    def test_react_variants_consistent(self, normalizer: SkillNormalizer):
        """All React variants should normalize to same value."""
        variants = ["React", "react", "React.js", "ReactJS", "reactjs"]
        results = [normalizer.normalize(v) for v in variants]
        assert len(set(results)) == 1, f"Inconsistent results: {results}"
        assert results[0] == "react"

    def test_dotnet_variants_consistent(self, normalizer: SkillNormalizer):
        """All .NET variants should normalize to same value."""
        variants = [".NET", ".net", "dotnet", ".NET Core", "dotnet core"]
        results = [normalizer.normalize(v) for v in variants]
        assert len(set(results)) == 1, f"Inconsistent results: {results}"
        assert results[0] == "dotnet"
