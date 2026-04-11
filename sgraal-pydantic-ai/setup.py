from setuptools import setup
setup(name="pydantic-ai-sgraal", version="0.1.0",
      description="Sgraal preflight validation bridge for Pydantic AI",
      long_description="Validate Pydantic AI message history with Sgraal before agent action.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["pydantic_ai_sgraal"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
