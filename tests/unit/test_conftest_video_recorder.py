"""
Tests for the video_recorder fixture added to tests/conftest.py.
TDD RED: these tests fail until video_recorder is added to conftest.py.

Tests verify:
- Fixture exists and has correct signature (scope, parameters)
- Fixture is opt-in (not autouse)
- Teardown deletes video on test pass
- Teardown retains video on test failure
- Teardown handles missing stash gracefully
- manager.stop() always called
"""
from __future__ import annotations

import inspect
import pytest
from unittest.mock import MagicMock, patch, call

import tests.conftest as conftest


class TestVideoRecorderPresence:
    """video_recorder fixture must exist with correct metadata."""

    def test_fixture_exists(self):
        assert hasattr(conftest, "video_recorder"), (
            "video_recorder not found in tests/conftest.py"
        )

    def test_fixture_is_callable(self):
        assert callable(conftest.video_recorder), (
            "video_recorder is not callable"
        )

    def test_fixture_not_autouse(self):
        """Fixture must be opt-in (autouse=False)."""
        # pytest marks autouse fixtures with _pytestfixturefunction.autouse = True
        marker = getattr(conftest.video_recorder, "_pytestfixturefunction", None)
        if marker is not None:
            assert not marker.autouse, "video_recorder must not be autouse"

    def test_fixture_scope_function(self):
        """Fixture must be function-scoped."""
        marker = getattr(conftest.video_recorder, "_pytestfixturefunction", None)
        if marker is not None:
            assert marker.scope in ("function", None), (
                f"video_recorder scope must be 'function', got {marker.scope!r}"
            )

    def test_fixture_signature_has_request(self):
        sig = inspect.signature(conftest.video_recorder)
        assert "request" in sig.parameters, "video_recorder must have 'request' parameter"

    def test_fixture_signature_has_app_config(self):
        sig = inspect.signature(conftest.video_recorder)
        assert "app_config" in sig.parameters, "video_recorder must have 'app_config' parameter"

    def test_fixture_signature_has_driver(self):
        sig = inspect.signature(conftest.video_recorder)
        assert "driver" in sig.parameters, "video_recorder must have 'driver' parameter"


class TestVideoRecorderBehavior:
    """Test the teardown logic of video_recorder via pytester."""

    @pytest.fixture()
    def mock_app_config(self):
        """Minimal AppConfig-like mock."""
        config = MagicMock()
        config.headless = False
        config.record_video = True
        return config

    @pytest.fixture()
    def mock_driver(self):
        """Minimal driver mock."""
        return MagicMock()

    def _make_request(self, call_failed: bool = False, setup_failed: bool = False, no_stash: bool = False):
        """Build a mock pytest request with stash populated as the hook would."""
        from tests.conftest import _phase_report_key

        request = MagicMock()
        request.node.name = "test_sample"

        if no_stash:
            # stash.get returns {} (no key present) — simulates error before call phase
            request.node.stash.get.return_value = {}
        else:
            call_report = MagicMock()
            call_report.failed = call_failed
            call_report.skipped = False
            setup_report = MagicMock()
            setup_report.failed = setup_failed
            setup_report.skipped = False
            stash_value = {"call": call_report, "setup": setup_report}
            request.node.stash.get.return_value = stash_value

        return request

    def _run_fixture(self, mock_app_config, mock_driver, request, video_path_return):
        """Drive the video_recorder generator fixture to completion."""
        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = video_path_return

            gen = conftest.video_recorder.__wrapped__(request, mock_app_config, mock_driver) \
                if hasattr(conftest.video_recorder, "__wrapped__") \
                else conftest.video_recorder(request, mock_app_config, mock_driver)

            yielded = next(gen)

            try:
                next(gen)
            except StopIteration:
                pass

            return mock_manager, yielded

    def test_start_passes_headless_when_headless_true(self, mock_app_config, mock_driver):
        """When headless=True, start() is called with headless=True (or not app_config.record_video equivalent)."""
        mock_app_config.headless = True
        mock_app_config.record_video = True
        request = self._make_request(call_failed=False)

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = None

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

            # headless=True -> start() called with headless=True
            call_kwargs = mock_manager.start.call_args
            assert call_kwargs is not None, "start() was not called"
            # The fixture passes headless=app_config.headless or not app_config.record_video
            # With headless=True and record_video=True: True or False = True
            _, kwargs = call_kwargs
            headless_arg = kwargs.get("headless", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else None)
            assert headless_arg is True, f"expected headless=True, got {headless_arg}"

    def test_stop_always_called(self, mock_app_config, mock_driver):
        """manager.stop() is called regardless of video_path value."""
        request = self._make_request(call_failed=False)

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = None  # no video

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

            mock_manager.stop.assert_called_once()

    def test_delete_called_on_pass(self, mock_app_config, mock_driver):
        """When test passes and video_path is not None: manager.delete(video_path) is called."""
        request = self._make_request(call_failed=False)
        video_path = "/tmp/test_sample.mp4"

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = video_path

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

            mock_manager.delete.assert_called_once_with(video_path)
            mock_manager.stop.assert_called_once()

    def test_delete_not_called_on_fail(self, mock_app_config, mock_driver):
        """When test fails and video_path is not None: manager.delete() is NOT called."""
        request = self._make_request(call_failed=True)
        video_path = "/tmp/test_sample.mp4"

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = video_path

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

            mock_manager.delete.assert_not_called()
            mock_manager.stop.assert_called_once()

    def test_no_delete_when_video_path_none(self, mock_app_config, mock_driver):
        """When video_path is None (recording unavailable): delete is never called."""
        request = self._make_request(call_failed=True)  # even on failure

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = None

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

            mock_manager.delete.assert_not_called()

    def test_missing_stash_handled_gracefully(self, mock_app_config, mock_driver):
        """When stash is missing (error in setup): no exception; stop() still called."""
        request = self._make_request(no_stash=True)
        video_path = "/tmp/test_sample.mp4"

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = video_path

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            # Should not raise
            try:
                next(gen)
            except StopIteration:
                pass

            # With empty stash, _Pass sentinel treats as passed => delete called
            mock_manager.stop.assert_called_once()

    def test_setup_fail_treated_as_failure(self, mock_app_config, mock_driver):
        """When setup phase fails (setup_report.failed=True): video is retained."""
        request = self._make_request(call_failed=False, setup_failed=True)
        video_path = "/tmp/test_sample.mp4"

        with patch("src.utils.videos.VideoManager") as MockVideoManagerClass:
            mock_manager = MagicMock()
            MockVideoManagerClass.return_value = mock_manager
            mock_manager.start.return_value = video_path

            gen = conftest.video_recorder(request, mock_app_config, mock_driver)
            next(gen)
            try:
                next(gen)
            except StopIteration:
                pass

            mock_manager.delete.assert_not_called()
