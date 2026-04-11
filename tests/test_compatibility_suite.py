"""Compatibility test suite — verifies all SDK bridge packages are importable."""
import pytest
import importlib


def _try_import(module_name, class_name):
    """Try importing a module and return the class, or skip if not installed."""
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, class_name)
    except (ImportError, ModuleNotFoundError):
        pytest.skip(f"{module_name} not installed")


class TestSDKImports:
    def test_sgraal_client(self):
        cls = _try_import("sgraal", "SgraalClient")
        assert hasattr(cls, "preflight")

    def test_mnemos_sgraal(self):
        cls = _try_import("mnemos_sgraal", "MnemosSgraal")
        assert hasattr(cls, "validate_memory")
        assert hasattr(cls, "is_safe")

    def test_memvid_sgraal(self):
        cls = _try_import("memvid_sgraal", "MemvidSgraal")
        assert hasattr(cls, "validate_chunks")
        assert hasattr(cls, "filter_safe_chunks")

    def test_llamaindex_sgraal(self):
        cls = _try_import("llamaindex_sgraal", "LlamaIndexSgraal")
        assert hasattr(cls, "validate_nodes")
        assert hasattr(cls, "filter_safe_nodes")

    def test_haystack_sgraal(self):
        cls = _try_import("haystack_sgraal", "HaystackSgraal")
        assert hasattr(cls, "validate_documents")
        assert hasattr(cls, "filter_safe_documents")

    def test_semantic_kernel_sgraal(self):
        cls = _try_import("semantic_kernel_sgraal", "SemanticKernelSgraal")
        assert hasattr(cls, "validate_memories")
        assert hasattr(cls, "is_safe")

    def test_langsmith_sgraal(self):
        cls = _try_import("langsmith_sgraal", "LangSmithSgraal")
        assert hasattr(cls, "preflight_with_trace")

    def test_langfuse_sgraal(self):
        cls = _try_import("langfuse_sgraal", "LangfuseSgraal")
        assert hasattr(cls, "preflight_with_trace")

    def test_llm_wrapper(self):
        cls = _try_import("llm_wrapper_sgraal", "SgraalLLMWrapper")
        assert hasattr(cls, "wrap")
        assert hasattr(cls, "decorator")
        assert hasattr(cls, "validate")

    def test_memory_normalizer(self):
        cls = _try_import("memory_normalizer", "MemoryNormalizer")
        assert hasattr(cls, "normalize")
        assert hasattr(cls, "from_mem0")
        assert hasattr(cls, "from_llamaindex")
        assert hasattr(cls, "from_langchain")
        assert hasattr(cls, "from_strings")
