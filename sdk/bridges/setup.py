from setuptools import setup, find_packages

setup(
    name="memorae-sgraal",
    version="0.1.0",
    description="Sgraal memory governance bridge for Memorae (WhatsApp/Telegram memory agent)",
    py_modules=["memorae_sgraal"],
    install_requires=["requests>=2.28.0"],
    python_requires=">=3.8",
    author="Sgraal",
    url="https://github.com/sgraal-ai/core/tree/main/sdk/bridges",
)
