from setuptools import setup
setup(
    name="semantic-kernel-sgraal", version="0.1.0",
    description="Sgraal preflight validation bridge for Microsoft Semantic Kernel",
    long_description="Validate Semantic Kernel memory results with Sgraal before use.",
    author="Sgraal", author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["semantic_kernel_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"],
)
