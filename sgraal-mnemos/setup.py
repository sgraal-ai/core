from setuptools import setup

setup(
    name="mnemos-sgraal",
    version="0.1.0",
    description="Sgraal preflight validation bridge for mnemos memory engine",
    long_description="Validate mnemos agent memories with Sgraal before acting. "
                     "Prevents stale, conflicting, or poisoned memories from triggering "
                     "irreversible agent actions.",
    author="Sgraal",
    author_email="hello@sgraal.com",
    url="https://github.com/sgraal-ai/core",
    py_modules=["mnemos_sgraal"],
    install_requires=["sgraal>=0.2.0"],
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
)
