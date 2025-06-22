from setuptools import setup, find_packages

setup(
    name="alienpimp",
    version="0.1.0",
    description="Modulares Pentest-Toolkit mit TUI, Datenbank, KI und JAN-Integration",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Dein Name",
    author_email="deine@email.de",
    url="https://github.com/M4tth4ck333/alienpimp_v0.1-/blob/main/setup.py",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "sqlalchemy>=1.4",
        "pandas>=1.3",
        "numpy>=1.21",
        "torch>=2.0",
        "requests>=2.22.0",
        "rich",           # Für schöne CLI-Ausgaben
        "prompt_toolkit", # Für TUI/CLI-Interaktivität
        # ggf. weitere Abhängigkeiten
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "alienpimp=alienpimp.tui:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Developers",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    project_urls={
        "Source": "https://github.com/DEINUSERNAME/alienpimp",
        "Bug Tracker": "https://github.com/DEINUSERNAME/alienpimp/issues",
    },
)
