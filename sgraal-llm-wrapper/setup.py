from setuptools import setup
setup(name="sgraal-llm-wrapper", version="0.1.0",
      description="Drop-in LLM wrapper that adds Sgraal preflight validation to any LLM call",
      long_description="Wrap any LLM function with Sgraal preflight. BLOCK raises ValueError before generation.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["llm_wrapper_sgraal"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
