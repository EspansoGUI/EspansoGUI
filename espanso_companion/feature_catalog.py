"""Central reference for the requested Espanso Companion Pro feature set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass
class CatalogSection:
    title: str
    description: str
    items: Sequence[str]


class FeatureCatalog:
    architecture: Dict[str, Sequence[str]] = {
        "core_modules": [
            "config_loader",
            "yaml_processor",
            "cli_integration",
            "file_watcher",
            "variable_engine",
        ],
        "ui_pages": [
            "dashboard",
            "snippet_library",
            "word_processor_ide",
            "package_manager",
            "analytics",
        ],
    }

    requirements: CatalogSection = CatalogSection(
        title="Requirements",
        description="Edges the IDE to the auto-magical behaviors you expect.",
        items=[
            "auto_detection: espanso_config_paths_all_platforms",
            "real_time_updates: filesystem_watcher_with_websockets",
            "rich_editing: word_processor_interface",
            "variable_system: inline_ide_with_multiple_types",
            "user_experience: zero_learning_curve",
        ],
    )

    ide_spec: Dict[str, Sequence[str]] = {
        "editor_type": ["rich_text_word_processor"],
        "key_features": [
            "wysiwyg_editing",
            "floating_context_toolbars",
            "inline_variable_management",
            "real_time_preview",
            "drag_drop_components",
            "smart_auto_completion",
        ],
        "variable_types": [
            "text (rich_text)",
            "date (calendar_with_formats)",
            "time (time_selector_with_zones)",
            "number (calculator_interface)",
            "choice (visual_dropdown_builder)",
            "list (spreadsheet_interface)",
            "script (code_editor_with_preview)",
            "api (rest_client_builder)",
            "file (file_picker_with_preview)",
            "image (image_editor_with_crop)",
        ],
        "insertion_methods": [
            "double_brace_trigger",
            "tab_completion",
            "right_click_context",
            "drag_drop_palette",
            "voice_commands",
            "markdown_shortcuts",
        ],
    }

    user_workflow: Dict[str, CatalogSection] = {
        "first_time": CatalogSection(
            title="First-time Workflow",
            description="Guides new users through onboarding quickly.",
            items=[
                "guided_tour: interactive_onboarding",
                "quick_start: template_gallery",
                "discovery: contextual_tooltips",
            ],
        ),
        "daily_use": CatalogSection(
            title="Daily Use",
            description="Supports distraction-free creation and inline management.",
            items=[
                "composition: distraction_free_editor",
                "variables: inline_editing_badges",
                "preview: live_espanso_simulation",
                "organization: smart_search_and_folders",
            ],
        ),
        "advanced_use": CatalogSection(
            title="Advanced Use",
            description="Power tools for debugging, collaboration, and analytics.",
            items=[
                "power_tools: multi_cursor_batch_editing",
                "debugging: step_through_variable_evaluation",
                "collaboration: real_time_multi_user",
                "analytics: snippet_performance_insights",
            ],
        ),
    }

    integration_requirements: CatalogSection = CatalogSection(
        title="Integration Requirements",
        description="How the IDE talks to Espanso runtime and storage.",
        items=[
            "espanso_cli: full_command_set_support",
            "file_system: recursive_yaml_processing",
            "real_time: live_configuration_reload",
            "backup: version_controlled_snapshots",
        ],
    )

    ui_components: CatalogSection = CatalogSection(
        title="UI Components",
        description="Navigational framing and theming desired for the app.",
        items=[
            "navigation: persistent_sidebar_with_collapsible_sections",
            "layout: responsive_grid_system",
            "theming: dark_light_mode_support",
            "mobile: touch_optimized_gestures",
        ],
    )

    success_criteria: Sequence[str] = [
        "auto_detects_espanso_configuration",
        "handles_complex_yaml_structures",
        "provides_intuitive_variable_management",
        "enables_rapid_snippet_creation",
        "maintains_configuration_integrity",
        "delivers_production_ready_performance",
    ]

    @classmethod
    def describe_architecture(cls) -> Dict[str, Sequence[str]]:
        return cls.architecture

    @classmethod
    def describe_workflow(cls) -> Dict[str, CatalogSection]:
        return cls.user_workflow
