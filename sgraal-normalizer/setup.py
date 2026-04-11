from setuptools import setup
setup(name="sgraal-normalizer", version="0.1.0",
      description="Cross-provider memory normalizer for Sgraal — converts Mem0, LlamaIndex, LangChain, and raw strings to MemCube format",
      long_description="Normalize memory from any provider to Sgraal MemCube format for preflight validation.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["memory_normalizer"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
