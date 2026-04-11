from setuptools import setup
setup(name="google-adk-sgraal", version="0.1.0",
      description="Sgraal preflight validation bridge for Google Agent Development Kit",
      long_description="Validate Google ADK agent state with Sgraal before action execution.",
      author="Sgraal", author_email="hello@sgraal.com", url="https://github.com/sgraal-ai/core",
      py_modules=["google_adk_sgraal"], install_requires=["sgraal>=0.2.0"], python_requires=">=3.9",
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: Apache Software License"])
