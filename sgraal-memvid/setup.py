from setuptools import setup

setup(
    name="memvid-sgraal",
    version="0.1.0",
    description="Sgraal preflight validation bridge for Memvid memory layer",
    long_description="Validate Memvid retrieved chunks with Sgraal before passing to LLM. "
                     "Prevents stale, conflicting, or poisoned memory from reaching generation.",
    author="Sgraal",
    author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["memvid_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
)
