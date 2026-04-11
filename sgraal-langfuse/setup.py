from setuptools import setup
setup(
    name="langfuse-sgraal", version="0.1.0",
    description="Sgraal preflight decisions as Langfuse trace spans",
    long_description="Export Sgraal preflight decisions to Langfuse for observability.",
    author="Sgraal", author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["langfuse_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"],
)
