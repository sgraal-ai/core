from setuptools import setup
setup(name="letta-sgraal", version="0.1.0",
      description="Sgraal preflight validation bridge for Letta (MemGPT) agent memory",
      long_description="Validate Letta memory blocks with Sgraal preflight before agent action.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["letta_sgraal"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
