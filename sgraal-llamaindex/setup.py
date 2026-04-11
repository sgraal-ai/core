from setuptools import setup
setup(
    name="llamaindex-sgraal", version="0.1.0",
    description="Sgraal preflight validation bridge for LlamaIndex",
    long_description="Validate LlamaIndex retrieved nodes with Sgraal before passing to LLM.",
    author="Sgraal", author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["llamaindex_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"],
)
