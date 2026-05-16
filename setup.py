"""
PostMortemIQ Setup Configuration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="postmortemiq",
    version="1.0.0",
    author="PostMortemIQ Team",
    description="GraphRAG Incident Root-Cause Engine with Trusted Execution Environment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Shxam/graphRAG",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest==8.2.1",
            "pytest-cov==5.0.0",
            "pytest-asyncio==0.23.7",
            "pytest-mock==3.14.0",
            "black==24.4.2",
            "isort==5.13.2",
            "mypy==1.10.0",
            "pylint==3.2.2",
            "flake8==7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "postmortemiq=main:main",
        ],
    },
)
