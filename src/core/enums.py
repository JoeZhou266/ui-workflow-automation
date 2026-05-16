from __future__ import annotations

from enum import Enum


class ElementType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    BUTTON = "button"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    MULTISELECT = "multiselect"
    DATE = "date"
    LINK = "link"
    LABEL = "label"
    FILE = "file"
    NUMBER = "number"
    EMAIL = "email"


class ActionType(str, Enum):
    INPUT = "input"
    CLICK = "click"
    SELECT_BY_TEXT = "select_by_text"
    SELECT_BY_VALUE = "select_by_value"
    SELECT_BY_INDEX = "select_by_index"
    CHECK = "check"
    UNCHECK = "uncheck"
    SELECT_RADIO = "select_radio"
    UPLOAD = "upload"
    ASSERT_ONLY = "assert_only"
    NOOP = "noop"
    SWITCH_TO_NEW_WINDOW = "switch_to_new_window"
    SWITCH_TO_NEW_TAB = "switch_to_new_tab"
    SWITCH_TO_LATEST_WINDOW = "switch_to_latest_window"


class WaitConditionType(str, Enum):
    VISIBLE = "visible"
    CLICKABLE = "clickable"
    PRESENT = "present"
    INVISIBLE = "invisible"
    SELECTED = "selected"
    URL_CONTAINS = "url_contains"
    TEXT_EQUALS = "text_equals"
    TEXT_CONTAINS = "text_contains"
    VALUE_EQUALS = "value_equals"
    ATTRIBUTE_CONTAINS = "attribute_contains"
    ATTRIBUTE_EQUALS = "attribute_equals"
    COUNT_GREATER_THAN = "count_greater_than"
    OPTIONS_COUNT_GREATER_THAN = "options_count_greater_than"
    DOCUMENT_READY = "document_ready"
    AJAX_IDLE = "ajax_idle"
    SPINNER_GONE = "spinner_gone"
    OVERLAY_GONE = "overlay_gone"
    ENABLED = "enabled"


class StepStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BrowserType(str, Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"


class FailurePhase(str, Enum):
    PAGE_LOAD = "page_load_wait"
    PRE_WAIT = "pre_action_wait"
    ACTION = "interaction"
    POST_WAIT = "post_action_wait"
    ASSERTION = "assertion"
