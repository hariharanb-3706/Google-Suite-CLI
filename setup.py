from setuptools import setup, find_packages

setup(
    name="gsuite-cli",
    version="0.1.0",
    description="Advanced CLI tool for Google Workspace services",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "google-auth>=2.0.0",
        "google-auth-oauthlib>=1.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-api-python-client>=2.0.0",
        "tabulate>=0.9.0",
        "colorama>=0.4.4",
        "diskcache>=5.4.0",
        "prompt-toolkit>=3.0.0",
        "pyyaml>=6.0",
        "python-dateutil>=2.8.0",
        "requests>=2.25.0",
        "google-genai>=0.1.0",
    ],
    entry_points={
        "console_scripts": [
            "gs=gsuite_cli.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
