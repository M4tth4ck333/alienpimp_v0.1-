from setuptools import setup, find_packages

# Es ist eine gute Praxis, die Anforderungen aus einer externen Datei zu lesen,
# aber für den Anfang ist das so völlig in Ordnung.

# Lese den Inhalt der README.md-Datei für die lange Beschreibung
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="alienpimp",
    version="0.1.0",
    author="Jan Schroeder",  
    author_email="jjschroeder64@gmail.con",  
    url="https://github.com/M4tth4ck333/alienpimp",
    description="Modulares Pentest-Toolkit mit TUI, Datenbank und KI-Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "sqlalchemy>=1.4",
        "pandas>=1.3",
        "numpy>=1.21",
        "torch>=2.0",
        "requests>=2.22.0",
        "rich",           
        "prompt_toolkit", 
        # ggf. weitere Abhängigkeiten hier eintragen
    ],
    
    entry_points={
        "console_scripts": [
            "alienpimp=alienpimp.tui:main"
        ]
    },
    # Diese Klassifizierer sind sehr gut gewählt!
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Developers",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    
    # Zusätzliche Links für dein Projekt
    project_urls={
        "Source": "https://github.com/M4tth4ck333/alienpimp", # <-- HIER AUCH ÄNDERN
        "Bug Tracker": "https://github.com/M4tth4ck333/alienpimp/issues", # <-- UND HIER
    },
    include_package_data=True,
)
