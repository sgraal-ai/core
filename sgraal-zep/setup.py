from setuptools import setup
setup(name="zep-sgraal", version="0.1.0",
      description="Sgraal preflight validation bridge for Zep memory store",
      long_description="Validate Zep memory search results with Sgraal preflight.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["zep_sgraal"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
