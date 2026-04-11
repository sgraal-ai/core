from setuptools import setup
setup(name="azure-ai-sgraal", version="0.1.0",
      description="Sgraal preflight validation bridge for Azure AI Foundry",
      long_description="Validate Azure AI agent messages and tool results with Sgraal preflight.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["azure_ai_sgraal"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
