from setuptools import setup
setup(
    name="langsmith-sgraal", version="0.1.0",
    description="Sgraal preflight decisions as LangSmith trace spans",
    long_description="Export Sgraal preflight decisions to LangSmith for observability.",
    author="Sgraal", author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["langsmith_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"],
)
