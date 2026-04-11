from setuptools import setup
setup(
    name="haystack-sgraal", version="0.1.0",
    description="Sgraal preflight validation bridge for Haystack (deepset)",
    long_description="Validate Haystack retrieved documents with Sgraal before generation.",
    author="Sgraal", author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["haystack_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"],
)
