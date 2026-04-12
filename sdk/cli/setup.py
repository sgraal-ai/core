from setuptools import setup, find_packages
setup(
    name="sgraal-cli",
    version="0.1.0",
    description="Sgraal Memory Governance CLI",
    packages=find_packages(),
    install_requires=["click>=8.0", "requests>=2.28", "pyyaml>=6.0", "sgraal>=0.2.0"],
    entry_points={"console_scripts": ["sgraal=sgraal_cli.main:cli"]},
    python_requires=">=3.9",
)
