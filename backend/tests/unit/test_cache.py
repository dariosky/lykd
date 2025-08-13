from pathlib import Path

import pytest

from utils.cache import disk_cache


class TestDiskCacheMiss:
    """Test suite for disk_cache decorator."""

    @pytest.fixture
    def cache_miss(self, mocker):
        mock_read = mocker.patch("utils.cache._read_json", return_value=None)
        mock_write = mocker.patch("utils.cache._write_json")
        return mock_read, mock_write

    def test_sync_cache_miss(self, tmp_path: Path, cache_miss):
        """Test sync cache miss - _read_json returns None, _write_json called with path and data."""
        mock_read, mock_write = cache_miss

        @disk_cache(cache_dir=str(tmp_path), namespace="test_ns")
        def add_numbers(a, b, *, c=0):
            return a + b + c

        assert add_numbers(1, 2, c=3) == 6

        expected_path = tmp_path / "add_numbers" / "test_ns" / "1__2__c=3.json"
        mock_read.assert_called_once_with(expected_path)

        # Verify _write_json was called with correct path and data
        assert mock_write.call_count == 1
        assert mock_write.mock_calls[0].args == (expected_path, 6)

    async def test_async_cache_miss(self, tmp_path: Path, cache_miss):
        """Test async cache miss - _read_json returns None, _write_json called with path and data."""
        mock_read, mock_write = cache_miss

        @disk_cache(cache_dir=str(tmp_path), namespace="async_ns")
        async def multiply_async(x, y):
            return x * y

        assert await multiply_async(5, 2) == 10

        expected_path = tmp_path / "multiply_async" / "async_ns" / "5__2.json"
        mock_read.assert_called_once_with(expected_path)

        # Verify _write_json was called with correct path and data
        assert mock_write.call_count == 1
        assert mock_write.mock_calls[0].args == (expected_path, 10)

    def test_no_args_cache_miss(self, tmp_path: Path, cache_miss):
        """Test cache miss for function with no arguments."""
        mock_read, mock_write = cache_miss

        @disk_cache(cache_dir=str(tmp_path))
        def no_args_func():
            return "no_args_result"

        # Verify function result
        assert no_args_func() == "no_args_result"

        # Verify correct path used for no-args function
        expected_path = tmp_path / "no_args_func" / "no_args.json"
        mock_read.assert_called_once_with(expected_path)

        # Verify _write_json called with correct path and data
        assert mock_write.call_count == 1
        write_path, write_data = mock_write.mock_calls[0].args
        assert write_path, write_data == (expected_path, "no_args_result")

    def test_complex_path_structure(self, tmp_path: Path, cache_miss):
        """Test path generation with multiple args and kwargs."""
        mock_read, mock_write = cache_miss

        @disk_cache(cache_dir=str(tmp_path), namespace="complex")
        def complex_func(a, b, c, x=1, y=2):
            return f"{a}-{b}-{c}-{x}-{y}"

        complex_func("arg1", "arg2", "arg3", x=10, y=20)

        # Verify path structure: namespace becomes first dir, remaining args become filename
        expected_path = (
            tmp_path / "complex_func" / "complex" / "arg1__arg2__arg3__x=10__y=20.json"
        )
        mock_read.assert_called_once_with(expected_path)

        assert mock_write.call_count == 1
        assert mock_write.mock_calls[0].args == (expected_path, "arg1-arg2-arg3-10-20")


class TestDiskCaseHit:
    def test_sync_cache_hit(self, tmp_path: Path, mocker):
        """Test sync cache hit - _read_json returns cached data, _write_json not called."""
        # Mock _read_json to simulate cache hit
        mock_read = mocker.patch("utils.cache._read_json", return_value="cached_result")
        mock_write = mocker.patch("utils.cache._write_json")

        @disk_cache(cache_dir=str(tmp_path))
        def expensive_function(arg):
            return "not called"

        assert expensive_function("test") == "cached_result"

        expected_path = tmp_path / "expensive_function" / "test" / "data.json"
        mock_read.assert_called_once_with(expected_path)

        mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_cache_hit(self, tmp_path: Path, mocker):
        """Test async cache hit - _read_json returns cached data, _write_json not called."""
        # Mock _read_json to simulate cache hit
        mock_read = mocker.patch(
            "utils.cache._read_json", return_value={"cached": "data"}
        )
        mock_write = mocker.patch("utils.cache._write_json")

        @disk_cache(cache_dir=str(tmp_path))
        async def expensive_async_function(arg1, arg2):
            return "not called"

        # Verify cached result returned
        assert await expensive_async_function("foo", "bar") == {"cached": "data"}

        expected_path = tmp_path / "expensive_async_function" / "foo" / "bar.json"
        mock_read.assert_called_once_with(expected_path)

        mock_write.assert_not_called()
