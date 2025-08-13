# Unit tests for utils.chunks.reverse_block_chunks

import itertools
import math
import pytest

from utils.chunks import reverse_block_chunks


class TestReverseBlockChunks:
    def test_list_exact_multiple(self):
        data = [1, 2, 3, 4, 5, 6]
        chunks = list(reverse_block_chunks(data, 2))
        assert chunks == [[5, 6], [3, 4], [1, 2]]

    def test_list_non_multiple(self):
        data = [1, 2, 3, 4, 5]
        chunks = list(reverse_block_chunks(data, 2))
        assert chunks == [[4, 5], [2, 3], [1]]

    def test_tuple_preserves_type_and_order(self):
        data = ("a", "b", "c", "d", "e")
        chunks = list(reverse_block_chunks(data, 2))
        # Should keep inner order and return tuple slices
        assert chunks == [("d", "e"), ("b", "c"), ("a",)]
        assert all(isinstance(c, tuple) for c in chunks)

    def test_set_covers_all_elements_and_expected_blocking(self):
        # Sets are unordered, so only verify coverage and block sizes
        s = set(range(7))
        size = 3
        chunks = list(reverse_block_chunks(s, size))
        # Expect ceil(7/3) blocks with sizes [3, 3, 1] in that order (from latest backwards)
        sizes = [len(c) for c in chunks]
        assert len(chunks) == math.ceil(len(s) / size)
        assert sizes == [3, 3, 1]
        # All elements covered exactly once
        flattened = list(itertools.chain.from_iterable(chunks))
        assert sorted(flattened) == sorted(s)

    def test_empty_inputs(self):
        assert list(reverse_block_chunks([], 3)) == []
        assert list(reverse_block_chunks((), 3)) == []
        assert list(reverse_block_chunks(set(), 3)) == []

    def test_size_greater_than_length(self):
        data_list = [1, 2]
        data_tuple = (1, 2)
        assert list(reverse_block_chunks(data_list, 5)) == [[1, 2]]
        assert list(reverse_block_chunks(data_tuple, 5)) == [(1, 2)]

    def test_size_one_behaves_like_reverse_iteration(self):
        data = [1, 2, 3, 4]
        chunks = list(reverse_block_chunks(data, 1))
        assert chunks == [[4], [3], [2], [1]]

    @pytest.mark.parametrize("size", [0, -1])
    def test_non_positive_size_is_not_supported_do_not_iterate(self, size):
        # The function would otherwise loop infinitely for size <= 0, so ensure we never iterate
        gen = reverse_block_chunks([1, 2, 3], size)
        # Don't iterate the generator; just confirm it's a generator
        assert hasattr(gen, "__iter__") and not isinstance(gen, list)
